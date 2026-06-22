"""CodeDNA FastAPI REST servisi."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from codedna import __version__
from codedna.db import (
    get_commit_history,
    get_db_path,
    get_file_scores_for_commit,
    init_db,
    update_understanding_score,
)
from codedna.scorer import scan_repository
from codedna.git_hook import find_git_root

# ---------------------------------------------------------------------------
# Ortam değişkenlerinden yapılandırma
# ---------------------------------------------------------------------------

def _repo_yolu() -> Path:
    """Ortam değişkeninden veya otomatik bularak repo yolunu döndür."""
    env = os.environ.get("CODEDNA_REPO_PATH")
    if env:
        return Path(env).resolve()
    return find_git_root() or Path.cwd()


def _db_yolu() -> Path:
    """Ortam değişkeninden veya repo köküne göre DB yolunu döndür."""
    env = os.environ.get("CODEDNA_DB_PATH")
    if env:
        return Path(env).resolve()
    return get_db_path(_repo_yolu())


# ---------------------------------------------------------------------------
# FastAPI uygulaması — lifespan pattern (startup deprecated değil)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama yaşam döngüsü — başlangıçta DB'yi hazırla."""
    init_db(_db_yolu())
    yield


app = FastAPI(
    title="CodeDNA API",
    description="AI kod şeffaflık aracı — REST API",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — dashboard veya harici araçlar için tam açık
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic modelleri
# ---------------------------------------------------------------------------
class SurveyGirdi(BaseModel):
    """Anlama anketi giriş verisi."""
    skor_1: float  # Bu değişikliği 3 ay sonra açıklayabilir misin? [1-5]
    skor_2: float  # Bir hata çıksa debug edebilir misin? [1-5]
    skor_3: float  # Başkası sorsa, nasıl çalıştığını anlatabilir misin? [1-5]


# ---------------------------------------------------------------------------
# Endpoint'ler
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Sistem"])
async def saglik_kontrolu() -> dict:
    """Servisin ayakta olduğunu doğrula."""
    return {
        "durum": "çalışıyor",
        "versiyon": __version__,
        "zaman": datetime.utcnow().isoformat(),
    }


@app.get("/repo/summary", tags=["Repo"])
async def repo_ozeti() -> dict:
    """Repo geneli özet: ortalama AI skoru, toplam commit, risk seviyesi."""
    db = _db_yolu()
    init_db(db)

    commitler = get_commit_history(limit=1000, db_path=db)

    if not commitler:
        return {
            "toplam_commit": 0,
            "ortalama_ai_skoru": None,
            "risk_seviyesi": "BİLİNMİYOR",
            "anlama_skoru_olan_commit": 0,
            "ortalama_anlama_skoru": None,
        }

    toplam = len(commitler)
    anlama_skorlari = [
        float(c["understanding_score"])
        for c in commitler
        if c["understanding_score"] is not None
    ]

    # Dosya skorlarından ortalama AI olasılığını hesapla
    tum_ai_skorlari: list[float] = []
    for commit in commitler[:50]:  # Son 50 commit yeterli
        dosyalar = get_file_scores_for_commit(commit["commit_hash"], db_path=db)
        for d in dosyalar:
            if d["ai_probability"] is not None:
                tum_ai_skorlari.append(float(d["ai_probability"]))

    ort_ai = sum(tum_ai_skorlari) / len(tum_ai_skorlari) if tum_ai_skorlari else None
    ort_anlama = sum(anlama_skorlari) / len(anlama_skorlari) if anlama_skorlari else None

    # Risk seviyesi
    if ort_ai is None:
        risk = "BİLİNMİYOR"
    elif ort_ai >= 0.7:
        risk = "YÜKSEK"
    elif ort_ai >= 0.4:
        risk = "ORTA"
    else:
        risk = "DÜŞÜK"

    return {
        "toplam_commit": toplam,
        "ortalama_ai_skoru": round(ort_ai, 3) if ort_ai is not None else None,
        "ortalama_ai_yuzdesi": round(ort_ai * 100, 1) if ort_ai is not None else None,
        "risk_seviyesi": risk,
        "anlama_skoru_olan_commit": len(anlama_skorlari),
        "ortalama_anlama_skoru": round(ort_anlama, 2) if ort_anlama is not None else None,
    }


@app.get("/repo/files", tags=["Repo"])
async def repo_dosyalari(
    min_risk: float = Query(0.0, ge=0.0, le=1.0, description="Minimum AI olasılığı filtresi"),
    max_dosya: int = Query(200, ge=1, le=1000, description="Maksimum dosya sayısı"),
) -> dict:
    """Tüm desteklenen dosyaları tara ve AI skorlarını döndür."""
    kok = _repo_yolu()

    sonuclar = scan_repository(kok, max_files=max_dosya)

    # Filtrele ve sırala
    if min_risk > 0:
        sonuclar = [s for s in sonuclar if s.ai_probability >= min_risk]
    sonuclar.sort(key=lambda s: s.ai_probability, reverse=True)

    dosyalar = []
    for s in sonuclar:
        # Göreli yol hesapla
        try:
            goreceli = str(Path(s.file_path).relative_to(kok))
        except ValueError:
            goreceli = s.file_path

        dosyalar.append({
            "dosya_yolu": goreceli,
            "ai_olasıligi": round(s.ai_probability, 3),
            "ai_yuzdesi": round(s.ai_probability * 100, 1),
            "karmasiklik_skoru": round(s.complexity_score, 1),
            "karmasiklik_etiketi": s.complexity_label,
            "yorum_orani": round(s.comment_ratio, 3),
            "ortalama_fonksiyon_uzunlugu": round(s.avg_function_length, 1),
            "tek_commit_orani": round(s.single_commit_ratio, 3),
            "toplam_satir": s.total_lines,
            "fonksiyon_sayisi": s.function_count,
        })

    toplam_ai = sum(d["ai_olasıligi"] for d in dosyalar)
    ort_ai = toplam_ai / len(dosyalar) if dosyalar else 0

    return {
        "toplam_dosya": len(dosyalar),
        "ortalama_ai_skoru": round(ort_ai, 3),
        "dosyalar": dosyalar,
    }


@app.get("/commits", tags=["Commit"])
async def commit_listesi(
    limit: int = Query(20, ge=1, le=100, description="Döndürülecek commit sayısı"),
) -> dict:
    """Geçmiş commit listesini döndür."""
    db = _db_yolu()
    init_db(db)
    commitler = get_commit_history(limit=limit, db_path=db)

    liste = []
    for c in commitler:
        liste.append({
            "commit_hash": c["commit_hash"],
            "hash_kisa": c["commit_hash"][:8] if c["commit_hash"] else "",
            "yazar": c["author"],
            "zaman_dam": c["timestamp"],
            "tarih": (
                datetime.fromtimestamp(c["timestamp"]).strftime("%Y-%m-%d %H:%M")
                if c["timestamp"] else None
            ),
            "degisen_dosya_sayisi": c["files_changed"],
            "anlama_skoru": (
                round(float(c["understanding_score"]), 2)
                if c["understanding_score"] is not None else None
            ),
            "olusturulma": c["created_at"],
        })

    return {"toplam": len(liste), "commitler": liste}


@app.get("/commits/{commit_hash}", tags=["Commit"])
async def commit_detayi(commit_hash: str) -> dict:
    """Tek commit detayı ve ilgili dosya skorlarını döndür."""
    db = _db_yolu()
    init_db(db)

    # Tam hash veya kısa hash ile ara
    commitler = get_commit_history(limit=1000, db_path=db)
    bulunan = None
    for c in commitler:
        if c["commit_hash"] and (
            c["commit_hash"] == commit_hash
            or c["commit_hash"].startswith(commit_hash)
        ):
            bulunan = c
            break

    if not bulunan:
        raise HTTPException(
            status_code=404,
            detail=f"'{commit_hash}' hash'li commit bulunamadı.",
        )

    dosyalar = get_file_scores_for_commit(bulunan["commit_hash"], db_path=db)
    dosya_listesi = [
        {
            "dosya_yolu": d["file_path"],
            "ai_olasıligi": round(float(d["ai_probability"]), 3) if d["ai_probability"] is not None else None,
            "karmasiklik_skoru": round(float(d["complexity_score"]), 1) if d["complexity_score"] is not None else None,
            "yorum_orani": round(float(d["comment_ratio"]), 3) if d["comment_ratio"] is not None else None,
            "anlama_skoru": round(float(d["understanding_score"]), 2) if d["understanding_score"] is not None else None,
        }
        for d in dosyalar
    ]

    return {
        "commit_hash": bulunan["commit_hash"],
        "yazar": bulunan["author"],
        "tarih": (
            datetime.fromtimestamp(bulunan["timestamp"]).strftime("%Y-%m-%d %H:%M")
            if bulunan["timestamp"] else None
        ),
        "degisen_dosya_sayisi": bulunan["files_changed"],
        "anlama_skoru": (
            round(float(bulunan["understanding_score"]), 2)
            if bulunan["understanding_score"] is not None else None
        ),
        "dosyalar": dosya_listesi,
    }


@app.post("/survey/{commit_hash}", tags=["Anket"])
async def anket_kaydet(commit_hash: str, girdi: SurveyGirdi) -> dict:
    """Anlama anketi sonucunu kaydet."""
    # Skor doğrulama
    for alan, deger in [("skor_1", girdi.skor_1), ("skor_2", girdi.skor_2), ("skor_3", girdi.skor_3)]:
        if not (1.0 <= deger <= 5.0):
            raise HTTPException(
                status_code=422,
                detail=f"'{alan}' değeri 1 ile 5 arasında olmalıdır, gelen: {deger}",
            )

    ortalama = (girdi.skor_1 + girdi.skor_2 + girdi.skor_3) / 3.0
    db = _db_yolu()
    init_db(db)

    # Commit var mı kontrol et
    commitler = get_commit_history(limit=1000, db_path=db)
    bulunan_hash = None
    for c in commitler:
        if c["commit_hash"] and (
            c["commit_hash"] == commit_hash
            or c["commit_hash"].startswith(commit_hash)
        ):
            bulunan_hash = c["commit_hash"]
            break

    if not bulunan_hash:
        raise HTTPException(
            status_code=404,
            detail=f"'{commit_hash}' hash'li commit bulunamadı.",
        )

    update_understanding_score(bulunan_hash, ortalama, db_path=db)

    return {
        "commit_hash": bulunan_hash,
        "anlama_skoru": round(ortalama, 2),
        "mesaj": "Anlama skoru başarıyla kaydedildi.",
    }


@app.get("/report", tags=["Rapor"])
async def rapor(fmt: str = Query("json", description="Çıktı formatı: 'json' veya 'html'")) -> object:
    """Repo özet raporunu JSON veya HTML olarak döndür."""
    db = _db_yolu()
    init_db(db)
    kok = _repo_yolu()

    # Veri topla
    commitler = get_commit_history(limit=50, db_path=db)
    dosyalar_sonuc = scan_repository(kok, max_files=100)
    dosyalar_sonuc.sort(key=lambda s: s.ai_probability, reverse=True)

    tum_ai = [s.ai_probability for s in dosyalar_sonuc]
    ort_ai = sum(tum_ai) / len(tum_ai) if tum_ai else 0.0

    anlama_skorlari = [
        float(c["understanding_score"])
        for c in commitler
        if c["understanding_score"] is not None
    ]
    ort_anlama = sum(anlama_skorlari) / len(anlama_skorlari) if anlama_skorlari else None

    if ort_ai >= 0.7:
        risk = "YÜKSEK"
    elif ort_ai >= 0.4:
        risk = "ORTA"
    else:
        risk = "DÜŞÜK"

    if fmt == "html":
        html = _rapor_html_olustur(
            repo_adi=kok.name,
            toplam_dosya=len(dosyalar_sonuc),
            ort_ai=ort_ai,
            risk=risk,
            ort_anlama=ort_anlama,
            toplam_commit=len(commitler),
            dosyalar=dosyalar_sonuc,
            commitler=commitler,
            kok=kok,
        )
        return HTMLResponse(content=html)

    # JSON formatı
    return {
        "repo": kok.name,
        "tarih": datetime.utcnow().isoformat(),
        "ozet": {
            "toplam_dosya": len(dosyalar_sonuc),
            "ortalama_ai_skoru": round(ort_ai, 3),
            "risk_seviyesi": risk,
            "toplam_commit": len(commitler),
            "ortalama_anlama_skoru": round(ort_anlama, 2) if ort_anlama else None,
        },
        "dosyalar": [
            {
                "yol": str(Path(s.file_path).relative_to(kok)) if Path(s.file_path).is_relative_to(kok) else s.file_path,
                "ai_yuzdesi": round(s.ai_probability * 100, 1),
                "karmasiklik": s.complexity_label,
                "satir": s.total_lines,
            }
            for s in dosyalar_sonuc[:20]
        ],
    }


# ---------------------------------------------------------------------------
# HTML rapor üretici (Jinja2 yok — f-string)
# ---------------------------------------------------------------------------
def _rapor_html_olustur(
    repo_adi: str,
    toplam_dosya: int,
    ort_ai: float,
    risk: str,
    ort_anlama: Optional[float],
    toplam_commit: int,
    dosyalar: list,
    commitler: list,
    kok: Path,
) -> str:
    """Inline CSS ile sade HTML rapor üret."""
    tarih_str = datetime.now().strftime("%d %B %Y, %H:%M")
    risk_renk = {"YÜKSEK": "#e74c3c", "ORTA": "#f39c12", "DÜŞÜK": "#27ae60"}.get(risk, "#95a5a6")

    anlama_str = f"{ort_anlama:.1f}/5" if ort_anlama is not None else "Veri yok"

    # Dosya satırları
    dosya_satirlari = ""
    for s in dosyalar:
        try:
            yol = str(Path(s.file_path).relative_to(kok))
        except ValueError:
            yol = s.file_path

        yuzde = s.ai_probability * 100
        if yuzde >= 70:
            renk = "#e74c3c"
            emoji = "🔴"
        elif yuzde >= 40:
            renk = "#f39c12"
            emoji = "🟡"
        else:
            renk = "#27ae60"
            emoji = "🟢"

        dosya_satirlari += f"""
        <tr>
            <td style="font-family:monospace;font-size:13px">{yol}</td>
            <td style="color:{renk};font-weight:bold;text-align:center">{emoji} %{yuzde:.0f}</td>
            <td style="text-align:center">{s.complexity_label}</td>
            <td style="text-align:right">{s.total_lines}</td>
            <td style="text-align:right">{s.function_count}</td>
        </tr>"""

    # Commit satırları
    commit_satirlari = ""
    for c in commitler[:20]:
        tarih = (
            datetime.fromtimestamp(c["timestamp"]).strftime("%Y-%m-%d %H:%M")
            if c["timestamp"] else "?"
        )
        anlama = (
            f"{float(c['understanding_score']):.1f}/5"
            if c["understanding_score"] is not None else "—"
        )
        commit_satirlari += f"""
        <tr>
            <td style="font-family:monospace">{(c['commit_hash'] or '')[:8]}</td>
            <td>{c['author'] or '?'}</td>
            <td>{tarih}</td>
            <td style="text-align:right">{c['files_changed'] or 0}</td>
            <td style="text-align:center">{anlama}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🧬 CodeDNA Raporu — {repo_adi}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #0f1117; color: #e2e8f0; padding: 32px; }}
  h1 {{ font-size: 28px; margin-bottom: 4px; }}
  h2 {{ font-size: 18px; margin: 32px 0 12px; color: #94a3b8; text-transform: uppercase;
        letter-spacing: 1px; font-size: 13px; }}
  .subtitle {{ color: #64748b; font-size: 14px; margin-bottom: 32px; }}
  .cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 32px; }}
  .card {{ background: #1e2433; border-radius: 12px; padding: 20px 28px;
           min-width: 160px; flex: 1; border: 1px solid #2d3748; }}
  .card-label {{ font-size: 12px; color: #64748b; text-transform: uppercase;
                 letter-spacing: 1px; margin-bottom: 8px; }}
  .card-value {{ font-size: 28px; font-weight: 700; }}
  table {{ width: 100%; border-collapse: collapse; background: #1e2433;
           border-radius: 12px; overflow: hidden; border: 1px solid #2d3748; }}
  th {{ background: #252d3d; padding: 12px 16px; text-align: left;
        font-size: 12px; text-transform: uppercase; letter-spacing: 1px;
        color: #94a3b8; }}
  td {{ padding: 11px 16px; border-top: 1px solid #2d3748; font-size: 14px; }}
  tr:hover td {{ background: #252d3d; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px;
            font-size: 12px; font-weight: 600; color: white;
            background: {risk_renk}; }}
  footer {{ margin-top: 40px; color: #4a5568; font-size: 12px; text-align: center; }}
</style>
</head>
<body>
<h1>🧬 CodeDNA Raporu</h1>
<p class="subtitle">📁 {repo_adi} &nbsp;·&nbsp; 📅 {tarih_str}</p>

<div class="cards">
  <div class="card">
    <div class="card-label">Toplam Dosya</div>
    <div class="card-value">{toplam_dosya}</div>
  </div>
  <div class="card">
    <div class="card-label">Ort. AI Skoru</div>
    <div class="card-value">%{ort_ai*100:.0f}</div>
  </div>
  <div class="card">
    <div class="card-label">Risk Seviyesi</div>
    <div class="card-value"><span class="badge">{risk}</span></div>
  </div>
  <div class="card">
    <div class="card-label">Toplam Commit</div>
    <div class="card-value">{toplam_commit}</div>
  </div>
  <div class="card">
    <div class="card-label">Ort. Anlama</div>
    <div class="card-value">{anlama_str}</div>
  </div>
</div>

<h2>Dosya Analizi</h2>
<table>
  <thead>
    <tr>
      <th>Dosya</th><th>AI Olasılığı</th><th>Karmaşıklık</th>
      <th style="text-align:right">Satır</th><th style="text-align:right">Fonksiyon</th>
    </tr>
  </thead>
  <tbody>{dosya_satirlari}</tbody>
</table>

<h2>Commit Geçmişi</h2>
<table>
  <thead>
    <tr>
      <th>Hash</th><th>Yazar</th><th>Tarih</th>
      <th style="text-align:right">Dosya</th><th style="text-align:center">Anlama</th>
    </tr>
  </thead>
  <tbody>{commit_satirlari}</tbody>
</table>

<footer>🧬 CodeDNA v{__version__} &nbsp;·&nbsp; codedna raporu otomatik oluşturuldu</footer>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Yardımcı: plan 403 yanıtı
# ---------------------------------------------------------------------------
def _plan_403(ozellik: str, tr_mesaj: str, en_mesaj: str) -> HTTPException:
    """Plan kısıtlaması için standart 403 hatası üret."""
    return HTTPException(
        status_code=403,
        detail={
            "hata": tr_mesaj,
            "error": en_mesaj,
            "ozellik": ozellik,
            "gerekli_plan": "team",
        },
    )


# ---------------------------------------------------------------------------
# Bus Factor endpoint'leri
# ---------------------------------------------------------------------------

@app.get("/bus-factor", tags=["Bus Factor"])
async def bus_factor_listesi(
    max_dosya: int = Query(200, ge=1, le=500, description="Maksimum dosya sayısı"),
) -> dict:
    """Tüm dosyalar için bus factor listesi. Team+ planı gerektirir."""
    from codedna.plan import is_feature_available
    from codedna.bus_factor import calculate_bus_factor

    if not is_feature_available("bus_factor"):
        raise _plan_403(
            "bus_factor",
            "Bu özellik Team planında mevcut.",
            "This feature is available on Team plan.",
        )

    kok = _repo_yolu()
    db = _db_yolu()
    init_db(db)

    sonuclar = calculate_bus_factor(kok, db, max_dosya=max_dosya)

    return {
        "toplam_dosya": len(sonuclar),
        "kritik_sayisi": sum(1 for s in sonuclar if s.risk == "KRİTİK"),
        "riskli_sayisi": sum(1 for s in sonuclar if s.risk == "RİSKLİ"),
        "dosyalar": [
            {
                "dosya_yolu": s.dosya_yolu,
                "bus_factor": s.bus_factor,
                "birincil_sahip": s.birincil_sahip,
                "sahiplik_yuzdesi": s.sahiplik_yuzdesi,
                "risk": s.risk,
                "anlayan_yazarlar": s.anlayan_yazarlar,
                "toplam_satir": s.toplam_satir,
            }
            for s in sonuclar
        ],
    }


@app.get("/bus-factor/critical", tags=["Bus Factor"])
async def bus_factor_kritik() -> dict:
    """Sadece bus_factor=1 olan kritik dosyaları döndür. Team+ planı gerektirir."""
    from codedna.plan import is_feature_available
    from codedna.bus_factor import get_at_risk_files

    if not is_feature_available("bus_factor"):
        raise _plan_403(
            "bus_factor",
            "Bu özellik Team planında mevcut.",
            "This feature is available on Team plan.",
        )

    kok = _repo_yolu()
    db = _db_yolu()
    init_db(db)

    sonuclar = get_at_risk_files(kok, db)

    return {
        "kritik_sayisi": len(sonuclar),
        "dosyalar": [
            {
                "dosya_yolu": s.dosya_yolu,
                "bus_factor": s.bus_factor,
                "birincil_sahip": s.birincil_sahip,
                "sahiplik_yuzdesi": s.sahiplik_yuzdesi,
                "risk": s.risk,
                "toplam_satir": s.toplam_satir,
            }
            for s in sonuclar
        ],
    }


# ---------------------------------------------------------------------------
# Teknik Borç endpoint'leri
# ---------------------------------------------------------------------------

@app.get("/debt/summary", tags=["Teknik Borç"])
async def borclu_ozet(
    rate: float = Query(75.0, ge=1.0, le=1000.0, description="Saatlik maliyet ($/saat)"),
) -> dict:
    """
    Repo geneli teknik borç özeti.
    Free planda dolar tutarları maskelenir.
    """
    from codedna.plan import get_current_plan, Plan
    from codedna.tech_debt import calculate_repo_debt

    kok = _repo_yolu()
    db = _db_yolu()
    init_db(db)

    ozet = calculate_repo_debt(kok, db, hourly_rate=rate)
    mevcut_plan = get_current_plan()
    dolar_gizli = mevcut_plan == Plan.FREE

    en_pahali = []
    for d in ozet.en_pahali_5:
        try:
            goreceli = str(Path(d.dosya_yolu).relative_to(kok))
        except ValueError:
            goreceli = d.dosya_yolu

        en_pahali.append({
            "dosya_yolu": goreceli,
            "debt_saatleri": d.debt_saatleri,
            "aylik_maliyet_usd": None if dolar_gizli else d.aylik_maliyet_usd,
            "risk_seviyesi": d.risk_seviyesi,
        })

    return {
        "toplam_debt_saatleri": ozet.toplam_debt_saatleri,
        "toplam_aylik_maliyet_usd": None if dolar_gizli else ozet.toplam_aylik_maliyet_usd,
        "dolar_gizli": dolar_gizli,
        "saatlik_ucret": rate,
        "toplam_dosya": ozet.toplam_dosya,
        "en_pahali_5": en_pahali,
    }


@app.get("/debt/files", tags=["Teknik Borç"])
async def borclu_dosyalar(
    rate: float = Query(75.0, ge=1.0, le=1000.0, description="Saatlik maliyet ($/saat)"),
    limit: int = Query(20, ge=1, le=100, description="Döndürülecek dosya sayısı"),
) -> dict:
    """
    Dosya bazlı teknik borç listesi, en maliyetliden sıralı.
    Free planda dolar tutarları maskelenir.
    """
    from codedna.plan import get_current_plan, Plan
    from codedna.tech_debt import calculate_repo_debt

    kok = _repo_yolu()
    db = _db_yolu()
    init_db(db)

    ozet = calculate_repo_debt(kok, db, hourly_rate=rate)
    mevcut_plan = get_current_plan()
    dolar_gizli = mevcut_plan == Plan.FREE

    # Tüm dosyaları en pahali'dan sıralı al
    from codedna.tech_debt import calculate_file_debt
    from codedna.scorer import scan_repository

    taranan = scan_repository(kok, max_files=200)
    taranan.sort(key=lambda s: s.ai_probability, reverse=True)

    dosya_listesi = []
    for s in taranan[:limit]:
        borc = calculate_file_debt(s.file_path, db, hourly_rate=rate)
        if borc is None:
            continue
        try:
            goreceli = str(Path(s.file_path).relative_to(kok))
        except ValueError:
            goreceli = s.file_path

        dosya_listesi.append({
            "dosya_yolu": goreceli,
            "debt_saatleri": borc.debt_saatleri,
            "aylik_maliyet_usd": None if dolar_gizli else borc.aylik_maliyet_usd,
            "risk_seviyesi": borc.risk_seviyesi,
            "ai_olasiligi": borc.ai_olasiligi,
            "karmasiklik": borc.karmasiklik,
            "toplam_satir": borc.toplam_satir,
        })

    dosya_listesi.sort(key=lambda d: d["debt_saatleri"], reverse=True)

    return {
        "toplam_dosya": len(dosya_listesi),
        "dolar_gizli": dolar_gizli,
        "saatlik_ucret": rate,
        "dosyalar": dosya_listesi,
    }


# ---------------------------------------------------------------------------
# Sprint endpoint'leri
# ---------------------------------------------------------------------------

class SprintGirdi(BaseModel):
    """Yeni sprint oluşturma giriş verisi."""
    sprint_adi: str
    baslangic: str   # ISO date: "2026-06-01"
    bitis: str       # ISO date: "2026-06-14"


@app.post("/sprints", tags=["Sprint"])
async def sprint_olustur(girdi: SprintGirdi) -> dict:
    """
    Yeni sprint kaydı oluştur ve sağlık skoru hesapla.
    Team+ planı gerektirir.
    """
    from codedna.plan import is_feature_available
    from codedna.sprint_health import calculate_sprint_health, save_sprint_result
    from datetime import datetime as dt

    if not is_feature_available("sprint_health"):
        raise _plan_403(
            "sprint_health",
            "Bu özellik Team planında mevcut.",
            "This feature is available on Team plan.",
        )

    try:
        baslangic = dt.fromisoformat(girdi.baslangic)
        bitis = dt.fromisoformat(girdi.bitis)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Geçersiz tarih formatı: {e}")

    if bitis <= baslangic:
        raise HTTPException(status_code=422, detail="Bitiş tarihi başlangıçtan sonra olmalı.")

    kok = _repo_yolu()
    db = _db_yolu()
    init_db(db)

    sonuc = calculate_sprint_health(kok, db, baslangic, bitis, girdi.sprint_adi)
    sprint_id = save_sprint_result(sonuc, db)

    return {
        "sprint_id": sprint_id,
        "sprint_adi": sonuc.sprint_adi,
        "health_score": sonuc.health_score,
        "durum": sonuc.durum,
        "avg_understanding": sonuc.avg_understanding,
        "ai_orani": sonuc.ai_orani,
        "debt_delta_saati": sonuc.debt_delta_saati,
        "toplam_commit": sonuc.toplam_commit,
        "ai_insan_orani": sonuc.ai_insan_orani_str,
    }


@app.get("/sprints/current/health", tags=["Sprint"])
async def aktif_sprint_sagligi() -> dict:
    """
    En son sprint'in sağlık skorunu döndür.
    Team+ planı gerektirir.
    """
    from codedna.plan import is_feature_available
    from codedna.db import get_latest_sprint

    if not is_feature_available("sprint_health"):
        raise _plan_403(
            "sprint_health",
            "Bu özellik Team planında mevcut.",
            "This feature is available on Team plan.",
        )

    db = _db_yolu()
    init_db(db)

    sprint = get_latest_sprint(db_path=db)
    if not sprint:
        raise HTTPException(status_code=404, detail="Henüz kayıtlı sprint yok.")

    return {
        "sprint_id": sprint["id"],
        "sprint_adi": sprint["sprint_name"],
        "health_score": sprint["health_score"],
        "durum": _sprint_durumu(sprint["health_score"]),
        "avg_understanding": sprint["avg_understanding"],
        "debt_delta_saati": sprint["debt_delta_hours"],
        "ai_satir": sprint["total_lines_ai"],
        "insan_satir": sprint["total_lines_human"],
        "baslangic": _ts_to_str(sprint["start_date"]),
        "bitis": _ts_to_str(sprint["end_date"]),
    }


@app.get("/sprints/history", tags=["Sprint"])
async def sprint_gecmisi(
    limit: int = Query(10, ge=1, le=50, description="Döndürülecek sprint sayısı"),
) -> dict:
    """Geçmiş sprint listesini döndür. Team+ planı gerektirir."""
    from codedna.plan import is_feature_available
    from codedna.db import get_sprint_history as db_sprint_history

    if not is_feature_available("sprint_health"):
        raise _plan_403(
            "sprint_health",
            "Bu özellik Team planında mevcut.",
            "This feature is available on Team plan.",
        )

    db = _db_yolu()
    init_db(db)
    sprintler = db_sprint_history(limit=limit, db_path=db)

    return {
        "toplam": len(sprintler),
        "sprintler": [
            {
                "id": s["id"],
                "sprint_adi": s["sprint_name"],
                "baslangic": _ts_to_str(s["start_date"]),
                "bitis": _ts_to_str(s["end_date"]),
                "health_score": s["health_score"],
                "durum": _sprint_durumu(s["health_score"]),
                "avg_understanding": s["avg_understanding"],
                "debt_delta_saati": s["debt_delta_hours"],
                "ai_satir": s["total_lines_ai"],
                "insan_satir": s["total_lines_human"],
            }
            for s in sprintler
        ],
    }


# ---------------------------------------------------------------------------
# Jira webhook endpoint'i
# ---------------------------------------------------------------------------

@app.post("/integrations/jira/webhook", tags=["Entegrasyonlar"])
async def jira_webhook(request: Request) -> dict:
    """
    Jira'dan gelen sprint event'lerini al ve işle.
    HMAC-SHA256 imza doğrulaması ZORUNLUDUR (Team+ planı gerektirir).
    """
    from codedna.integrations.jira import (
        get_or_create_secret,
        verify_signature,
        handle_jira_webhook,
    )
    from codedna.plan import is_feature_available

    # Plan kontrolü
    if not is_feature_available("sprint_health"):
        raise HTTPException(
            status_code=403,
            detail="Jira entegrasyonu Team planında mevcut. / Jira integration requires Team plan.",
        )

    body = await request.body()
    secret = get_or_create_secret()
    imza = request.headers.get("X-Hub-Signature-256", "")

    # İmza ZORUNLU — boşsa veya geçersizse reddet
    if not imza or not verify_signature(body, imza, secret):
        raise HTTPException(
            status_code=401,
            detail="Geçersiz veya eksik webhook imzası.",
        )

    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Geçersiz JSON payload.")

    db = _db_yolu()
    init_db(db)
    sonuc = handle_jira_webhook(payload, db)
    return sonuc


@app.get("/integrations/jira/config", tags=["Entegrasyonlar"])
async def jira_konfig() -> dict:
    """Jira webhook yapılandırmasını döndür. Team+ planı gerektirir."""
    from codedna.plan import is_feature_available
    from codedna.integrations.jira import get_or_create_secret

    if not is_feature_available("sprint_health"):
        raise _plan_403(
            "sprint_health",
            "Bu özellik Team planında mevcut.",
            "This feature is available on Team plan.",
        )

    secret = get_or_create_secret()
    return {
        "webhook_url": f"{_repo_yolu().name}/api/integrations/jira/webhook",
        "secret_mevcut": bool(secret),
        "secret_uzunluk": len(secret),
        "desteklenen_eventler": ["sprint_started", "sprint_closed"],
    }


@app.post("/integrations/jira/rotate-secret", tags=["Entegrasyonlar"])
async def jira_secret_yenile() -> dict:
    """Webhook secret'ı yenile. Team+ planı gerektirir."""
    from codedna.plan import is_feature_available
    from codedna.integrations.jira import rotate_secret

    if not is_feature_available("sprint_health"):
        raise _plan_403(
            "sprint_health",
            "Bu özellik Team planında mevcut.",
            "This feature is available on Team plan.",
        )

    yeni = rotate_secret()
    return {
        "mesaj": "Webhook secret yenilendi.",
        "secret": yeni,
    }


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar (sprint için)
# ---------------------------------------------------------------------------

def _sprint_durumu(skor: Optional[float]) -> str:
    """Skor değerine göre durum etiketi döndür."""
    if skor is None:
        return "BİLİNMİYOR"
    if skor >= 80:
        return "SAĞLIKLI"
    elif skor >= 50:
        return "DİKKAT"
    return "RİSKLİ"


def _ts_to_str(ts: Optional[int]) -> Optional[str]:
    """Unix timestamp'i okunabilir tarih string'ine çevir."""
    if not ts:
        return None
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# AI Araç Karşılaştırma endpoint'i
# ---------------------------------------------------------------------------

@app.get("/ai-compare", tags=["AI Karşılaştırma"])
async def ai_arac_karsilastir() -> dict:
    """
    Repo genelinde AI araç bazlı karşılaştırma.
    Enterprise planı gerektirir.
    """
    from codedna.plan import is_feature_available
    from codedna.ai_fingerprint import compare_tools_in_repo

    if not is_feature_available("ai_comparison"):
        raise _plan_403(
            "ai_comparison",
            "Bu özellik Enterprise planında mevcut.",
            "This feature is available on Enterprise plan.",
        )

    kok = _repo_yolu()
    db = _db_yolu()
    init_db(db)

    sonuclar = compare_tools_in_repo(kok, db)

    return {
        "uyari": (
            "Bu tespit örüntü tabanlı bir tahmindir — kesin değildir. "
            "This detection is pattern-based estimation — not definitive."
        ),
        "araclar": sonuclar,
        "toplam_dosya": sum(
            v.get("dosya_sayisi", 0) for v in sonuclar.values()
        ),
    }


# ---------------------------------------------------------------------------
# Onboarding endpoint'leri
# ---------------------------------------------------------------------------

@app.get("/onboarding/team", tags=["Onboarding"])
async def onboarding_takim_ozeti() -> dict:
    """Takımdaki tüm yazarların ramp-up özeti. Team+ planı gerektirir."""
    from codedna.plan import is_feature_available
    from codedna.onboarding import team_onboarding_summary

    if not is_feature_available("sprint_health"):
        raise _plan_403(
            "sprint_health",
            "Bu özellik Team planında mevcut.",
            "This feature is available on Team plan.",
        )

    db = _db_yolu()
    init_db(db)

    ozet = team_onboarding_summary(db)
    return {
        "toplam_yazar": len(ozet),
        "yazarlar": ozet,
    }


@app.get("/onboarding/{author}", tags=["Onboarding"])
async def onboarding_yazar_egrisi(author: str) -> dict:
    """Tek yazar için onboarding zaman çizelgesi. Team+ planı gerektirir."""
    from codedna.plan import is_feature_available
    from codedna.onboarding import get_author_curve

    if not is_feature_available("sprint_health"):
        raise _plan_403(
            "sprint_health",
            "Bu özellik Team planında mevcut.",
            "This feature is available on Team plan.",
        )

    db = _db_yolu()
    init_db(db)

    egri = get_author_curve(author, db)

    if egri.toplam_commit == 0:
        raise HTTPException(
            status_code=404,
            detail=f"'{author}' yazarına ait commit bulunamadı.",
        )

    return {
        "yazar": egri.yazar,
        "toplam_commit": egri.toplam_commit,
        "anlama_skoru_olan": egri.anlama_skoru_olan,
        "ramp_up_hafta": egri.ramp_up_hafta,
        "son_ort_anlama": egri.son_ort_anlama,
        "yeterli_veri": egri.anlama_skoru_olan >= 5,
        "noktalar": [
            {
                "commit_no": n.commit_no,
                "hafta_no": n.hafta_no,
                "tarih": n.tarih.strftime("%Y-%m-%d"),
                "understanding_score": n.understanding_score,
            }
            for n in egri.noktalar
        ],
    }


# ---------------------------------------------------------------------------
# Korumalı Modül endpoint'leri
# ---------------------------------------------------------------------------

class ProtectedModulGirdi(BaseModel):
    """Korumalı modül ekleme giriş verisi."""
    dosya_yolu: str
    esik: float = 3.5
    etiket: str = ""
    ekleyen: str = "api"


@app.post("/protected-modules", tags=["Korumalı Modüller"])
async def korunali_modul_ekle(girdi: ProtectedModulGirdi) -> dict:
    """Yeni korumalı modül ekle. Team+ planı gerektirir."""
    from codedna.plan import is_feature_available
    from codedna.protection import protect_module

    if not is_feature_available("bus_factor"):
        raise _plan_403("bus_factor", "Bu özellik Team planında mevcut.", "This feature is available on Team plan.")

    if not (1.0 <= girdi.esik <= 5.0):
        raise HTTPException(status_code=422, detail="Eşik 1.0–5.0 arasında olmalı.")

    db = _db_yolu()
    init_db(db)
    kayit_id = protect_module(
        girdi.dosya_yolu, girdi.esik,
        girdi.etiket or girdi.dosya_yolu, girdi.ekleyen, db,
    )
    return {"id": kayit_id, "dosya_yolu": girdi.dosya_yolu, "mesaj": "Korumalı modül eklendi."}


@app.get("/protected-modules", tags=["Korumalı Modüller"])
async def korunali_modul_listesi() -> dict:
    """Tüm korumalı modülleri ve durumlarını döndür. Team+ planı gerektirir."""
    from codedna.plan import is_feature_available
    from codedna.protection import check_protected_modules

    if not is_feature_available("bus_factor"):
        raise _plan_403("bus_factor", "Bu özellik Team planında mevcut.", "This feature is available on Team plan.")

    db = _db_yolu()
    init_db(db)
    moduller = check_protected_modules(db)

    return {
        "toplam": len(moduller),
        "ihlal_sayisi": sum(1 for m in moduller if m.durum == "İHLAL"),
        "moduller": [
            {
                "dosya_yolu": m.dosya_yolu,
                "etiket": m.etiket,
                "esik": m.esik,
                "mevcut_skor": m.mevcut_skor,
                "durum": m.durum,
            }
            for m in moduller
        ],
    }


@app.delete("/protected-modules/{file_path:path}", tags=["Korumalı Modüller"])
async def korunali_modul_kaldir(file_path: str) -> dict:
    """Korumalı modülü kaldır. Team+ planı gerektirir."""
    from codedna.plan import is_feature_available
    from codedna.protection import unprotect_module

    if not is_feature_available("bus_factor"):
        raise _plan_403("bus_factor", "Bu özellik Team planında mevcut.", "This feature is available on Team plan.")

    db = _db_yolu()
    if unprotect_module(file_path, db):
        return {"mesaj": "Koruma kaldırıldı.", "dosya_yolu": file_path}
    raise HTTPException(status_code=404, detail="Korumalı modül bulunamadı.")


@app.get("/protected-modules/violations", tags=["Korumalı Modüller"])
async def korunali_modul_ihlalleri() -> dict:
    """Sadece ihlaldeki korumalı modülleri döndür. Team+ planı gerektirir."""
    from codedna.plan import is_feature_available
    from codedna.protection import get_violations

    if not is_feature_available("bus_factor"):
        raise _plan_403("bus_factor", "Bu özellik Team planında mevcut.", "This feature is available on Team plan.")

    db = _db_yolu()
    init_db(db)
    ihlaller = get_violations(db)

    return {
        "ihlal_sayisi": len(ihlaller),
        "ihlaller": [
            {"dosya_yolu": m.dosya_yolu, "etiket": m.etiket,
             "esik": m.esik, "mevcut_skor": m.mevcut_skor}
            for m in ihlaller
        ],
    }


# ---------------------------------------------------------------------------
# Mülakat endpoint'leri
# ---------------------------------------------------------------------------

class MulakatBaslatGirdi(BaseModel):
    """Mülakat başlatma giriş verisi."""
    candidate_name: str
    difficulty: str = "medium"


@app.post("/interview/start", tags=["Mülakat"])
async def mulakat_baslat(girdi: MulakatBaslatGirdi) -> dict:
    """Yeni mülakat oturumu başlat. Enterprise planı gerektirir."""
    from codedna.plan import is_feature_available
    from codedna.interview import select_candidate_file, generate_questions, start_session

    if not is_feature_available("interview_tool"):
        raise _plan_403("interview_tool", "Bu özellik Enterprise planında mevcut.", "This feature is available on Enterprise plan.")

    if girdi.difficulty not in ("easy", "medium", "hard"):
        raise HTTPException(status_code=422, detail="Zorluk: easy | medium | hard")

    kok = _repo_yolu()
    db = _db_yolu()
    init_db(db)

    dosya = select_candidate_file(kok, db, girdi.difficulty)
    if not dosya:
        raise HTTPException(status_code=404, detail=f"'{girdi.difficulty}' zorluğunda uygun dosya bulunamadı.")

    sorular = generate_questions(dosya.anonimlestirilmis_kod)
    session_id = start_session(girdi.candidate_name, dosya.dosya_yolu, sorular, db)

    return {
        "session_id": session_id,
        "aday": girdi.candidate_name,
        "zorluk": girdi.difficulty,
        "karmasiklik": dosya.karmasiklik_skoru,
        "satir_sayisi": dosya.satir_sayisi,
        "anonimlestirilmis_kod": dosya.anonimlestirilmis_kod,
        "sorular": sorular,
        "uyari": "Bu araç insan değerlendirmesinin yerine geçmez. This tool should not be used as the sole hiring decision factor.",
    }


class PuanGirdi(BaseModel):
    """Mülakat puanı giriş verisi."""
    score: float
    evaluator_notes: str = ""


@app.post("/interview/{session_id}/score", tags=["Mülakat"])
async def mulakat_puan_kaydet(session_id: int, girdi: PuanGirdi) -> dict:
    """İnsan değerlendirici puanını kaydet. Enterprise planı gerektirir."""
    from codedna.plan import is_feature_available
    from codedna.interview import submit_score

    if not is_feature_available("interview_tool"):
        raise _plan_403("interview_tool", "Bu özellik Enterprise planında mevcut.", "This feature is available on Enterprise plan.")

    db = _db_yolu()
    try:
        return submit_score(session_id, girdi.score, girdi.evaluator_notes, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/interview/sessions", tags=["Mülakat"])
async def mulakat_oturumlari(
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """Geçmiş mülakat oturumlarını döndür. Enterprise planı gerektirir."""
    from codedna.plan import is_feature_available
    from codedna.interview import get_sessions

    if not is_feature_available("interview_tool"):
        raise _plan_403("interview_tool", "Bu özellik Enterprise planında mevcut.", "This feature is available on Enterprise plan.")

    db = _db_yolu()
    init_db(db)
    return {"oturumlar": get_sessions(db, limit=limit)}


# ---------------------------------------------------------------------------
# Auth endpoint'leri
# ---------------------------------------------------------------------------

def _auth_db_yolu() -> Path:
    """Auth veritabanı yolunu döndür."""
    import os
    env = os.environ.get("CODEDNA_AUTH_DB_PATH")
    return Path(env).resolve() if env else Path.home() / ".codedna" / "auth.db"


def _token_al(request: Request) -> Optional[str]:
    """Authorization: Bearer <token> header'ından token'ı ayıkla."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


class AuthKayitGirdi(BaseModel):
    """Kayıt giriş verisi."""
    email: str
    password: str


class AuthGirisGirdi(BaseModel):
    """Giriş giriş verisi."""
    email: str
    password: str


@app.post("/auth/register", tags=["Auth"])
async def auth_kayit(girdi: AuthKayitGirdi) -> dict:
    """Yeni kullanıcı kaydı."""
    from codedna.auth import register_user, init_auth_db

    db = _auth_db_yolu()
    init_auth_db(db)

    try:
        sonuc = register_user(girdi.email, girdi.password, db)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {
        "user_id": sonuc["user_id"],
        "token": sonuc["token"],
        "plan": sonuc["plan"],
        "mesaj": "Kayıt başarılı.",
    }


@app.post("/auth/login", tags=["Auth"])
async def auth_giris(girdi: AuthGirisGirdi, request: Request) -> dict:
    """
    Giriş yap ve JWT token döndür.
    Rate limiting: IP bazlı VE e-posta bazlı — ikisi de 5 dk'da 5 deneme / 60s kilit.
    Botnet/proxy rotasyonuna karşı e-posta anahtarı eklendi.
    """
    from codedna.auth import login_user, init_auth_db
    from codedna.rate_limit import login_limiter

    db = _auth_db_yolu()
    init_auth_db(db)

    ip = request.client.host if request.client else "unknown"
    # "email:" öneki, e-posta anahtarının IP ile çakışmasını önler
    email_anahtari = f"email:{girdi.email.strip().lower()}"

    # IP bazlı VE e-posta bazlı kontrol — ikisi de geçmeli
    for anahtar in (ip, email_anahtari):
        izin_var, kalan = login_limiter.kontrol_et(anahtar)
        if not izin_var:
            raise HTTPException(
                status_code=429,
                detail=f"Çok fazla başarısız deneme. {kalan} saniye bekleyin.",
            )

    try:
        sonuc = login_user(girdi.email, girdi.password, db)
        # Başarılı girişte her iki anahtarı da sıfırla
        login_limiter.basarili_kaydet(ip)
        login_limiter.basarili_kaydet(email_anahtari)
    except ValueError:
        # Her iki anahtarı da say
        login_limiter.basarisiz_kaydet(ip)
        login_limiter.basarisiz_kaydet(email_anahtari)
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı.")

    return {
        "user_id": sonuc["user_id"],
        "token": sonuc["token"],
        "plan": sonuc["plan"],
        "subscription_status": sonuc["subscription_status"],
    }


@app.post("/auth/logout", tags=["Auth"])
async def auth_cikis(request: Request) -> dict:
    """Oturumu sonlandır."""
    from codedna.auth import logout_user

    token = _token_al(request)
    if not token:
        raise HTTPException(status_code=401, detail="Token gerekli.")

    db = _auth_db_yolu()
    logout_user(token, db)
    return {"mesaj": "Çıkış başarılı."}


@app.get("/auth/me", tags=["Auth"])
async def auth_ben(request: Request) -> dict:
    """Mevcut kullanıcı bilgisini döndür."""
    from codedna.auth import verify_token, get_user_by_id

    token = _token_al(request)
    if not token:
        raise HTTPException(status_code=401, detail="Token gerekli.")

    db = _auth_db_yolu()
    kullanici = verify_token(token, db)
    if not kullanici:
        raise HTTPException(status_code=401, detail="Geçersiz veya süresi dolmuş token.")

    detay = get_user_by_id(kullanici["user_id"], db)
    if not detay:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")

    return {
        "user_id": detay["id"],
        "email": detay["email"],
        "plan": detay["plan"],
        "subscription_status": detay["subscription_status"],
    }


# ---------------------------------------------------------------------------
# Billing endpoint'leri
# ---------------------------------------------------------------------------

class CheckoutGirdi(BaseModel):
    """Checkout isteği giriş verisi."""
    plan: str  # "pro" | "team" | "enterprise"


@app.post("/billing/checkout", tags=["Billing"])
async def billing_checkout(girdi: CheckoutGirdi, request: Request) -> dict:
    """
    Lemon Squeezy checkout URL'i oluştur.
    Authorization header gerektirir.
    """
    from codedna.auth import verify_token
    from codedna.integrations.lemonsqueezy import create_checkout_url

    token = _token_al(request)
    if not token:
        raise HTTPException(status_code=401, detail="Token gerekli.")

    db = _auth_db_yolu()
    kullanici = verify_token(token, db)
    if not kullanici:
        raise HTTPException(status_code=401, detail="Geçersiz token.")

    if girdi.plan not in ("pro", "team", "enterprise"):
        raise HTTPException(status_code=422, detail="Geçersiz plan: pro | team | enterprise")

    try:
        checkout_url = create_checkout_url(girdi.plan, kullanici["email"], kullanici["user_id"])
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"checkout_url": checkout_url, "plan": girdi.plan}


@app.post("/billing/webhook", tags=["Billing"])
async def billing_webhook(request: Request) -> dict:
    """
    Lemon Squeezy'den gelen abonelik event'lerini al ve işle.
    İmza ZORUNLU — imzasız veya geçersiz imzalı istek her zaman 401.
    """
    from codedna.integrations.lemonsqueezy import (
        verify_webhook_signature,
        handle_subscription_webhook,
    )

    body = await request.body()
    imza = request.headers.get("X-Signature", "")

    # İmza ZORUNLU — boşsa veya geçersizse reddet (Faz 6/7 deseniyle tutarlı)
    if not imza or not verify_webhook_signature(body, imza):
        raise HTTPException(status_code=401, detail="Geçersiz veya eksik webhook imzası.")

    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Geçersiz JSON payload.")

    db = _auth_db_yolu()
    sonuc = handle_subscription_webhook(payload, db)
    return sonuc


@app.get("/billing/subscription", tags=["Billing"])
async def billing_abonelik(request: Request) -> dict:
    """Mevcut kullanıcının abonelik durumunu döndür."""
    from codedna.auth import verify_token, get_user_by_id

    token = _token_al(request)
    if not token:
        raise HTTPException(status_code=401, detail="Token gerekli.")

    db = _auth_db_yolu()
    kullanici = verify_token(token, db)
    if not kullanici:
        raise HTTPException(status_code=401, detail="Geçersiz token.")

    detay = get_user_by_id(kullanici["user_id"], db)
    if not detay:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")

    return {
        "plan": detay["plan"],
        "subscription_status": detay["subscription_status"],
        "lemonsqueezy_customer_id": detay["lemonsqueezy_customer_id"],
    }
