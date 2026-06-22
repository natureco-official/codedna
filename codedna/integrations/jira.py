"""Jira sprint verilerini CodeDNA sprint kayıtlarıyla eşleştirir."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Webhook secret dosyası
_SECRET_DOSYASI = Path.home() / ".codedna" / "jira_secret.txt"


# ---------------------------------------------------------------------------
# Webhook Secret Yönetimi
# ---------------------------------------------------------------------------

def get_or_create_secret() -> str:
    """
    Jira webhook secret'ını oku veya yoksa yeni oluştur.

    Returns:
        Hex formatında 32-byte secret
    """
    if _SECRET_DOSYASI.exists():
        return _SECRET_DOSYASI.read_text().strip()
    secret = secrets.token_hex(32)
    _SECRET_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    _SECRET_DOSYASI.write_text(secret)
    return secret


def rotate_secret() -> str:
    """Webhook secret'ı yenile ve yeni değeri döndür."""
    yeni = secrets.token_hex(32)
    _SECRET_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    _SECRET_DOSYASI.write_text(yeni)
    return yeni


def verify_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    """
    Jira webhook imzasını HMAC-SHA256 ile doğrula.

    Jira imzası formatı: "sha256=<hex_digest>"

    Args:
        payload_bytes: Ham HTTP body
        signature_header: X-Hub-Signature-256 başlık değeri
        secret: Webhook secret

    Returns:
        İmza geçerliyse True
    """
    if not signature_header.startswith("sha256="):
        return False
    beklenen_imza = signature_header[7:]
    hesaplanan = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(hesaplanan, beklenen_imza)


# ---------------------------------------------------------------------------
# Webhook İşleme
# ---------------------------------------------------------------------------

def handle_jira_webhook(payload: dict[str, Any], db_path: Path) -> dict[str, Any]:
    """
    Jira webhook payload'unu işle, sprint kaydı oluştur/güncelle.

    Desteklenen event türleri:
      - sprint_started:  Yeni sprint başladı → kayıt oluştur
      - sprint_closed:   Sprint kapandı → sağlık skoru hesapla + güncelle

    Args:
        payload: Jira webhook JSON payload'u
        db_path: SQLite veritabanı yolu

    Returns:
        İşlem sonucu sözlüğü
    """
    event_turu = payload.get("webhookEvent", "")
    sprint_verisi = payload.get("sprint", {})

    if not sprint_verisi:
        return {"durum": "atlandı", "neden": "sprint verisi yok"}

    sprint_adi = sprint_verisi.get("name", "Jira Sprint")
    baslangic_str = sprint_verisi.get("startDate") or sprint_verisi.get("activatedDate")
    bitis_str = sprint_verisi.get("endDate") or sprint_verisi.get("completeDate")

    # Tarihleri parse et
    baslangic = _tarih_parse(baslangic_str)
    bitis = _tarih_parse(bitis_str)

    if not baslangic or not bitis:
        return {"durum": "hata", "neden": "tarih bilgisi eksik"}

    if event_turu in ("sprint_started", "jira:sprint_created"):
        # Sprint başladı — kayıt oluştur (sağlık skoru hesaplanmadı henüz)
        from codedna.db import save_sprint
        sprint_id = save_sprint(
            sprint_name=sprint_adi,
            start_date=int(baslangic.timestamp()),
            end_date=int(bitis.timestamp()),
            total_lines_ai=0,
            total_lines_human=0,
            avg_understanding=None,
            debt_delta_hours=None,
            health_score=None,
            db_path=db_path,
        )
        return {
            "durum": "oluşturuldu",
            "sprint_id": sprint_id,
            "sprint_adi": sprint_adi,
        }

    elif event_turu in ("sprint_closed", "jira:sprint_completed"):
        # Sprint kapandı — sağlık skoru hesapla
        from codedna.sprint_health import calculate_sprint_health, save_sprint_result
        from codedna.git_hook import find_git_root

        repo_koku = find_git_root() or Path.cwd()
        try:
            sonuc = calculate_sprint_health(repo_koku, db_path, baslangic, bitis, sprint_adi)
            sprint_id = save_sprint_result(sonuc, db_path)
            return {
                "durum": "tamamlandı",
                "sprint_id": sprint_id,
                "sprint_adi": sprint_adi,
                "health_score": sonuc.health_score,
                "durum_etiketi": sonuc.durum,
            }
        except Exception as e:
            return {"durum": "hata", "neden": str(e)}

    return {"durum": "atlandı", "neden": f"desteklenmeyen event: {event_turu}"}


def _tarih_parse(tarih_str: Optional[str]) -> Optional[datetime]:
    """
    Jira tarih string'lerini datetime'a çevir.
    Desteklenen formatlar: ISO 8601 ile çeşitli varyantlar.
    """
    if not tarih_str:
        return None
    formatlar = [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formatlar:
        try:
            return datetime.strptime(tarih_str[:len(fmt) + 5], fmt)
        except ValueError:
            continue
    return None
