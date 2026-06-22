"""Teknik borcu parasal değere çevirir."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from codedna.db import get_connection, get_file_scores_for_commit, get_commit_history

# Varsayılan saatlik maliyet (USD)
_VARSAYILAN_SAATLIK = 75.0

# Risk eşikleri (aylık maliyet)
_KRITIK_ESIK = 100.0   # $/ay üzeri → KRİTİK
_YUKSEK_ESIK = 50.0    # $/ay üzeri → YÜKSEK


@dataclass
class DosyaBorcu:
    """Tek dosyanın teknik borç analizi."""

    dosya_yolu: str
    debt_saatleri: float        # tahmini borç saati
    aylik_maliyet_usd: float    # amortismana yayılmış aylık maliyet
    risk_seviyesi: str          # KRİTİK / YÜKSEK / ORTA / DÜŞÜK
    toplam_satir: int
    ai_olasiligi: float
    karmasiklik: float
    anlama_skoru: Optional[float]


@dataclass
class RepoBorcu:
    """Repo geneli teknik borç özeti."""

    toplam_debt_saatleri: float
    toplam_aylik_maliyet_usd: float
    en_pahali_5: list[DosyaBorcu]
    toplam_dosya: int
    saatlik_ucret: float


def _risk_hesapla(aylik_maliyet: float) -> str:
    """Aylık maliyete göre risk seviyesi döndür."""
    if aylik_maliyet >= _KRITIK_ESIK:
        return "KRİTİK"
    elif aylik_maliyet >= _YUKSEK_ESIK:
        return "YÜKSEK"
    elif aylik_maliyet >= 20.0:
        return "ORTA"
    return "DÜŞÜK"


def _debt_saati_hesapla(
    anlama_skoru: Optional[float],
    ai_olasiligi: float,
    karmasiklik: float,
    toplam_satir: int,
) -> float:
    """
    Dosya için teknik borç saatini hesapla.

    Formül:
        debt_hours = (
            (1 - understanding_score/5) * 0.4   ← düşük anlama
          + ai_probability * 0.35                ← AI kodu
          + min(complexity/20, 1.0) * 0.25       ← karmaşıklık
        ) * (lines_of_code / 100) * 2

    Anlama skoru yoksa 2.5/5 varsayılır.
    """
    anlama = anlama_skoru if anlama_skoru is not None else 2.5
    anlama_faktor = (1.0 - anlama / 5.0) * 0.40
    ai_faktor = ai_olasiligi * 0.35
    karmasiklik_faktor = min(karmasiklik / 20.0, 1.0) * 0.25

    satir_carpan = (toplam_satir / 100.0) * 2.0

    return (anlama_faktor + ai_faktor + karmasiklik_faktor) * satir_carpan


def calculate_file_debt(
    file_path: str,
    db_path: Path,
    hourly_rate: float = _VARSAYILAN_SAATLIK,
) -> Optional[DosyaBorcu]:
    """
    Tek dosya için teknik borç saatini ve dolar maliyetini hesapla.
    Önce DB'den arar, bulamazsa dosyayı doğrudan analiz eder.

    Args:
        file_path: Dosya yolu (tam veya göreli)
        db_path: SQLite veritabanı yolu
        hourly_rate: Saatlik maliyet ($/saat)

    Returns:
        DosyaBorcu nesnesi veya dosya bulunamazsa None
    """
    # Önce DB'den en son skoru bul
    satir = None
    try:
        with get_connection(db_path) as conn:
            satir = conn.execute(
                """
                SELECT fs.ai_probability, fs.complexity_score, fs.understanding_score
                FROM file_scores fs
                JOIN commits c ON fs.commit_hash = c.commit_hash
                WHERE fs.file_path = ?
                ORDER BY c.timestamp DESC
                LIMIT 1
                """,
                (file_path,),
            ).fetchone()
    except Exception:
        pass

    # DB'den gelen değerleri al veya dosyayı doğrudan analiz et
    if satir:
        ai = float(satir["ai_probability"] or 0.0)
        karmasiklik = float(satir["complexity_score"] or 1.0)
        anlama = float(satir["understanding_score"]) if satir["understanding_score"] is not None else None
    else:
        # DB'de yok — tree-sitter ile doğrudan analiz et
        p = Path(file_path)
        if not p.exists():
            return None
        try:
            from codedna.analyzer import analyze_file
            sonuc = analyze_file(p)
            if sonuc.desteklenmiyor or sonuc.hata:
                return None
            ai = sonuc.ai_probability
            karmasiklik = sonuc.complexity_score
            anlama = None
        except Exception:
            return None

    # Satır sayısı
    toplam_satir = 100
    try:
        p = Path(file_path)
        if p.exists():
            toplam_satir = len(p.read_text(errors="replace").splitlines())
    except Exception:
        pass

    debt_saati = _debt_saati_hesapla(anlama, ai, karmasiklik, toplam_satir)
    aylik_maliyet = debt_saati * hourly_rate / 12.0

    return DosyaBorcu(
        dosya_yolu=file_path,
        debt_saatleri=round(debt_saati, 2),
        aylik_maliyet_usd=round(aylik_maliyet, 2),
        risk_seviyesi=_risk_hesapla(aylik_maliyet),
        toplam_satir=toplam_satir,
        ai_olasiligi=round(ai, 3),
        karmasiklik=round(karmasiklik, 1),
        anlama_skoru=round(anlama, 2) if anlama is not None else None,
    )


def calculate_repo_debt(
    repo_path: Path,
    db_path: Path,
    hourly_rate: float = _VARSAYILAN_SAATLIK,
) -> RepoBorcu:
    """
    Repo geneli toplam teknik borç özeti hesapla.

    Args:
        repo_path: Git repo kök dizini
        db_path: SQLite veritabanı yolu
        hourly_rate: Saatlik maliyet ($/saat)

    Returns:
        RepoBorcu özet nesnesi
    """
    # DB'deki tüm benzersiz dosya yollarını çek
    try:
        with get_connection(db_path) as conn:
            dosya_yollari = [
                r["file_path"]
                for r in conn.execute(
                    "SELECT DISTINCT file_path FROM file_scores"
                ).fetchall()
            ]
    except Exception:
        dosya_yollari = []

    # Repo dosyalarını da tara (DB'de yoksa da hesapla)
    from codedna.scorer import scan_repository
    taranan = scan_repository(repo_path, max_files=200)
    tarama_yollari = {s.file_path for s in taranan}

    # İkisini birleştir
    tum_yollar = list(set(dosya_yollari) | tarama_yollari)

    dosya_borclar: list[DosyaBorcu] = []
    for yol in tum_yollar:
        # DB'de varsa DB'den al, yoksa taranan sonuçtan hesapla
        borc = calculate_file_debt(yol, db_path, hourly_rate)
        if borc is None:
            # Taranan sonuçtan bulup hesapla
            taranan_sonuc = next((s for s in taranan if s.file_path == yol), None)
            if taranan_sonuc:
                debt_saati = _debt_saati_hesapla(
                    None,
                    taranan_sonuc.ai_probability,
                    taranan_sonuc.complexity_score,
                    taranan_sonuc.total_lines,
                )
                aylik = debt_saati * hourly_rate / 12.0
                borc = DosyaBorcu(
                    dosya_yolu=yol,
                    debt_saatleri=round(debt_saati, 2),
                    aylik_maliyet_usd=round(aylik, 2),
                    risk_seviyesi=_risk_hesapla(aylik),
                    toplam_satir=taranan_sonuc.total_lines,
                    ai_olasiligi=round(taranan_sonuc.ai_probability, 3),
                    karmasiklik=round(taranan_sonuc.complexity_score, 1),
                    anlama_skoru=None,
                )
        if borc:
            dosya_borclar.append(borc)

    # En pahalı 5 dosya
    dosya_borclar.sort(key=lambda d: d.aylik_maliyet_usd, reverse=True)
    en_pahali = dosya_borclar[:5]

    toplam_saat = sum(d.debt_saatleri for d in dosya_borclar)
    toplam_aylik = sum(d.aylik_maliyet_usd for d in dosya_borclar)

    return RepoBorcu(
        toplam_debt_saatleri=round(toplam_saat, 2),
        toplam_aylik_maliyet_usd=round(toplam_aylik, 2),
        en_pahali_5=en_pahali,
        toplam_dosya=len(dosya_borclar),
        saatlik_ucret=hourly_rate,
    )
