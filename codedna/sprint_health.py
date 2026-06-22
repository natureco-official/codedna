"""Sprint bazlı kod sağlığı skoru hesaplama."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from codedna.db import get_connection, get_sprint_history, save_sprint

# Sağlık skoru eşikleri (0-100)
_SAGLIKLI_ESIK = 80
_DIKKAT_ESIK = 50

# Yüksek riskli AI eşiği
_YUKSEK_RISK_AI = 0.7


@dataclass
class SprintSonucu:
    """Tek sprint'in sağlık analizi."""

    sprint_adi: str
    baslangic: datetime
    bitis: datetime
    health_score: float            # 0-100
    durum: str                     # SAĞLIKLI / DİKKAT / RİSKLİ
    avg_understanding: Optional[float]
    ai_orani: float                # yüksek riskli AI dosyalarının oranı
    debt_delta_saati: float        # borç değişimi (+ = arttı, - = azaldı)
    toplam_commit: int
    ai_satir: int
    insan_satir: int

    @property
    def ai_insan_orani_str(self) -> str:
        """AI/insan oranını yüzde string olarak döndür."""
        toplam = self.ai_satir + self.insan_satir
        if toplam == 0:
            return "N/A"
        ai_pct = self.ai_satir / toplam * 100
        return f"%{ai_pct:.0f} AI / %{100-ai_pct:.0f} İnsan"


def _durum_belirle(skor: float) -> str:
    """Skor aralığına göre durum etiketi döndür."""
    if skor >= _SAGLIKLI_ESIK:
        return "SAĞLIKLI"
    elif skor >= _DIKKAT_ESIK:
        return "DİKKAT"
    return "RİSKLİ"


def calculate_sprint_health(
    repo_path: Path,
    db_path: Path,
    start_date: datetime,
    end_date: datetime,
    sprint_adi: str = "Sprint",
) -> SprintSonucu:
    """
    Verilen tarih aralığındaki commitleri analiz edip sprint sağlık skoru üret.

    Health score formülü (0-100):
      - anlama_puani = (avg_understanding / 5) * 40       max 40 puan
      - ai_dengesi   = (1 - yüksek_riskli_ai_orani) * 30  max 30 puan
      - borc_trendi  = max(0, 1 - delta_oran) * 30         max 30 puan

    Args:
        repo_path: Git repo kök dizini
        db_path: SQLite veritabanı yolu
        start_date: Sprint başlangıç tarihi
        end_date: Sprint bitiş tarihi
        sprint_adi: Sprint ismi

    Returns:
        SprintSonucu nesnesi
    """
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())

    # Sprint tarih aralığındaki commit'leri ve dosya skorlarını çek
    try:
        with get_connection(db_path) as conn:
            commitler = conn.execute(
                """
                SELECT c.commit_hash, c.understanding_score, c.timestamp
                FROM commits c
                WHERE c.timestamp >= ? AND c.timestamp <= ?
                ORDER BY c.timestamp ASC
                """,
                (start_ts, end_ts),
            ).fetchall()
    except Exception:
        commitler = []

    toplam_commit = len(commitler)

    # Dosya skorlarını topla
    ai_skorlari: list[float] = []
    anlama_skorlari: list[float] = []

    try:
        with get_connection(db_path) as conn:
            for commit in commitler:
                dosyalar = conn.execute(
                    """
                    SELECT ai_probability, understanding_score
                    FROM file_scores
                    WHERE commit_hash = ?
                    """,
                    (commit["commit_hash"],),
                ).fetchall()
                for d in dosyalar:
                    if d["ai_probability"] is not None:
                        ai_skorlari.append(float(d["ai_probability"]))
                    if d["understanding_score"] is not None:
                        anlama_skorlari.append(float(d["understanding_score"]))
    except Exception:
        pass

    # Ortalama anlama skoru
    avg_anlama = (
        sum(anlama_skorlari) / len(anlama_skorlari)
        if anlama_skorlari else None
    )

    # Yüksek riskli AI oranı (>= 0.7)
    yuksek_riskli = sum(1 for a in ai_skorlari if a >= _YUKSEK_RISK_AI)
    ai_orani = yuksek_riskli / len(ai_skorlari) if ai_skorlari else 0.0

    # AI / insan satır tahmini (AI skoru > 0.5 → AI satır sayılır)
    ai_satir = sum(1 for a in ai_skorlari if a > 0.5) * 50  # yaklaşık
    insan_satir = max(len(ai_skorlari) * 50 - ai_satir, 0)

    # Teknik borç delta'sı — tüm repo borcu hesapla (sprint başı/sonu farkı yok,
    # mevcut durumu baz al, negatif = borç azaldı yorumu)
    from codedna.tech_debt import calculate_repo_debt
    try:
        ozet = calculate_repo_debt(repo_path, db_path)
        debt_delta = ozet.toplam_debt_saatleri / max(toplam_commit, 1)
    except Exception:
        debt_delta = 0.0

    # ---- Health score hesapla ----
    # 1. Anlama puanı (max 40)
    anlama_puani = ((avg_anlama / 5.0) * 40.0) if avg_anlama is not None else 20.0

    # 2. AI denge puanı (max 30)
    ai_dengesi = (1.0 - ai_orani) * 30.0

    # 3. Borç trendi puanı (max 30) — debt_delta küçükse iyi
    delta_oran = min(debt_delta / 10.0, 1.0)   # 10 saate normalize
    borc_trendi = max(0.0, 1.0 - delta_oran) * 30.0

    health_score = round(anlama_puani + ai_dengesi + borc_trendi, 1)
    durum = _durum_belirle(health_score)

    return SprintSonucu(
        sprint_adi=sprint_adi,
        baslangic=start_date,
        bitis=end_date,
        health_score=health_score,
        durum=durum,
        avg_understanding=round(avg_anlama, 2) if avg_anlama is not None else None,
        ai_orani=round(ai_orani, 3),
        debt_delta_saati=round(debt_delta, 2),
        toplam_commit=toplam_commit,
        ai_satir=ai_satir,
        insan_satir=insan_satir,
    )


def save_sprint_result(sonuc: SprintSonucu, db_path: Path) -> int:
    """Sprint sonucunu DB'ye kaydet, yeni id döndür."""
    return save_sprint(
        sprint_name=sonuc.sprint_adi,
        start_date=int(sonuc.baslangic.timestamp()),
        end_date=int(sonuc.bitis.timestamp()),
        total_lines_ai=sonuc.ai_satir,
        total_lines_human=sonuc.insan_satir,
        avg_understanding=sonuc.avg_understanding,
        debt_delta_hours=sonuc.debt_delta_saati,
        health_score=sonuc.health_score,
        db_path=db_path,
    )
