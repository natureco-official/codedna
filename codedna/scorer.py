"""Git geçmişinden single_commit_ratio hesaplama ve commit skorlama."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from git import InvalidGitRepositoryError, Repo
from rich.console import Console

from codedna.analyzer import FileAnalysisResult, analyze_file

console = Console()


def get_repo(path: Optional[Path] = None) -> Optional[Repo]:
    """Git repo nesnesini döndür, bulunamazsa None."""
    try:
        return Repo(path or Path.cwd(), search_parent_directories=True)
    except InvalidGitRepositoryError:
        return None


def calculate_single_commit_ratio(repo: Repo, file_path: str) -> float:
    """
    Dosyanın kaç satırının tek bir commit'te eklendiğini hesapla.

    Stratejisi: Dosyanın geçmiş commit'lerinde en büyük tek commit
    katkısının toplam satıra oranını döndür.

    Args:
        repo: Git repo nesnesi
        file_path: Repo köküne göre dosya yolu

    Returns:
        0.0 ile 1.0 arasında oran
    """
    try:
        # Dosyayla ilgili commit geçmişini al
        commitler = list(repo.iter_commits(paths=file_path, max_count=50))
        if not commitler:
            return 0.0

        # Her commit'teki satır ekleme sayısını topla
        commit_katkilar: list[int] = []
        for commit in commitler:
            try:
                if commit.parents:
                    diff = commit.parents[0].diff(commit, paths=[file_path])
                else:
                    # İlk commit
                    diff = commit.diff(None, paths=[file_path])

                for d in diff:
                    if d.a_blob or d.b_blob:
                        # Eklenen satır sayısını tahmin et
                        try:
                            stats = commit.stats.files.get(file_path, {})
                            eklenen = stats.get("insertions", 0)
                            commit_katkilar.append(eklenen)
                        except Exception:
                            pass
            except Exception:
                pass

        if not commit_katkilar:
            # Fallback: tek commit varsa %100 say
            return 1.0 if len(commitler) == 1 else 0.5

        toplam = sum(commit_katkilar)
        if toplam == 0:
            return 0.0

        en_buyuk = max(commit_katkilar)
        return min(en_buyuk / toplam, 1.0)

    except Exception:
        return 0.0


def scan_repository(
    repo_path: Optional[Path] = None,
    max_files: int = 200,
) -> list[FileAnalysisResult]:
    """
    Repo'daki desteklenen tüm dosyaları tara.

    Args:
        repo_path: Repo kök dizini (None ise mevcut dizin)
        max_files: Maksimum taranacak dosya sayısı

    Returns:
        FileAnalysisResult listesi
    """
    kok = Path(repo_path or Path.cwd()).resolve()
    repo = get_repo(kok)

    desteklenen_uzantilar = {".py", ".js", ".jsx", ".ts", ".tsx"}
    atlanan_dizinler = {
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        "dist", "build", ".mypy_cache", ".pytest_cache",
    }

    # İzlenen dosyaları al (git varsa)
    izlenen_dosyalar: set[str] = set()
    if repo:
        try:
            izlenen_dosyalar = {item for item in repo.git.ls_files().splitlines()}
        except Exception:
            pass

    sonuclar: list[FileAnalysisResult] = []
    sayac = 0

    for dosya in kok.rglob("*"):
        if sayac >= max_files:
            break

        # Atlanacak dizinleri geç
        parcalar = dosya.parts
        if any(atla in parcalar for atla in atlanan_dizinler):
            continue

        if not dosya.is_file():
            continue

        if dosya.suffix.lower() not in desteklenen_uzantilar:
            continue

        # Git izlemesindeyse oranı hesapla
        goreceli_yol = str(dosya.relative_to(kok))
        tek_commit_orani = 0.0
        if repo and goreceli_yol in izlenen_dosyalar:
            tek_commit_orani = calculate_single_commit_ratio(repo, goreceli_yol)

        sonuc = analyze_file(dosya, single_commit_ratio=tek_commit_orani)
        if not sonuc.desteklenmiyor and sonuc.hata is None:
            sonuclar.append(sonuc)
            sayac += 1

    return sonuclar


def get_commit_files(repo: Repo, commit_hash: Optional[str] = None) -> list[str]:
    """
    Belirli bir commit'teki (ya da HEAD'deki) değişen dosyaları listele.

    Args:
        repo: Git repo nesnesi
        commit_hash: İncelenecek commit hash'i (None ise HEAD)

    Returns:
        Değişen dosyaların yol listesi
    """
    try:
        if commit_hash:
            commit = repo.commit(commit_hash)
        else:
            commit = repo.head.commit

        return list(commit.stats.files.keys())
    except Exception:
        return []


def score_latest_commit(repo_path: Optional[Path] = None) -> tuple[Optional[str], list[FileAnalysisResult]]:
    """
    Son commit'teki dosyaları analiz et.

    Returns:
        (commit_hash, sonuç_listesi) çifti
    """
    kok = Path(repo_path or Path.cwd()).resolve()
    repo = get_repo(kok)
    if not repo:
        return None, []

    try:
        commit = repo.head.commit
        commit_hash = commit.hexsha
        dosyalar = get_commit_files(repo, commit_hash)
    except Exception:
        return None, []

    sonuclar: list[FileAnalysisResult] = []
    desteklenen_uzantilar = {".py", ".js", ".jsx", ".ts", ".tsx"}

    for dosya_yolu in dosyalar:
        tam_yol = kok / dosya_yolu
        if not tam_yol.exists():
            continue
        if tam_yol.suffix.lower() not in desteklenen_uzantilar:
            continue

        tek_commit_orani = calculate_single_commit_ratio(repo, dosya_yolu)
        sonuc = analyze_file(tam_yol, single_commit_ratio=tek_commit_orani)
        if not sonuc.desteklenmiyor and sonuc.hata is None:
            sonuclar.append(sonuc)

    return commit_hash, sonuclar
