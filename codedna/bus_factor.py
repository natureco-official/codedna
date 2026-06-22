"""Bus factor hesaplama — bir dosyayı kaç kişi gerçekten anlıyor."""

from __future__ import annotations

import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from codedna.db import get_file_ownership, upsert_file_ownership

# Büyük repo uyarı eşiği
_BUYUK_REPO_ESIGI = 500

# Yeterli anlayış eşiği (bu skorun altındaki yazarlar "anlıyor" sayılmaz)
_ANLAMA_ESIGI = 3.5

# Birincil sahip sayılmak için gereken minimum satır yüzdesi
_SAHIPLIK_ESIGI = 0.10  # %10 → o dosyada "ilgili" sayılır


@dataclass
class DosyaSahiplik:
    """Tek bir dosyanın yazar bazlı sahiplik özeti."""

    dosya_yolu: str
    toplam_satir: int
    yazarlar: dict[str, int] = field(default_factory=dict)  # yazar → satır sayısı

    @property
    def birincil_sahip(self) -> Optional[str]:
        """En fazla satıra sahip yazarı döndür."""
        if not self.yazarlar:
            return None
        return max(self.yazarlar, key=lambda y: self.yazarlar[y])

    @property
    def birincil_sahiplik_yuzdesi(self) -> float:
        """Birincil sahibin sahiplik yüzdesi (0.0–1.0)."""
        if not self.yazarlar or self.toplam_satir == 0:
            return 0.0
        birincil = self.birincil_sahip
        return self.yazarlar.get(birincil or "", 0) / self.toplam_satir


@dataclass
class BusFaktorSonucu:
    """Tek dosya için bus factor sonucu."""

    dosya_yolu: str
    bus_factor: int                  # kaç kişi bu dosyayı anlıyor
    birincil_sahip: Optional[str]
    sahiplik_yuzdesi: float          # birincil sahibin yüzdesi
    risk: str                        # KRİTİK / RİSKLİ / GÜVENLİ
    anlayan_yazarlar: list[str]      # anlama skoru >= eşik olan yazarlar
    toplam_satir: int


