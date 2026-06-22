"""GitHub PR'larına otomatik CodeDNA analiz yorumu bırakır."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

# GitHub API temel URL'i
_GH_API = "https://api.github.com"

# Yorumda kullanılan gizli marker — mevcut CodeDNA yorumunu bulmak için
_YORUM_MARKERI = "<!-- codedna-bot-comment -->"

# Güvenlik: token asla loglanmaz veya hata mesajlarında görünmez
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"


# ---------------------------------------------------------------------------
# Yorum formatlama
# ---------------------------------------------------------------------------

def format_pr_comment(
    scan_sonuclari: list,
    debt_ozeti: Optional[dict] = None,
) -> str:
    """
    Analiz sonuçlarını GitHub Markdown yorumuna dönüştür.

    Okunabilirlik için 2000 karakter altında tutulur.
    ℹ️ teknik borç disclaimer'ı dahil.

    Args:
        scan_sonuclari: FileAnalysisResult listesi
        debt_ozeti: RepoBorcu özeti (opsiyonel)

    Returns:
        Markdown formatında yorum metni
    """
    if not scan_sonuclari:
        return f"{_YORUM_MARKERI}\n## 🧬 CodeDNA Analizi\n\nDeğişen dosya bulunamadı.\n"

    toplam = len(scan_sonuclari)
    ort_ai = sum(s.ai_probability for s in scan_sonuclari) / toplam
    yuksek_risk = [s for s in scan_sonuclari if s.ai_probability >= 0.7]

    # Risk seviyesi
    if ort_ai >= 0.7:
        risk_emoji = "🔴"
        risk_label = "YÜKSEK"
    elif ort_ai >= 0.4:
        risk_emoji = "🟡"
        risk_label = "ORTA"
    else:
        risk_emoji = "🟢"
        risk_label = "DÜŞÜK"

    satirlar = [
        _YORUM_MARKERI,
        "## 🧬 CodeDNA Analizi",
        "",
        f"| Metrik | Değer |",
        f"|--------|-------|",
        f"| Analiz edilen dosya | {toplam} |",
        f"| Ort. AI olasılığı | %{ort_ai * 100:.0f} |",
        f"| Risk seviyesi | {risk_emoji} {risk_label} |",
        f"| Yüksek riskli dosya (≥%70) | {len(yuksek_risk)} |",
        "",
    ]

    # En riskli 3 dosya
    en_riskli = sorted(scan_sonuclari, key=lambda s: s.ai_probability, reverse=True)[:3]
    if en_riskli:
        satirlar.append("### ⚠️ Dikkat Gerektiren Dosyalar")
        satirlar.append("")
        satirlar.append("| Dosya | AI Olasılığı | Karmaşıklık |")
        satirlar.append("|-------|-------------|------------|")
        for s in en_riskli:
            try:
                from pathlib import Path
                kisa_yol = "/".join(Path(s.file_path).parts[-2:])
            except Exception:
                kisa_yol = s.file_path[-40:]
            satirlar.append(
                f"| `{kisa_yol}` | %{s.ai_probability * 100:.0f} | {s.complexity_label} |"
            )
        satirlar.append("")

    # Teknik borç (varsa)
    if debt_ozeti:
        toplam_saat = debt_ozeti.get("toplam_debt_saatleri", 0)
        satirlar.append(f"### 💰 Teknik Borç Tahmini")
        satirlar.append(f"")
        satirlar.append(f"Tahmini borç: **{toplam_saat:.1f} saat**")
        satirlar.append(f"")
        satirlar.append(
            "> ℹ️ *Bu bir tahmin modelidir — anlama skoru, AI olasılığı ve "
            "karmaşıklık ağırlıklarına dayanır. Kesin muhasebe verisi değildir.*"
        )
        satirlar.append("")

    # Footer
    satirlar += [
        "---",
        "<sub>🧬 [CodeDNA](https://github.com/codedna/codedna) · "
        "Detaylı analiz için `codedna dashboard` çalıştırın.</sub>",
    ]

    yorum = "\n".join(satirlar)

    # 2000 karakter limitini aş
    if len(yorum) > 2000:
        ozet = "\n".join(satirlar[:20])
        yorum = (
            ozet + "\n\n"
            "*... (kısaltıldı — tam rapor için CodeDNA dashboard'a bakın)*\n\n"
            f"---\n<sub>🧬 CodeDNA</sub>\n{_YORUM_MARKERI}"
        )

    return yorum


# ---------------------------------------------------------------------------
# GitHub API işlemleri
# ---------------------------------------------------------------------------

def _gh_istek(
    method: str,
    url: str,
    token: str,
    veri: Optional[dict] = None,
) -> dict:
    """
    GitHub API'ye kimlik doğrulamalı istek gönder.

    Güvenlik: token sadece Authorization header'ında kullanılır,
    asla loglanmaz veya hata mesajına eklenmez.
    """
    govde = json.dumps(veri).encode("utf-8") if veri else None
    istek = urllib.request.Request(
        url,
        data=govde,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(istek, timeout=15) as yanit:
            return json.loads(yanit.read())
    except urllib.error.HTTPError as e:
        govde_str = e.read().decode("utf-8", errors="replace")
        # Token'ı hata mesajına ASLA ekleme
        raise RuntimeError(f"GitHub API hatası ({e.code}): {govde_str[:300]}")


def find_existing_comment(
    repo: str,
    pr_number: int,
    token: str,
) -> Optional[int]:
    """
    Mevcut CodeDNA bot yorumunun ID'sini bul (marker ile).

    Args:
        repo: "owner/repo" formatında repo adı
        pr_number: PR numarası
        token: GitHub token

    Returns:
        Yorum ID'si veya yoksa None
    """
    url = f"{_GH_API}/repos/{repo}/issues/{pr_number}/comments?per_page=100"
    try:
        yorumlar = _gh_istek("GET", url, token)
    except Exception:
        return None

    if not isinstance(yorumlar, list):
        return None

    for yorum in yorumlar:
        body = yorum.get("body", "")
        if _YORUM_MARKERI in body:
            return yorum.get("id")

    return None


def post_or_update_comment(
    repo: str,
    pr_number: int,
    body: str,
    token: str,
) -> dict:
    """
    PR'a CodeDNA yorumu gönder veya mevcut yorumu güncelle.

    Spam önleme: Her push'ta yeni yorum açılmaz — mevcut CodeDNA
    yorumu bulunur ve PATCH ile güncellenir. Yoksa yeni POST yapılır.

    Args:
        repo: "owner/repo" formatında repo adı
        pr_number: PR numarası
        body: Yorum metni (Markdown)
        token: GitHub token

    Returns:
        GitHub API yanıtı
    """
    mevcut_id = find_existing_comment(repo, pr_number, token)

    if mevcut_id:
        # Mevcut yorumu güncelle — spam yaratma
        url = f"{_GH_API}/repos/{repo}/issues/comments/{mevcut_id}"
        return _gh_istek("PATCH", url, token, {"body": body})
    else:
        # İlk defa yorum bırak
        url = f"{_GH_API}/repos/{repo}/issues/{pr_number}/comments"
        return _gh_istek("POST", url, token, {"body": body})


# ---------------------------------------------------------------------------
# GitHub Actions ortamından PR bilgisi otomatik algıla
# ---------------------------------------------------------------------------

def github_actions_pr_bilgisi() -> Optional[tuple[str, int]]:
    """
    GitHub Actions ortamından repo adı ve PR numarasını otomatik algıla.

    GITHUB_REPOSITORY ve GITHUB_EVENT_PATH ortam değişkenlerini kullanır.

    Returns:
        (repo, pr_number) çifti veya algılanamıyorsa None
    """
    repo = os.environ.get("GITHUB_REPOSITORY")
    event_path = os.environ.get("GITHUB_EVENT_PATH")

    if not repo or not event_path:
        return None

    try:
        with open(event_path, encoding="utf-8") as f:
            event_veri = json.load(f)
        pr_number = (
            event_veri.get("pull_request", {}).get("number")
            or event_veri.get("number")
        )
        if pr_number:
            return repo, int(pr_number)
    except Exception:
        pass

    return None
