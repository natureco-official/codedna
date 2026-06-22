"""Kritik modüller için anlama eşiği izleme — kod sahipliği sigortası."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from codedna.db import get_connection

# Durum sabitleri
_DURUM_IHLAL = "İHLAL"
_DURUM_GUVENLI = "GÜVENLİ"
_DURUM_BILINMIYOR = "BİLİNMİYOR"

# Aynı modül için uyarılar arası minimum süre (spam önleme, saniye)
_MIN_UYARI_ARASI = 3600  # 1 saat


@dataclass
class ModulDurumu:
    """Tek korumalı modülün anlık durumu."""

    dosya_yolu: str
    etiket: str
    esik: float
    mevcut_skor: Optional[float]
    durum: str   # İHLAL / GÜVENLİ / BİLİNMİYOR
    aktif: bool


def protect_module(
    file_path: str,
    threshold: float,
    label: str,
    author: str,
    db_path: Path,
) -> int:
    """
    Bir dosyayı korumalı modül olarak işaretle.

    Args:
        file_path: Korunacak dosyanın yolu
        threshold: Minimum anlama skoru eşiği (1.0–5.0)
        label: İnsan okunabilir etiket (örn. "Ödeme Sistemi")
        author: Korumayı ekleyen kişi
        db_path: SQLite veritabanı yolu

    Returns:
        Yeni kaydın id'si
    """
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO protected_modules
                (file_path, min_understanding_threshold, label, added_by, added_at, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(file_path) DO UPDATE SET
                min_understanding_threshold = excluded.min_understanding_threshold,
                label     = excluded.label,
                added_by  = excluded.added_by,
                added_at  = excluded.added_at,
                is_active = 1
            """,
            (file_path, threshold, label, author, int(time.time())),
        )
        return cur.lastrowid or 0


def unprotect_module(file_path: str, db_path: Path) -> bool:
    """
    Korumayı kaldır (is_active = 0 yap, kaydı silme).

    Args:
        file_path: Koruma kaldırılacak dosya yolu
        db_path: SQLite veritabanı yolu

    Returns:
        Kayıt bulunup güncellendiyse True
    """
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "UPDATE protected_modules SET is_active = 0 WHERE file_path = ?",
            (file_path,),
        )
        return cur.rowcount > 0


def _dosya_mevcut_skoru(file_path: str, db_path: Path) -> Optional[float]:
    """DB'den dosyanın en güncel anlama skorunu çek."""
    try:
        with get_connection(db_path) as conn:
            row = conn.execute(
                """
                SELECT fs.understanding_score
                FROM file_scores fs
                JOIN commits c ON fs.commit_hash = c.commit_hash
                WHERE fs.file_path = ? AND fs.understanding_score IS NOT NULL
                ORDER BY c.timestamp DESC
                LIMIT 1
                """,
                (file_path,),
            ).fetchone()
        return float(row["understanding_score"]) if row else None
    except Exception:
        return None


def check_protected_modules(db_path: Path) -> list[ModulDurumu]:
    """
    Tüm aktif korumalı modülleri kontrol et, anlama eşiğini aşıp aşmadığını belirle.

    Returns:
        ModulDurumu listesi
    """
    try:
        with get_connection(db_path) as conn:
            kayitlar = conn.execute(
                """
                SELECT file_path, min_understanding_threshold, label, is_active
                FROM protected_modules
                WHERE is_active = 1
                ORDER BY label
                """
            ).fetchall()
    except Exception:
        return []

    sonuclar: list[ModulDurumu] = []
    for k in kayitlar:
        mevcut = _dosya_mevcut_skoru(k["file_path"], db_path)

        if mevcut is None:
            durum = _DURUM_BILINMIYOR
        elif mevcut >= k["min_understanding_threshold"]:
            durum = _DURUM_GUVENLI
        else:
            durum = _DURUM_IHLAL

        sonuclar.append(
            ModulDurumu(
                dosya_yolu=k["file_path"],
                etiket=k["label"] or k["file_path"],
                esik=k["min_understanding_threshold"],
                mevcut_skor=round(mevcut, 2) if mevcut is not None else None,
                durum=durum,
                aktif=bool(k["is_active"]),
            )
        )

    return sonuclar


def get_violations(db_path: Path) -> list[ModulDurumu]:
    """
    Sadece eşik altına düşmüş (İHLAL durumundaki) modülleri döndür.

    Returns:
        İhlaldeki ModulDurumu listesi
    """
    return [m for m in check_protected_modules(db_path) if m.durum == _DURUM_IHLAL]


def ihlal_uyarisi_goster(db_path: Path) -> list[str]:
    """
    Post-commit hook için ihlal uyarılarını döndür.
    Spam önlemek için son 1 saat içinde uyarı verilen modülleri atla.

    Returns:
        Uyarı mesajı listesi (boşsa ihlal yok)
    """
    ihlaller = get_violations(db_path)
    if not ihlaller:
        return []

    su_an = int(time.time())
    uyarilar: list[str] = []

    for ihlal in ihlaller:
        # Son uyarı zamanını kontrol et
        try:
            with get_connection(db_path) as conn:
                row = conn.execute(
                    "SELECT last_alert_at FROM protected_modules WHERE file_path = ?",
                    (ihlal.dosya_yolu,),
                ).fetchone()
            son_uyari = row["last_alert_at"] if row and row["last_alert_at"] else 0
        except Exception:
            son_uyari = 0

        if su_an - son_uyari < _MIN_UYARI_ARASI:
            continue

        # Uyarı zamanını güncelle
        try:
            with get_connection(db_path) as conn:
                conn.execute(
                    "UPDATE protected_modules SET last_alert_at = ? WHERE file_path = ?",
                    (su_an, ihlal.dosya_yolu),
                )
        except Exception:
            pass

        skor_str = f"{ihlal.mevcut_skor:.1f}" if ihlal.mevcut_skor else "?"
        uyarilar.append(
            f"⚠️  UYARI: {ihlal.dosya_yolu} artık güvenle değiştirilemiyor "
            f"(anlama: {skor_str} < eşik: {ihlal.esik:.1f})"
        )

    return uyarilar
