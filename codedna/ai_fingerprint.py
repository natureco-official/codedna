"""
Farklı AI kod asistanlarının bıraktığı örüntüleri ayırt eder.

ÖNEMLİ UYARI:
  Bu kesin bir tespit DEĞİL — örüntü tabanlı sezgisel bir TAHMİN modelidir.
  Sonuçlar yanlış pozitif/negatif içerebilir. Kesinlik iddia edilmez.
  Kullanıcıya bu bağlamda sunulmalıdır.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from codedna.db import get_connection


# ---------------------------------------------------------------------------
# Araç örüntü tanımları — sezgisel, savunulabilir ama kesin değil
# ---------------------------------------------------------------------------

# Her araç için ağırlıklı örüntü listesi: (regex_pattern, ağırlık)
_ARAC_ORNUNTULERI: dict[str, list[tuple[str, float]]] = {
    "copilot": [
        # GitHub Copilot: kısa, özlü satır içi yorumlar, tip bildirimleri yok
        (r"#\s+[A-Z][a-z].{5,40}$", 0.15),           # tek satır başlık yorum
        (r"def \w+\([^)]{0,30}\):\s*$", 0.10),        # parametresiz/minimal fonksiyon
        (r"#\s+TODO:", 0.10),                          # TODO yorumları
        (r"^\s{4}pass\s*$", 0.08),                     # pass ile biten fonksiyonlar
        (r"return \w+\.get\(", 0.07),                  # .get() pattern
    ],
    "cursor": [
        # Cursor: detaylı docstring, tip ipucu zenginliği
        (r'"""[\s\S]{20,200}"""', 0.20),               # uzun docstring
        (r":\s*(str|int|float|bool|list|dict|Optional)", 0.15),  # tip ipuçları
        (r"->.*:\s*$", 0.12),                          # dönüş tipi bildirimi
        (r"from typing import", 0.10),                 # typing modülü
        (r"@dataclass", 0.10),                         # dataclass kullanımı
    ],
    "claude": [
        # Claude: yapılandırılmış çok satırlı açıklamalar, Türkçe/çok dilli yorum
        (r"#\s+\d+\.\s+\w", 0.18),                    # numaralı adım yorumları
        (r"\"\"\"[\s\S]*Args:[\s\S]*Returns:", 0.20),  # Args/Returns docstring
        (r"#\s+─{3,}", 0.15),                          # ayırıcı çizgi yorumlar
        (r"raise \w+Error\(f[\"']", 0.10),             # f-string hata mesajları
        (r"from __future__ import annotations", 0.12), # modern annotation
    ],
}

# Minimum güven eşiği — altındaysa "unknown" döndür
_MIN_GUVEN = 0.15


@dataclass
class AIAracTahmini:
    """Tek dosya için AI araç tahmini."""

    arac: str              # "copilot" | "cursor" | "claude" | "unknown"
    guven: float           # 0.0–1.0
    puan_detayi: dict[str, float]  # araç → ham puan
    uyari: str = (
        "Bu tespit örüntü tabanlı bir tahmindir — kesin değildir."
    )


def guess_ai_tool(file_path: str, code: str) -> AIAracTahmini:
    """
    Dosya için olası AI aracı tahmini ve güven skoru döndür.

    Strateji:
      Her araç için tanımlı regex örüntüleri koda uygulanır, ağırlıklı
      eşleşme sayısına göre toplam puan hesaplanır. En yüksek puanlı
      araç, minimum güven eşiğini geçiyorsa seçilir.

    Args:
        file_path: Dosya yolu (uzantı filtresi için kullanılır)
        code: Dosyanın kaynak kodu

    Returns:
        AIAracTahmini nesnesi
    """
    satirlar = code.splitlines()
    puan: dict[str, float] = {arac: 0.0 for arac in _ARAC_ORNUNTULERI}

    for arac, ornuntular in _ARAC_ORNUNTULERI.items():
        for desen, agirlik in ornuntular:
            eslesme_sayisi = sum(
                1 for satir in satirlar if re.search(desen, satir)
            )
            # Satır sayısına normalize et (büyük dosyalarda haksız avantajı engelle)
            norm = eslesme_sayisi / max(len(satirlar), 1)
            puan[arac] += norm * agirlik * 10  # 0-10 arası ölçek

    # Normalize et — toplam puana göre güven hesapla
    toplam = sum(puan.values())
    if toplam < 0.01:
        return AIAracTahmini(
            arac="unknown",
            guven=0.0,
            puan_detayi={k: round(v, 3) for k, v in puan.items()},
        )

    en_iyi_arac = max(puan, key=lambda k: puan[k])
    guven = puan[en_iyi_arac] / toplam

    # Minimum eşiği geçemiyen → unknown
    if guven < _MIN_GUVEN:
        en_iyi_arac = "unknown"

    return AIAracTahmini(
        arac=en_iyi_arac,
        guven=round(guven, 3),
        puan_detayi={k: round(v, 3) for k, v in puan.items()},
    )


def analyze_repo_tools(
    repo_path: Path,
    db_path: Path,
) -> dict[str, dict[str, float]]:
    """
    Repo genelinde araç bazlı dosya analizi yap ve sonuçları DB'ye kaydet.

    Returns:
        {arac: {"dosya_sayisi": N, "avg_ai_probability": X}} sözlüğü
    """
    from codedna.scorer import scan_repository
    from codedna.db import get_connection

    desteklenen = {".py", ".js", ".jsx", ".ts", ".tsx"}
    sonuclar = scan_repository(repo_path, max_files=200)

    # Araç sayaçları
    arac_istatistik: dict[str, dict[str, list]] = {
        "copilot": {"ai_prob": [], "understanding": []},
        "cursor":  {"ai_prob": [], "understanding": []},
        "claude":  {"ai_prob": [], "understanding": []},
        "unknown": {"ai_prob": [], "understanding": []},
    }

    for sonuc in sonuclar:
        if Path(sonuc.file_path).suffix.lower() not in desteklenen:
            continue
        try:
            kod = Path(sonuc.file_path).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        tahmin = guess_ai_tool(sonuc.file_path, kod)

        # DB'ye kaydet — en son file_score kaydını güncelle
        try:
            with get_connection(db_path) as conn:
                conn.execute(
                    """
                    UPDATE file_scores
                    SET ai_tool_guess = ?
                    WHERE file_path = ?
                      AND id = (
                          SELECT id FROM file_scores
                          WHERE file_path = ?
                          ORDER BY id DESC LIMIT 1
                      )
                    """,
                    (tahmin.arac, sonuc.file_path, sonuc.file_path),
                )
        except Exception:
            pass

        if tahmin.arac in arac_istatistik:
            arac_istatistik[tahmin.arac]["ai_prob"].append(sonuc.ai_probability)
        else:
            arac_istatistik["unknown"]["ai_prob"].append(sonuc.ai_probability)

    # DB'den anlama skorlarını araç bazlı topla
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(
                """
                SELECT fs.ai_tool_guess, fs.understanding_score
                FROM file_scores fs
                WHERE fs.ai_tool_guess IS NOT NULL
                  AND fs.understanding_score IS NOT NULL
                """
            ).fetchall()
            for r in rows:
                arac = r["ai_tool_guess"] or "unknown"
                if arac in arac_istatistik:
                    arac_istatistik[arac]["understanding"].append(
                        float(r["understanding_score"])
                    )
    except Exception:
        pass

    # Sonuçları hesapla
    cikti: dict[str, dict[str, float]] = {}
    for arac, veri in arac_istatistik.items():
        if not veri["ai_prob"]:
            continue
        avg_ai = sum(veri["ai_prob"]) / len(veri["ai_prob"])
        avg_und = (
            sum(veri["understanding"]) / len(veri["understanding"])
            if veri["understanding"] else None
        )
        cikti[arac] = {
            "dosya_sayisi": len(veri["ai_prob"]),
            "avg_ai_probability": round(avg_ai, 3),
            "avg_understanding": round(avg_und, 2) if avg_und is not None else None,
        }

    return cikti


def compare_tools_in_repo(repo_path: Path, db_path: Path) -> dict:
    """
    Repo genelinde araç bazlı ortalama anlama skoru ve AI olasılığı karşılaştırması.

    Returns:
        {"copilot": {...}, "cursor": {...}, ...} sözlüğü
    """
    return analyze_repo_tools(repo_path, db_path)
