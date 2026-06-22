"""Git hook kurulum ve yönetim modülü."""

import os
import stat
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()

# Post-commit hook içeriği
HOOK_TEMPLATE = """#!/bin/bash
# CodeDNA post-commit hook
# Otomatik olarak codedna tarafından oluşturuldu.

# codedna'nın PATH'te olup olmadığını kontrol et
if command -v codedna &> /dev/null; then
    codedna status --hook
else
    # uv ile çalıştırmayı dene (geliştirme ortamı için)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    if [ -f "$REPO_ROOT/.venv/bin/codedna" ]; then
        "$REPO_ROOT/.venv/bin/codedna" status --hook
    elif [ -f "$HOME/.local/bin/codedna" ]; then
        "$HOME/.local/bin/codedna" status --hook
    fi
fi
"""


def find_git_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Verilen yoldan yukarı doğru .git dizinini ara.

    Args:
        start_path: Arama başlangıç noktası (None ise mevcut dizin)

    Returns:
        .git dizinini içeren repo kökü veya None
    """
    yol = Path(start_path or Path.cwd()).resolve()
    for ebeveyn in [yol, *yol.parents]:
        if (ebeveyn / ".git").exists():
            return ebeveyn
    return None


def install_hook(repo_path: Optional[Path] = None) -> bool:
    """
    Post-commit hook'u kur.

    Args:
        repo_path: Git repo kök dizini (None ise otomatik bul)

    Returns:
        Başarıyla kurulduysa True
    """
    kok = repo_path or find_git_root()
    if not kok:
        console.print("[bold red]Hata:[/bold red] Git repo bulunamadı. 'git init' ile başlatın.")
        return False

    hooks_dir = kok / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_dosyasi = hooks_dir / "post-commit"

    # Mevcut hook varsa yedekle
    if hook_dosyasi.exists():
        yedek = hooks_dir / "post-commit.backup"
        hook_dosyasi.rename(yedek)
        console.print(f"[yellow]Mevcut hook yedeklendi:[/yellow] {yedek}")

    # Yeni hook'u yaz
    hook_dosyasi.write_text(HOOK_TEMPLATE, encoding="utf-8")

    # Çalıştırılabilir yap (chmod +x)
    mevcut_mod = hook_dosyasi.stat().st_mode
    hook_dosyasi.chmod(mevcut_mod | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    console.print(f"[green]✓[/green] Hook kuruldu: {hook_dosyasi}")
    return True


def uninstall_hook(repo_path: Optional[Path] = None) -> bool:
    """
    Post-commit hook'u kaldır.

    Args:
        repo_path: Git repo kök dizini (None ise otomatik bul)

    Returns:
        Başarıyla kaldırıldıysa True
    """
    kok = repo_path or find_git_root()
    if not kok:
        console.print("[bold red]Hata:[/bold red] Git repo bulunamadı.")
        return False

    hook_dosyasi = kok / ".git" / "hooks" / "post-commit"

    if not hook_dosyasi.exists():
        console.print("[yellow]Post-commit hook bulunamadı, zaten kaldırılmış.[/yellow]")
        return True

    # Yedekten geri yükle
    yedek = kok / ".git" / "hooks" / "post-commit.backup"
    if yedek.exists():
        hook_dosyasi.unlink()
        yedek.rename(hook_dosyasi)
        console.print("[green]✓[/green] Önceki hook geri yüklendi.")
    else:
        hook_dosyasi.unlink()
        console.print("[green]✓[/green] CodeDNA hook kaldırıldı.")

    return True


def install_ci_workflow(repo_path: Optional[Path] = None) -> bool:
    """
    GitHub Actions CI şablonunu repo'ya yaz.

    Args:
        repo_path: Git repo kök dizini (None ise otomatik bul)

    Returns:
        Başarıyla yazıldıysa True
    """
    import importlib.resources

    kok = repo_path or find_git_root()
    if not kok:
        console.print("[bold red]Hata:[/bold red] Git repo bulunamadı.")
        return False

    workflows_dir = kok / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    hedef = workflows_dir / "codedna.yml"

    if hedef.exists():
        console.print("[yellow]⚠[/yellow]  .github/workflows/codedna.yml zaten mevcut, üzerine yazılmıyor.")
        return True

    # Paketle birlikte gelen şablonu kopyala
    try:
        sablon_yolu = Path(__file__).parent.parent / ".github" / "workflows" / "codedna.yml"
        if sablon_yolu.exists():
            hedef.write_text(sablon_yolu.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            # Fallback: inline şablon
            hedef.write_text(_CI_SABLON, encoding="utf-8")
        console.print(f"[green]✓[/green] CI şablonu oluşturuldu: [dim]{hedef}[/dim]")
        return True
    except Exception as e:
        console.print(f"[red]✗[/red] CI şablonu yazılamadı: {e}")
        return False


# GitHub Actions şablon içeriği (fallback)
_CI_SABLON = """\
name: CodeDNA Analysis

on:
  push:
    branches: ["**"]
  pull_request:
    branches: ["**"]

jobs:
  analyze:
    name: AI Kod Analizi
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install codedna
      - run: codedna scan
        continue-on-error: true
      - name: Yüksek risk kontrolü
        run: |
          codedna scan --min-risk 0.7 && echo "✅ Yüksek riskli dosya yok." || echo "⚠️ Yüksek riskli dosyalar tespit edildi."
        continue-on-error: true
"""


def is_hook_installed(repo_path: Optional[Path] = None) -> bool:
    """CodeDNA hook'unun kurulu olup olmadığını kontrol et."""
    kok = repo_path or find_git_root()
    if not kok:
        return False
    hook_dosyasi = kok / ".git" / "hooks" / "post-commit"
    if not hook_dosyasi.exists():
        return False
    icerik = hook_dosyasi.read_text(encoding="utf-8", errors="replace")
    return "CodeDNA" in icerik
