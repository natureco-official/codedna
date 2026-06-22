"""Yeni katılan geliştiricilerin üretkenlik eğrisini ölçer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from codedna.db import get_connection

# Üretkenlik eşiği — bu skoru aşınca "ramp-up tamamlandı" sayılır
_VARSAYILAN_ESIK = 3.5

# Ramp-up tahmini için minimum commit sayısı
_MIN_COMMIT = 5


@dataclass
class CommitNoktasi:
    """Tek commit için anlama skoru verisi."""

    commit_hash: str
    commit_no: int           # yazar bazlı sıra numarası (1'den başlar)
    tarih: datetime
    understanding_score: Optional[float]
    hafta_no: int            # ilk committen itibaren geçen hafta sayısı


@dataclass
class YazarEgri:
    """Tek yazar için onboarding eğrisi."""

    yazar: str
    toplam_commit: int
    anlama_skoru_olan: int
    ramp_up_hafta: Optional[float]   # None = yeterli veri yok / eşik aşılmadı
    son_ort_anlama: Optional[float]  # son 5 commit ortalaması
    noktalar: list[CommitNoktasi]


def get_author_timeline(author: str, db_path: Path) -> list[CommitNoktasi]:
    """
    Bir yazarın tüm commit'lerini kronolojik anlama skoruyla döndür.

    Args:
        author: Yazar adı (commits.author ile eşleşmeli)
        db_path: SQLite veritabanı yolu

    Returns:
        CommitNoktasi listesi, tarih sırasıyla
    """
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(
                """
                SELECT commit_hash, author, timestamp, understanding_score
                FROM commits
                WHERE author = ?
                ORDER BY timestamp ASC
                """,
                (author,),
            ).fetchall()
    except Exception:
        return []

    if not rows:
        return []

    ilk_ts = rows[0]["timestamp"] or 0
    noktalar: list[CommitNoktasi] = []

    for i, r in enumerate(rows):
        ts = r["timestamp"] or ilk_ts
        hafta = int((ts - ilk_ts) / (7 * 24 * 3600))
        noktalar.append(
            CommitNoktasi(
                commit_hash=r["commit_hash"] or "",
                commit_no=i + 1,
                tarih=datetime.fromtimestamp(ts),
                understanding_score=(
                    float(r["understanding_score"])
                    if r["understanding_score"] is not None
                    else None
                ),
                hafta_no=hafta,
            )
        )

    return noktalar


def estimate_ramp_up_weeks(
    author: str,
    db_path: Path,
    threshold: float = _VARSAYILAN_ESIK,
) -> Optional[float]:
    """
    Yazarın ortalama anlama skoru threshold'u aştığı ilk haftayı tahmin et.

    Algoritma:
      - Anlama skoru olan commit'ler 3'lü hareketli ortalama ile yumuşatılır
      - Yumuşatılmış skor threshold'u aştığı ilk commit'in hafta numarası döndürülür
      - Yeterli veri yoksa (< MIN_COMMIT anketli commit) None döndürülür

    Args:
        author: Yazar adı
        db_path: SQLite veritabanı yolu
        threshold: Üretkenlik eşiği (varsayılan 3.5/5)

    Returns:
        Ramp-up haftası veya None
    """
    noktalar = get_author_timeline(author, db_path)
    anketli = [n for n in noktalar if n.understanding_score is not None]

    if len(anketli) < _MIN_COMMIT:
        return None

    # 3'lü hareketli ortalama
    skorlar = [n.understanding_score for n in anketli]  # type: ignore[misc]
    for i in range(2, len(skorlar)):
        pencere = skorlar[max(0, i - 2): i + 1]
        ort = sum(pencere) / len(pencere)
        if ort >= threshold:
            return float(anketli[i].hafta_no)

    return None  # eşik hiç aşılmadı


def get_author_curve(author: str, db_path: Path) -> YazarEgri:
    """
    Tek yazar için tam onboarding eğrisi nesnesi oluştur.

    Args:
        author: Yazar adı
        db_path: SQLite veritabanı yolu

    Returns:
        YazarEgri nesnesi
    """
    noktalar = get_author_timeline(author, db_path)
    anketli = [n for n in noktalar if n.understanding_score is not None]

    ramp_up = estimate_ramp_up_weeks(author, db_path)

    son_5 = [n.understanding_score for n in anketli[-5:] if n.understanding_score]
    son_ort = sum(son_5) / len(son_5) if son_5 else None

    return YazarEgri(
        yazar=author,
        toplam_commit=len(noktalar),
        anlama_skoru_olan=len(anketli),
        ramp_up_hafta=round(ramp_up, 1) if ramp_up is not None else None,
        son_ort_anlama=round(son_ort, 2) if son_ort is not None else None,
        noktalar=noktalar,
    )


def get_all_authors(db_path: Path) -> list[str]:
    """DB'deki tüm benzersiz yazar listesini döndür."""
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT author FROM commits WHERE author IS NOT NULL ORDER BY author"
            ).fetchall()
        return [r["author"] for r in rows]
    except Exception:
        return []


def team_onboarding_summary(db_path: Path) -> list[dict]:
    """
    Takımdaki tüm yazarlar için ramp-up süresi özeti döndür.

    Returns:
        Yazar bazlı özet dict listesi, ramp_up_hafta'ya göre sıralı
    """
    yazarlar = get_all_authors(db_path)
    ozet: list[dict] = []

    for yazar in yazarlar:
        egri = get_author_curve(yazar, db_path)
        ozet.append({
            "yazar": yazar,
            "toplam_commit": egri.toplam_commit,
            "anlama_skoru_olan": egri.anlama_skoru_olan,
            "ramp_up_hafta": egri.ramp_up_hafta,
            "son_ort_anlama": egri.son_ort_anlama,
            "yeterli_veri": egri.anlama_skoru_olan >= _MIN_COMMIT,
        })

    # Ramp-up süresi olan önce, sonra None olanlar
    ozet.sort(key=lambda x: (x["ramp_up_hafta"] is None, x["ramp_up_hafta"] or 999))
    return ozet