def _git_blame_calistir(dosya_yolu: Path, repo_koku: Path) -> dict[str, int]:
    """
    git blame --line-porcelain ile satır bazlı yazar tespiti yap.

    Returns:
        {yazar_adi: satir_sayisi} sözlüğü
    """
    try:
        goreceli = dosya_yolu.relative_to(repo_koku)
    except ValueError:
        goreceli = dosya_yolu

    try:
        sonuc = subprocess.run(
            ["git", "blame", "--line-porcelain", str(goreceli)],
            cwd=str(repo_koku),
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {}

    if sonuc.returncode != 0:
        return {}

    # Çıktıdan "author " satırlarını topla
    yazar_satirlari: dict[str, int] = defaultdict(int)
    for satir in sonuc.stdout.splitlines():
        if satir.startswith("author "):
            yazar = satir[7:].strip()
            # Özel "Not Committed Yet" durumunu atla
            if yazar and yazar != "Not Committed Yet":
                yazar_satirlari[yazar] += 1

    return dict(yazar_satirlari)


def _dosya_listesi_al(repo_koku: Path, max_dosya: int = _BUYUK_REPO_ESIGI) -> list[Path]:
    """
    Git tarafından izlenen desteklenen kaynak dosyaları listele.

    Args:
        repo_koku: Git repo kök dizini
        max_dosya: İşlenecek maksimum dosya sayısı (performans için)

    Returns:
        Mutlak Path listesi
    """
    desteklenen = {".py", ".js", ".jsx", ".ts", ".tsx"}

    try:
        sonuc = subprocess.run(
            ["git", "ls-files"],
            cwd=str(repo_koku),
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
        dosyalar = sonuc.stdout.strip().splitlines()
    except Exception:
        dosyalar = []

    filtreli = [
        repo_koku / d for d in dosyalar
        if Path(d).suffix.lower() in desteklenen and (repo_koku / d).exists()
    ]
    return filtreli[:max_dosya]


def calculate_bus_factor(
    repo_path: Path,
    db_path: Path,
    max_dosya: int = _BUYUK_REPO_ESIGI,
) -> list[BusFaktorSonucu]:
    """
    Repo genelinde her dosya için bus factor hesapla ve DB'ye kaydet.

    Bus factor = o dosyanın %50'sinden fazlasına sahip OLAN
    VE understanding_score >= 3.5 olan yazar sayısı.
    Anlama skoru yoksa sahiplik oranı >= 10% yeterli sayılır.

    Args:
        repo_path: Git repo kök dizini
        max_dosya: İşlenecek maksimum dosya sayısı

    Returns:
        BusFaktorSonucu listesi, bus_factor'a göre artan sırada
    """
    kok = Path(repo_path).resolve()
    dosyalar = _dosya_listesi_al(kok, max_dosya)

    # Mevcut anlama skorlarını DB'den tek sorguda çek
    from codedna.db import get_connection
    anlama_map: dict[tuple[str, str], float] = {}  # (dosya_yolu, yazar) → skor
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(
                """
                SELECT fo.file_path, fo.author, fo.avg_understanding
                FROM file_ownership fo
                WHERE fo.avg_understanding IS NOT NULL
                """
            ).fetchall()
            for r in rows:
                anlama_map[(r["file_path"], r["author"])] = float(r["avg_understanding"])
    except Exception:
        pass

    sonuclar: list[BusFaktorSonucu] = []

    for dosya in dosyalar:
        yazar_satirlari = _git_blame_calistir(dosya, kok)
        if not yazar_satirlari:
            continue

        toplam = sum(yazar_satirlari.values())
        if toplam == 0:
            continue

        # DB'ye kaydet
        for yazar, satir in yazar_satirlari.items():
            anlama = anlama_map.get((str(dosya), yazar))
            upsert_file_ownership(
                file_path=str(dosya),
                author=yazar,
                lines_owned=satir,
                last_touched=0,     # gelecekte git log ile doldurulacak
                avg_understanding=anlama,
                db_path=db_path,
            )

        # "Anlayan" yazarları belirle
        anlayan: list[str] = []
        for yazar, satir in yazar_satirlari.items():
            yuzde = satir / toplam
            # Anlama skoru varsa kontrol et, yoksa %10+ sahiplik yeterli
            anlama_skoru = anlama_map.get((str(dosya), yazar))
            if anlama_skoru is not None:
                if anlama_skoru >= _ANLAMA_ESIGI and yuzde >= _SAHIPLIK_ESIGI:
                    anlayan.append(yazar)
            elif yuzde >= _SAHIPLIK_ESIGI:
                # Anket verisi yoksa sahipliği baz al
                anlayan.append(yazar)

        bus_factor = max(len(anlayan), 1)
        if bus_factor == 1:
            risk = "KRİTİK"
        elif bus_factor == 2:
            risk = "RİSKLİ"
        else:
            risk = "GÜVENLİ"

        # Birincil sahip
        birincil = max(yazar_satirlari, key=lambda y: yazar_satirlari[y])
        birincil_yuzde = yazar_satirlari[birincil] / toplam

        # Göreli dosya yolu
        try:
            goreceli_yol = str(dosya.relative_to(kok))
        except ValueError:
            goreceli_yol = str(dosya)

        sonuclar.append(
            BusFaktorSonucu(
                dosya_yolu=goreceli_yol,
                bus_factor=bus_factor,
                birincil_sahip=birincil,
                sahiplik_yuzdesi=round(birincil_yuzde * 100, 1),
                risk=risk,
                anlayan_yazarlar=anlayan,
                toplam_satir=toplam,
            )
        )

    # Bus factor'a göre artan sıralama (KRİTİK önce)
    sonuclar.sort(key=lambda s: s.bus_factor)
    return sonuclar


def get_at_risk_files(
    repo_path: Path,
    db_path: Path,
) -> list[BusFaktorSonucu]:
    """
    bus_factor == 1 olan dosyaları döndür (KRİTİK liste).

    Args:
        repo_path: Git repo kök dizini
        db_path: SQLite veritabanı yolu

    Returns:
        Kritik dosyaların BusFaktorSonucu listesi
    """
    tum = calculate_bus_factor(repo_path, db_path)
    return [s for s in tum if s.bus_factor == 1]
