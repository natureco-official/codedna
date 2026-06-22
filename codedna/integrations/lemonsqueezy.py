"""Lemon Squeezy checkout ve abonelik webhook entegrasyonu."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Ortam değişkenleri — koda gömülmez
# ---------------------------------------------------------------------------

LEMONSQUEEZY_API_KEY = os.environ.get("LEMONSQUEEZY_API_KEY")
LEMONSQUEEZY_WEBHOOK_SECRET = os.environ.get("LEMONSQUEEZY_WEBHOOK_SECRET")
LEMONSQUEEZY_STORE_ID = os.environ.get("LEMONSQUEEZY_STORE_ID")

# Plan → Lemon Squeezy variant ID eşlemesi (gerçek ID'ler .env'den)
PLAN_VARIANT_MAP: dict[str, Optional[str]] = {
    "pro":        os.environ.get("LS_VARIANT_PRO"),
    "team":       os.environ.get("LS_VARIANT_TEAM"),
    "enterprise": os.environ.get("LS_VARIANT_ENTERPRISE"),
}

# Lemon Squeezy API temel URL'i
_LS_API_BASE = "https://api.lemonsqueezy.com/v1"


# ---------------------------------------------------------------------------
# Webhook imza doğrulama
# ---------------------------------------------------------------------------

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Lemon Squeezy webhook imzasını HMAC-SHA256 ile doğrula.

    Lemon Squeezy, X-Signature header'ında hex digest gönderir.
    hmac.compare_digest ile timing-safe karşılaştırma yapılır.

    Args:
        payload: Ham HTTP body (bytes)
        signature: X-Signature header değeri

    Returns:
        İmza geçerliyse True
    """
    secret = LEMONSQUEEZY_WEBHOOK_SECRET
    if not secret:
        return False

    hesaplanan = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(hesaplanan, signature)


# ---------------------------------------------------------------------------
# Checkout URL oluşturma
# ---------------------------------------------------------------------------

def create_checkout_url(
    plan: str,
    user_email: str,
    user_id: int,
) -> str:
    """
    Lemon Squeezy Checkout API'sine istek at ve hosted checkout URL'ini döndür.

    custom_data içine user_id gömülür — webhook'ta hangi kullanıcıya ait
    olduğunu eşleştirmek için kullanılır.

    Dokümantasyon: https://docs.lemonsqueezy.com/api/checkouts

    Args:
        plan: "pro" | "team" | "enterprise"
        user_email: Kullanıcının e-posta adresi (checkout'ta ön doldurulur)
        user_id: Kullanıcı ID'si (webhook eşleştirmesi için)

    Returns:
        Checkout URL string'i

    Raises:
        ValueError: API anahtarı veya variant ID eksikse
        RuntimeError: API isteği başarısız olursa
    """
    import urllib.request

    api_key = LEMONSQUEEZY_API_KEY
    store_id = LEMONSQUEEZY_STORE_ID
    variant_id = PLAN_VARIANT_MAP.get(plan)

    if not api_key:
        raise ValueError(
            "LEMONSQUEEZY_API_KEY ortam değişkeni tanımlanmamış. "
            ".env.example dosyasına bakın."
        )
    if not store_id:
        raise ValueError("LEMONSQUEEZY_STORE_ID ortam değişkeni tanımlanmamış.")
    if not variant_id:
        raise ValueError(
            f"LS_VARIANT_{plan.upper()} ortam değişkeni tanımlanmamış."
        )

    istek_govdesi = json.dumps({
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "email": user_email,
                    "custom": {"user_id": str(user_id)},
                },
            },
            "relationships": {
                "store": {
                    "data": {"type": "stores", "id": str(store_id)}
                },
                "variant": {
                    "data": {"type": "variants", "id": str(variant_id)}
                },
            },
        }
    }).encode("utf-8")

    istek = urllib.request.Request(
        f"{_LS_API_BASE}/checkouts",
        data=istek_govdesi,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(istek, timeout=10) as yanit:
            veri = json.loads(yanit.read())
            return veri["data"]["attributes"]["url"]
    except urllib.error.HTTPError as e:
        hata_govdesi = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Lemon Squeezy API hatası ({e.code}): {hata_govdesi}"
        )
    except Exception as e:
        raise RuntimeError(f"Checkout URL oluşturulamadı: {e}")


# ---------------------------------------------------------------------------
# Webhook event işleme
# ---------------------------------------------------------------------------

# LS event → (plan, subscription_status) eşlemesi
_EVENT_DURUM_MAP: dict[str, tuple[Optional[str], str]] = {
    "subscription_created":        (None,   "active"),     # plan custom_data'dan alınır
    "subscription_updated":        (None,   "active"),
    "subscription_cancelled":      (None,   "cancelled"),  # plan hemen düşürülmez
    "subscription_expired":        ("free", "none"),
    "subscription_payment_failed": (None,   "past_due"),
}


def handle_subscription_webhook(
    payload: dict,
    db_path: Path,
) -> dict:
    """
    Lemon Squeezy webhook event'lerini işle ve kullanıcı planını güncelle.

    Tüm event'lerde custom_data.user_id ile kullanıcı eşleştirilir.

    Args:
        payload: Webhook JSON payload'u
        db_path: Auth DB yolu

    Returns:
        İşlem sonucu sözlüğü
    """
    from codedna.auth import update_user_plan, init_auth_db

    init_auth_db(db_path)

    event_turu = payload.get("meta", {}).get("event_name", "")
    if event_turu not in _EVENT_DURUM_MAP:
        return {"durum": "atlandı", "event": event_turu}

    # Kullanıcı ID'sini custom_data'dan al
    custom_data = payload.get("meta", {}).get("custom_data", {})
    user_id_str = custom_data.get("user_id") or custom_data.get("user_id")
    if not user_id_str:
        return {"durum": "hata", "neden": "custom_data.user_id eksik"}

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        return {"durum": "hata", "neden": f"Geçersiz user_id: {user_id_str!r}"}

    # Abonelik verilerini al
    abonelik = payload.get("data", {}).get("attributes", {})
    customer_id = str(abonelik.get("customer_id", "")) or None
    subscription_id = str(payload.get("data", {}).get("id", "")) or None

    # Planı belirle
    yeni_plan, yeni_durum = _EVENT_DURUM_MAP[event_turu]

    # subscription_created/updated için plan variant'tan belirle
    if yeni_plan is None:
        variant_id = str(abonelik.get("variant_id", ""))
        # Variant ID → plan eşlemesi (ters yön)
        for plan_adi, vid in PLAN_VARIANT_MAP.items():
            if vid and vid == variant_id:
                yeni_plan = plan_adi
                break
        if yeni_plan is None:
            yeni_plan = "pro"  # bilinmeyen variant → pro varsayılan

    update_user_plan(
        user_id=user_id,
        plan=yeni_plan,
        subscription_status=yeni_durum,
        customer_id=customer_id,
        subscription_id=subscription_id,
        db_path=db_path,
    )

    return {
        "durum": "güncellendi",
        "user_id": user_id,
        "yeni_plan": yeni_plan,
        "subscription_status": yeni_durum,
        "event": event_turu,
    }
