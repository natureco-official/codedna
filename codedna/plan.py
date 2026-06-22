"""Plan yönetimi — lisans anahtarı ile plan seviyesi belirlenir."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Optional


class Plan(str, Enum):
    """Kullanılabilir plan seviyeleri."""

    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


# Lisans dosyası yolu
_LISANS_YOLU = Path.home() / ".codedna" / "license.json"

# Özellik → izin verilen planlar eşlemesi
_OZELLIK_PLANLARI: dict[str, list[Plan]] = {
    "unlimited_repos":  [Plan.PRO, Plan.TEAM, Plan.ENTERPRISE],
    "unlimited_files":  [Plan.PRO, Plan.TEAM, Plan.ENTERPRISE],
    "history_90d":      [Plan.PRO, Plan.TEAM, Plan.ENTERPRISE],
    "history_365d":     [Plan.TEAM, Plan.ENTERPRISE],
    "dashboard_access": [Plan.PRO, Plan.TEAM, Plan.ENTERPRISE],
    "github_actions":   [Plan.PRO, Plan.TEAM, Plan.ENTERPRISE],
    "slack_notify":     [Plan.TEAM, Plan.ENTERPRISE],
    "bus_factor":       [Plan.TEAM, Plan.ENTERPRISE],
    "sprint_health":    [Plan.TEAM, Plan.ENTERPRISE],
    "ai_comparison":    [Plan.ENTERPRISE],
    "interview_tool":   [Plan.ENTERPRISE],
}

# Tüm planlarda erişilebilen özellikler (varsayılan)
_HERKESE_ACIK: set[str] = {
    "scan", "history_7d", "cli_basic",
}


def get_current_plan() -> Plan:
    """
    ~/.codedna/license.json dosyasından plan oku.

    Dosya yoksa FREE döndür.
    Format: {"plan": "pro", "key": "...", "expires": "2027-01-01"}
    """
    if not _LISANS_YOLU.exists():
        return Plan.FREE
    try:
        veri = json.loads(_LISANS_YOLU.read_text(encoding="utf-8"))
        return Plan(veri.get("plan", "free"))
    except Exception:
        return Plan.FREE


def is_feature_available(feature: str, plan: Optional[Plan] = None) -> bool:
    """
    Verilen özelliğin mevcut planda kullanılabilir olup olmadığını kontrol et.

    Args:
        feature: Kontrol edilecek özellik adı
        plan: Plan seviyesi (None ise mevcut plan okunur)

    Returns:
        Özellik kullanılabilirse True
    """
    if plan is None:
        plan = get_current_plan()

    # Herkese açık özellikler
    if feature in _HERKESE_ACIK:
        return True

    return plan in _OZELLIK_PLANLARI.get(
        feature,
        [Plan.FREE, Plan.PRO, Plan.TEAM, Plan.ENTERPRISE],
    )


def activate_license(key: str) -> Plan:
    """
    Lisans anahtarını doğrula ve aktif et.

    Gerçek doğrulama Faz 9'da API üzerinden yapılacak.
    Şimdilik anahtar formatına göre plan belirler:
      - 'CDNA-PRO-...'  → pro
      - 'CDNA-TEAM-...' → team
      - 'CDNA-ENT-...'  → enterprise

    Args:
        key: Lisans anahtarı

    Returns:
        Aktif edilen plan seviyesi
    """
    anahtar = key.upper().strip()
    if anahtar.startswith("CDNA-PRO"):
        plan = Plan.PRO
    elif anahtar.startswith("CDNA-TEAM"):
        plan = Plan.TEAM
    elif anahtar.startswith("CDNA-ENT"):
        plan = Plan.ENTERPRISE
    else:
        raise ValueError(f"Geçersiz lisans anahtarı formatı: {key!r}")

    # Lisans dosyasını yaz
    _LISANS_YOLU.parent.mkdir(parents=True, exist_ok=True)
    _LISANS_YOLU.write_text(
        json.dumps({"plan": plan.value, "key": anahtar}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return plan


def get_plan_limits() -> dict[str, object]:
    """Mevcut planın limit değerlerini döndür."""
    plan = get_current_plan()
    limitler: dict[str, object] = {
        Plan.FREE: {
            "max_repos": 1, "max_files_scan": 50, "history_days": 7,
            "dashboard_access": False, "github_actions": False,
        },
        Plan.PRO: {
            "max_repos": -1, "max_files_scan": -1, "history_days": 90,
            "dashboard_access": True, "github_actions": True,
        },
        Plan.TEAM: {
            "max_repos": -1, "max_files_scan": -1, "history_days": 365,
            "dashboard_access": True, "github_actions": True,
            "slack_notify": True, "bus_factor": True,
        },
        Plan.ENTERPRISE: {
            "max_repos": -1, "max_files_scan": -1, "history_days": -1,
            "dashboard_access": True, "github_actions": True,
            "slack_notify": True, "bus_factor": True,
            "sprint_health": True, "ai_comparison": True,
        },
    }
    return limitler.get(plan, limitler[Plan.FREE])  # type: ignore[return-value]
