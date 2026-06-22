"""CodeDNA CLI — typer tabanlı komut satırı arayüzü."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from codedna import __version__
from codedna.db import (
    get_db_path,
    get_all_file_understanding_scores,
    get_commit_history,
    get_file_scores_for_commit,
    get_latest_commit,
    init_db,
    save_commit,
    save_file_score,
    update_understanding_score,
)
from codedna.git_hook import find_git_root, install_hook, install_ci_workflow, is_hook_installed, uninstall_hook
from codedna.scorer import get_repo, scan_repository, score_latest_commit
from codedna.survey import run_survey

app = typer.Typer(
    name="codedna",
    help="🧬 CodeDNA — AI kod şeffaflık aracı",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


def _get_db(repo_path: Optional[Path] = None) -> Path:
    """Repo'ya özel veritabanı yolunu döndür."""
    kok = repo_path or find_git_root() or Path.cwd()
    return get_db_path(kok)


# ---------------------------------------------------------------------------
# codedna init
# ---------------------------------------------------------------------------
@app.command()
def init(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
    with_ci: bool = typer.Option(False, "--with-ci", help="GitHub Actions CI şablonunu da oluştur"),
) -> None:
    """Git hook'u kur, veritabanını oluştur ve isteğe bağlı CI şablonu yaz."""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]🧬 CodeDNA[/bold cyan] kurulumu başlatılıyor...",
            border_style="cyan",
        )
    )

    # Repo kökünü bul
    kok = repo or find_git_root()
    if not kok:
        console.print("[bold red]Hata:[/bold red] Git repo bulunamadı. Önce 'git init' komutunu çalıştırın.")
        raise typer.Exit(1)

    console.print(f"[dim]Repo kökü:[/dim] {kok}")

    # Veritabanını başlat
    db_yolu = _get_db(kok)
    init_db(db_yolu)
    console.print(f"[green]✓[/green] Veritabanı oluşturuldu: [dim]{db_yolu}[/dim]")

    # Hook'u kur
    if is_hook_installed(kok):
        console.print("[yellow]⚠[/yellow]  Post-commit hook zaten kurulu.")
    else:
        if install_hook(kok):
            console.print("[green]✓[/green] Post-commit hook kuruldu.")
        else:
            console.print("[red]✗[/red] Hook kurulumu başarısız.")
            raise typer.Exit(1)

    # CI şablonu
    if with_ci:
        install_ci_workflow(kok)

    bilgi = (
        "[bold green]CodeDNA başarıyla kuruldu![/bold green]\n"
        "Artık her [bold]git commit[/bold] sonrası otomatik analiz çalışacak.\n\n"
        "[dim]• Tüm repoyu taramak için:[/dim] [cyan]codedna scan[/cyan]\n"
        "[dim]• Son commit skorunu görmek için:[/dim] [cyan]codedna status[/cyan]\n"
        "[dim]• Geçmiş skorları görmek için:[/dim] [cyan]codedna history[/cyan]\n"
        "[dim]• API sunucuyu başlatmak için:[/dim] [cyan]codedna serve[/cyan]\n"
        "[dim]• HTML rapor üretmek için:[/dim] [cyan]codedna report[/cyan]"
    )
    if with_ci:
        bilgi += "\n[dim]• CI şablonu:[/dim] [cyan].github/workflows/codedna.yml[/cyan]"

    console.print()
    console.print(Panel(bilgi, border_style="green", padding=(1, 2)))


# ---------------------------------------------------------------------------
# codedna scan
# ---------------------------------------------------------------------------
@app.command()
def scan(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
    max_files: int = typer.Option(200, "--max", "-m", help="Maksimum taranacak dosya sayısı"),
    min_risk: float = typer.Option(0.0, "--min-risk", help="Minimum AI olasılığı filtresi (0.0-1.0)"),
) -> None:
    """Mevcut repo'yu tara ve AI risk raporu göster."""
    console.print()
    console.print("[bold cyan]🧬 CodeDNA[/bold cyan] — Repo taranıyor...\n")

    kok = repo or find_git_root() or Path.cwd()

    with console.status("[dim]Dosyalar analiz ediliyor...[/dim]"):
        sonuclar = scan_repository(kok, max_files=max_files)

    if not sonuclar:
        console.print("[yellow]Taranacak desteklenen dosya bulunamadı.[/yellow]")
        console.print("[dim]Desteklenen: .py .js .jsx .ts .tsx[/dim]")
        return

    # Min risk filtresi uygula
    if min_risk > 0:
        sonuclar = [s for s in sonuclar if s.ai_probability >= min_risk]

    # AI olasılığına göre sırala (yüksekten düşüğe)
    sonuclar.sort(key=lambda s: s.ai_probability, reverse=True)

    # DB'den tüm dosya anlama skorlarını tek sorguda çek
    db_yolu = _get_db(kok)
    anlama_skorlari_map: dict[str, float] = {}
    try:
        anlama_skorlari_map = get_all_file_understanding_scores(db_path=db_yolu)
    except Exception:
        pass

    # Tablo oluştur
    tablo = Table(
        title="",
        border_style="dim",
        show_lines=True,
        header_style="bold",
    )
    tablo.add_column("Dosya", style="white", min_width=25)
    tablo.add_column("AI Olasılığı", justify="center", min_width=14)
    tablo.add_column("Karmaşıklık", justify="center", min_width=12)
    tablo.add_column("Satır", justify="right", min_width=6)
    tablo.add_column("Anlama Skoru", justify="center", min_width=14)

    toplam_ai = 0.0
    for s in sonuclar:
        yuzde = int(s.ai_probability * 100)
        ai_metin = f"{s.ai_color} %{yuzde}"

        if s.complexity_label == "Yüksek":
            karmasiklik = "[red]Yüksek[/red]"
        elif s.complexity_label == "Orta":
            karmasiklik = "[yellow]Orta[/yellow]"
        else:
            karmasiklik = "[green]Düşük[/green]"

        # DB'den tek sorguda gelen map'ten anlama skorunu oku
        anlama_skor = anlama_skorlari_map.get(s.file_path)
        if anlama_skor is not None:
            renk = "green" if anlama_skor >= 4.0 else "yellow" if anlama_skor >= 2.5 else "red"
            anlama = f"[{renk}]✅ {anlama_skor:.1f}/5[/{renk}]"
        else:
            anlama = "[dim]⚠️  Bilinmiyor[/dim]"

        goreceli = _kisalt_yol(s.file_path, str(kok))

        tablo.add_row(goreceli, ai_metin, karmasiklik, str(s.total_lines), anlama)
        toplam_ai += s.ai_probability

    console.print(tablo)

    # Özet satırı
    ortalama_ai = (toplam_ai / len(sonuclar)) * 100 if sonuclar else 0
    risk_etiketi, risk_renk = _risk_etiketi(ortalama_ai)

    console.print(
        f"\n[bold]Repo Özeti:[/bold] {len(sonuclar)} dosya tarandı · "
        f"Ortalama AI olasılığı: [bold]%{ortalama_ai:.0f}[/bold] · "
        f"Risk: [bold {risk_renk}]{risk_etiketi}[/bold {risk_renk}]\n"
    )


# ---------------------------------------------------------------------------
# codedna status
# ---------------------------------------------------------------------------
@app.command()
def status(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
    hook: bool = typer.Option(False, "--hook", hidden=True, help="Hook modunda çalış (anket sor)"),
) -> None:
    """Son commit'in skorunu göster (ve hook modunda anket sor)."""
    console.print()
    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)

    # DB yoksa init et
    init_db(db_yolu)

    git_repo = get_repo(kok)
    if not git_repo:
        console.print("[bold red]Hata:[/bold red] Git repo bulunamadı.")
        raise typer.Exit(1)

    with console.status("[dim]Son commit analiz ediliyor...[/dim]"):
        commit_hash, sonuclar = score_latest_commit(kok)

    if not commit_hash:
        console.print("[yellow]Henüz commit bulunamadı.[/yellow]")
        return

    # Commit bilgilerini al
    try:
        commit = git_repo.head.commit
        yazar = f"{commit.author.name}"
        zaman_dam = int(commit.committed_date)
        mesaj = commit.message.strip().splitlines()[0][:60]
    except Exception:
        yazar = "Bilinmiyor"
        zaman_dam = 0
        mesaj = ""

    # Anket (sadece hook modunda)
    anlama_skoru: Optional[float] = None
    if hook:
        anlama_skoru = run_survey(commit_hash)

    # DB'ye kaydet
    save_commit(
        commit_hash=commit_hash,
        author=yazar,
        timestamp=zaman_dam,
        files_changed=len(sonuclar),
        understanding_score=anlama_skoru,
        db_path=db_yolu,
    )
    for s in sonuclar:
        save_file_score(
            commit_hash=commit_hash,
            file_path=s.file_path,
            ai_probability=s.ai_probability,
            complexity_score=s.complexity_score,
            comment_ratio=s.comment_ratio,
            understanding_score=anlama_skoru,
            db_path=db_yolu,
        )

    # Özet göster
    if sonuclar:
        ort_ai = sum(s.ai_probability for s in sonuclar) / len(sonuclar)
        risk_etiketi, risk_renk = _risk_etiketi(ort_ai * 100)

        anlama_goster = (
            f"[bold green]{anlama_skoru:.1f}/5[/bold green]"
            if anlama_skoru is not None
            else "[dim]Anket yapılmadı[/dim]"
        )

        console.print(
            Panel(
                f"[bold]Commit:[/bold] [dim]{commit_hash[:8]}[/dim]  [dim]{mesaj}[/dim]\n"
                f"[bold]Yazar:[/bold] {yazar}\n"
                f"[bold]Değişen dosyalar:[/bold] {len(sonuclar)}\n"
                f"[bold]Ort. AI olasılığı:[/bold] [bold {risk_renk}]%{ort_ai*100:.0f} ({risk_etiketi})[/bold {risk_renk}]\n"
                f"[bold]Anlama skoru:[/bold] {anlama_goster}",
                title="[bold cyan]🧬 CodeDNA — Commit Skoru[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        console.print("[dim]Commit skoru kaydedildi.[/dim]\n")

    # Post-commit hook: korumalı modül ihlallerini kontrol et ve uyar (bloklama YOK)
    if hook:
        try:
            from codedna.protection import ihlal_uyarisi_goster
            uyarilar = ihlal_uyarisi_goster(db_yolu)
            for uyari in uyarilar:
                console.print(f"[bold red]{uyari}[/bold red]")
        except Exception:
            pass  # Hook'u asla bozmaz

    else:
        console.print(
            f"[bold]Commit:[/bold] [dim]{commit_hash[:8]}[/dim]\n"
            "[dim]Bu commit'te desteklenen kod dosyası bulunamadı.[/dim]"
        )


# ---------------------------------------------------------------------------
# codedna history
# ---------------------------------------------------------------------------
@app.command()
def history(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
    limit: int = typer.Option(20, "--limit", "-n", help="Gösterilecek commit sayısı"),
) -> None:
    """Geçmiş commit skorlarını tablo olarak göster."""
    console.print()
    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)

    init_db(db_yolu)
    satirlar = get_commit_history(limit=limit, db_path=db_yolu)

    if not satirlar:
        console.print(
            "[yellow]Henüz kayıtlı commit yok.[/yellow]\n"
            "[dim]İpucu: 'codedna init' ile kurulum yapın, ardından commit atın.[/dim]"
        )
        return

    tablo = Table(
        title=f"[bold cyan]🧬 CodeDNA — Son {len(satirlar)} Commit[/bold cyan]",
        border_style="dim",
        show_lines=True,
        header_style="bold",
    )
    tablo.add_column("Commit", style="dim", min_width=10)
    tablo.add_column("Yazar", min_width=15)
    tablo.add_column("Tarih", min_width=17)
    tablo.add_column("Dosya", justify="right", min_width=6)
    tablo.add_column("Anlama", justify="center", min_width=12)

    for satir in satirlar:
        tarih_str = (
            datetime.fromtimestamp(satir["timestamp"]).strftime("%Y-%m-%d %H:%M")
            if satir["timestamp"]
            else "?"
        )

        if satir["understanding_score"] is not None:
            skor = satir["understanding_score"]
            if skor >= 4.0:
                anlama = f"[green]✅ {skor:.1f}/5[/green]"
            elif skor >= 2.5:
                anlama = f"[yellow]🔶 {skor:.1f}/5[/yellow]"
            else:
                anlama = f"[red]🔴 {skor:.1f}/5[/red]"
        else:
            anlama = "[dim]⚠️  Yok[/dim]"

        tablo.add_row(
            satir["commit_hash"][:8],
            satir["author"] or "?",
            tarih_str,
            str(satir["files_changed"] or 0),
            anlama,
        )

    console.print(tablo)
    console.print()


# ---------------------------------------------------------------------------
# codedna serve
# ---------------------------------------------------------------------------
@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Dinlenecek IP adresi"),
    port: int = typer.Option(8000, "--port", "-p", help="Port numarası"),
    reload: bool = typer.Option(False, "--reload", help="Geliştirme modunda otomatik yeniden başlat"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
) -> None:
    """FastAPI REST sunucusunu başlat."""
    import os
    import uvicorn

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)

    # Ortam değişkenlerini ayarla (api.py tarafından okunur)
    os.environ.setdefault("CODEDNA_REPO_PATH", str(kok))
    os.environ.setdefault("CODEDNA_DB_PATH", str(db_yolu))

    init_db(db_yolu)

    console.print()
    console.print(
        Panel(
            f"[bold cyan]🧬 CodeDNA API[/bold cyan] başlatılıyor...\n\n"
            f"[bold]Adres:[/bold]    [link]http://{host}:{port}[/link]\n"
            f"[bold]Docs:[/bold]     [link]http://{host}:{port}/docs[/link]\n"
            f"[bold]Repo:[/bold]     [dim]{kok}[/dim]\n"
            f"[bold]Veritabanı:[/bold] [dim]{db_yolu}[/dim]\n\n"
            "[dim]Durdurmak için Ctrl+C[/dim]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    uvicorn.run(
        "codedna.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


# ---------------------------------------------------------------------------
# codedna report
# ---------------------------------------------------------------------------
@app.command()
def report(
    output: Path = typer.Option(Path("codedna-report.html"), "--output", "-o", help="Çıktı dosyası"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
    open_browser: bool = typer.Option(False, "--open", help="Raporu tarayıcıda aç"),
) -> None:
    """HTML rapor oluştur."""
    import webbrowser
    from datetime import datetime
    from codedna.api import _rapor_html_olustur

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)
    init_db(db_yolu)

    console.print()
    console.print("[bold cyan]🧬 CodeDNA[/bold cyan] — HTML rapor oluşturuluyor...\n")

    with console.status("[dim]Dosyalar analiz ediliyor...[/dim]"):
        sonuclar = scan_repository(kok, max_files=200)

    sonuclar.sort(key=lambda s: s.ai_probability, reverse=True)
    commitler = get_commit_history(limit=50, db_path=db_yolu)

    tum_ai = [s.ai_probability for s in sonuclar]
    ort_ai = sum(tum_ai) / len(tum_ai) if tum_ai else 0.0
    risk_etkt, _ = _risk_etiketi(ort_ai * 100)

    anlama_skorlari = [
        float(c["understanding_score"])
        for c in commitler
        if c["understanding_score"] is not None
    ]
    ort_anlama = sum(anlama_skorlari) / len(anlama_skorlari) if anlama_skorlari else None

    html = _rapor_html_olustur(
        repo_adi=kok.name,
        toplam_dosya=len(sonuclar),
        ort_ai=ort_ai,
        risk=risk_etkt,
        ort_anlama=ort_anlama,
        toplam_commit=len(commitler),
        dosyalar=sonuclar,
        commitler=commitler,
        kok=kok,
    )

    output.write_text(html, encoding="utf-8")
    console.print(f"[green]✓[/green] Rapor oluşturuldu: [bold]{output.resolve()}[/bold]")
    console.print(
        f"  [dim]{len(sonuclar)} dosya · "
        f"Ort. AI: %{ort_ai*100:.0f} · "
        f"Risk: {risk_etkt}[/dim]"
    )

    if open_browser:
        webbrowser.open(output.resolve().as_uri())
        console.print("[dim]Tarayıcıda açılıyor...[/dim]")

    console.print()


# ---------------------------------------------------------------------------
# codedna ai-compare
# ---------------------------------------------------------------------------
@app.command(name="ai-compare")
def ai_compare(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
) -> None:
    """Repo genelinde AI araç bazlı karşılaştırma tablosu göster."""
    from codedna.ai_fingerprint import compare_tools_in_repo
    from codedna.plan import is_feature_available

    if not is_feature_available("ai_comparison"):
        console.print(
            Panel(
                "[bold yellow]🔒 Bu özellik Enterprise planında mevcut.[/bold yellow]\n"
                "[dim]This feature is available on Enterprise plan.[/dim]\n\n"
                "[dim]Yükseltmek için:[/dim] [cyan]codedna plan activate <LICENSE_KEY>[/cyan]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        raise typer.Exit(1)

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)
    init_db(db_yolu)

    console.print()
    console.print("[bold cyan]🧬 CodeDNA[/bold cyan] — AI araç parmak izi analizi çalışıyor...\n")
    console.print(
        "[dim]⚠️  Bu tespit örüntü tabanlı bir tahmindir — kesin değildir.[/dim]\n"
    )

    with console.status("[dim]Dosyalar analiz ediliyor...[/dim]"):
        sonuclar = compare_tools_in_repo(kok, db_yolu)

    if not sonuclar:
        console.print("[yellow]Analiz edilecek dosya bulunamadı.[/yellow]")
        return

    tablo = Table(border_style="dim", show_lines=True, header_style="bold")
    tablo.add_column("AI Aracı", min_width=12)
    tablo.add_column("Dosya Sayısı", justify="right", min_width=13)
    tablo.add_column("Ort. AI Skoru", justify="right", min_width=13)
    tablo.add_column("Ort. Anlama", justify="right", min_width=12)

    arac_emojileri = {
        "copilot": "🐙", "cursor": "🖱️",
        "claude": "🧠", "unknown": "❓",
    }

    for arac, veri in sorted(sonuclar.items(), key=lambda x: -x[1].get("dosya_sayisi", 0)):
        emoji = arac_emojileri.get(arac, "🤖")
        anlama = (
            f"{veri['avg_understanding']:.1f}/5"
            if veri.get("avg_understanding") else "—"
        )
        tablo.add_row(
            f"{emoji} {arac}",
            str(veri.get("dosya_sayisi", 0)),
            f"%{veri.get('avg_ai_probability', 0) * 100:.0f}",
            anlama,
        )

    console.print(tablo)
    console.print()


# ---------------------------------------------------------------------------
# codedna onboarding
# ---------------------------------------------------------------------------
@app.command()
def onboarding(
    author: Optional[str] = typer.Option(None, "--author", "-a", help="Tek yazar analizi"),
    team: bool = typer.Option(False, "--team", "-t", help="Takım geneli özet"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
) -> None:
    """Geliştirici onboarding hızını ölç ve ramp-up eğrisini göster."""
    from codedna.onboarding import (
        get_author_curve, team_onboarding_summary, get_all_authors,
    )
    from codedna.plan import is_feature_available

    if not is_feature_available("sprint_health"):
        console.print(
            Panel(
                "[bold yellow]🔒 Bu özellik Team planında mevcut.[/bold yellow]\n"
                "[dim]Yükseltmek için:[/dim] [cyan]codedna plan activate <LICENSE_KEY>[/cyan]",
                border_style="yellow",
            )
        )
        raise typer.Exit(1)

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)
    init_db(db_yolu)

    console.print()

    if team or not author:
        # Takım özeti
        console.print("[bold cyan]🧬 CodeDNA[/bold cyan] — Onboarding takım özeti\n")

        with console.status("[dim]Analiz ediliyor...[/dim]"):
            ozet = team_onboarding_summary(db_yolu)

        if not ozet:
            console.print("[yellow]Kayıtlı yazar bulunamadı.[/yellow]")
            return

        tablo = Table(
            title="[bold cyan]🚀 Onboarding Özeti[/bold cyan]",
            border_style="dim",
            show_lines=True,
            header_style="bold",
        )
        tablo.add_column("Yazar", min_width=18)
        tablo.add_column("Commit", justify="right", min_width=8)
        tablo.add_column("Anketli", justify="right", min_width=9)
        tablo.add_column("Ramp-up", justify="center", min_width=12)
        tablo.add_column("Son Anlama", justify="center", min_width=12)

        for y in ozet:
            ramp_str = (
                f"{y['ramp_up_hafta']:.1f} hafta"
                if y["ramp_up_hafta"] is not None
                else ("[dim]Yeterli veri yok[/dim]" if not y["yeterli_veri"] else "[yellow]Eşik aşılmadı[/yellow]")
            )
            anlama_str = (
                f"{y['son_ort_anlama']:.1f}/5" if y["son_ort_anlama"] else "—"
            )
            tablo.add_row(
                y["yazar"],
                str(y["toplam_commit"]),
                str(y["anlama_skoru_olan"]),
                ramp_str,
                anlama_str,
            )

        console.print(tablo)

    else:
        # Tek yazar eğrisi
        console.print(f"[bold cyan]🧬 CodeDNA[/bold cyan] — [bold]{author}[/bold] onboarding eğrisi\n")

        with console.status("[dim]Analiz ediliyor...[/dim]"):
            egri = get_author_curve(author, db_yolu)

        if egri.toplam_commit == 0:
            console.print(f"[yellow]'{author}' yazarına ait commit bulunamadı.[/yellow]")
            return

        # Ramp-up panel
        ramp_str = (
            f"[green]{egri.ramp_up_hafta:.1f} hafta[/green]"
            if egri.ramp_up_hafta is not None
            else "[yellow]Eşik henüz aşılmadı[/yellow]"
            if egri.anlama_skoru_olan >= 5
            else "[dim]Yeterli veri yok (en az 5 commit)[/dim]"
        )

        anlama_str = (
            f"{egri.son_ort_anlama:.1f}/5" if egri.son_ort_anlama else "—"
        )

        console.print(
            Panel(
                f"[bold]Yazar:[/bold] {egri.yazar}\n"
                f"[bold]Toplam commit:[/bold] {egri.toplam_commit}\n"
                f"[bold]Anketli commit:[/bold] {egri.anlama_skoru_olan}\n"
                f"[bold]Tahmini ramp-up:[/bold] {ramp_str}\n"
                f"[bold]Son ort. anlama:[/bold] {anlama_str}",
                title="[bold cyan]🚀 Onboarding Analizi[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )

        # Commit bazlı tablo (anket verisi olanlar)
        anketli = [n for n in egri.noktalar if n.understanding_score is not None]
        if anketli:
            tablo = Table(border_style="dim", show_lines=True, header_style="bold")
            tablo.add_column("#", justify="right", min_width=4)
            tablo.add_column("Hash", style="dim", min_width=10)
            tablo.add_column("Tarih", min_width=12)
            tablo.add_column("Hafta", justify="right", min_width=7)
            tablo.add_column("Anlama", justify="center", min_width=10)

            for n in anketli:
                skor = n.understanding_score or 0.0
                renk = "green" if skor >= 4 else "yellow" if skor >= 2.5 else "red"
                tablo.add_row(
                    str(n.commit_no),
                    n.commit_hash[:8],
                    n.tarih.strftime("%Y-%m-%d"),
                    str(n.hafta_no),
                    f"[{renk}]{skor:.1f}/5[/{renk}]",
                )
            console.print(tablo)

    console.print()


# ---------------------------------------------------------------------------
# codedna pr-comment
# ---------------------------------------------------------------------------
@app.command(name="pr-comment")
def pr_comment(
    repo: Optional[str] = typer.Option(None, "--repo", help="owner/repo formatında repo (boşsa GITHUB_REPOSITORY env'den alınır)"),
    pr: Optional[int] = typer.Option(None, "--pr", help="PR numarası (boşsa event payload'dan algılanır)"),
    rate: float = typer.Option(75.0, "--rate", help="Teknik borç saatlik ücreti"),
) -> None:
    """GitHub PR'ına CodeDNA analiz yorumu bırak (mevcut yorumu günceller, spam yapmaz)."""
    import os
    from codedna.integrations.github_bot import (
        format_pr_comment, post_or_update_comment, github_actions_pr_bilgisi,
    )
    from codedna.tech_debt import calculate_repo_debt

    # Token — asla loglanmaz
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        console.print(
            "[bold red]Hata:[/bold red] GITHUB_TOKEN ortam değişkeni tanımlanmamış."
        )
        raise typer.Exit(1)

    # Repo ve PR numarası — önce parametre, sonra GitHub Actions env
    hedef_repo = repo
    hedef_pr = pr

    if not hedef_repo or not hedef_pr:
        bilgi = github_actions_pr_bilgisi()
        if bilgi:
            otomatik_repo, otomatik_pr = bilgi
            hedef_repo = hedef_repo or otomatik_repo
            hedef_pr = hedef_pr or otomatik_pr

    if not hedef_repo or not hedef_pr:
        console.print(
            "[bold red]Hata:[/bold red] Repo ve PR numarası bulunamadı.\n"
            "[dim]--repo owner/repo --pr 42 ile belirtin veya GitHub Actions içinde çalıştırın.[/dim]"
        )
        raise typer.Exit(1)

    kok = find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)
    init_db(db_yolu)

    console.print(f"\n[bold cyan]🧬 CodeDNA[/bold cyan] — PR #{hedef_pr} analiz ediliyor...\n")

    with console.status("[dim]Dosyalar taranıyor...[/dim]"):
        from codedna.scorer import scan_repository
        sonuclar = scan_repository(kok, max_files=200)

    debt_ozeti_dict: Optional[dict] = None
    try:
        debt = calculate_repo_debt(kok, db_yolu, hourly_rate=rate)
        debt_ozeti_dict = {
            "toplam_debt_saatleri": debt.toplam_debt_saatleri,
            "toplam_aylik_maliyet_usd": debt.toplam_aylik_maliyet_usd,
        }
    except Exception:
        pass

    yorum = format_pr_comment(sonuclar, debt_ozeti_dict)

    try:
        sonuc = post_or_update_comment(hedef_repo, hedef_pr, yorum, token)
        yorum_url = sonuc.get("html_url", "")
        console.print(
            f"[green]✓[/green] PR yorumu gönderildi: [dim]{yorum_url}[/dim]\n"
        )
    except RuntimeError as e:
        console.print(f"[bold red]Hata:[/bold red] GitHub API isteği başarısız: {e}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# codedna protect
# ---------------------------------------------------------------------------
protect_app = typer.Typer(help="Korumalı modül yönetimi.")
app.add_typer(protect_app, name="protect")


@protect_app.command("add")
def protect_add(
    file_path: str = typer.Argument(..., help="Korunacak dosya yolu"),
    threshold: float = typer.Option(3.5, "--threshold", "-t", help="Minimum anlama skoru eşiği"),
    label: str = typer.Option("", "--label", "-l", help="İnsan okunabilir etiket"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
) -> None:
    """Bir dosyayı korumalı modül olarak işaretle."""
    from codedna.protection import protect_module
    from codedna.plan import is_feature_available

    if not is_feature_available("bus_factor"):
        console.print("[bold yellow]🔒 Bu özellik Team planında mevcut.[/bold yellow]")
        raise typer.Exit(1)

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)
    init_db(db_yolu)

    # Göreli yolu tam yola çevir
    tam_yol = str((kok / file_path).resolve())
    etiket = label or file_path
    yazar = "cli"

    kayit_id = protect_module(tam_yol, threshold, etiket, yazar, db_yolu)
    console.print(
        f"[green]✓[/green] Korumalı modül eklendi: [cyan]{file_path}[/cyan]\n"
        f"  [dim]Etiket:[/dim] {etiket} · [dim]Eşik:[/dim] {threshold}/5 · [dim]ID:[/dim] #{kayit_id}"
    )


@protect_app.command("remove")
def protect_remove(
    file_path: str = typer.Argument(..., help="Koruma kaldırılacak dosya yolu"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
) -> None:
    """Bir dosyadan korumayı kaldır."""
    from codedna.protection import unprotect_module
    from codedna.plan import is_feature_available

    if not is_feature_available("bus_factor"):
        console.print("[bold yellow]🔒 Bu özellik Team planında mevcut.[/bold yellow]")
        raise typer.Exit(1)

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)
    tam_yol = str((kok / file_path).resolve())

    if unprotect_module(tam_yol, db_yolu):
        console.print(f"[green]✓[/green] Koruma kaldırıldı: [cyan]{file_path}[/cyan]")
    else:
        console.print(f"[yellow]Bulunamadı:[/yellow] '{file_path}' korumalı modüller arasında yok.")


@protect_app.command("list")
def protect_list(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
) -> None:
    """Tüm korumalı modülleri ve durumlarını göster."""
    from codedna.protection import check_protected_modules
    from codedna.plan import is_feature_available

    if not is_feature_available("bus_factor"):
        console.print("[bold yellow]🔒 Bu özellik Team planında mevcut.[/bold yellow]")
        raise typer.Exit(1)

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)
    init_db(db_yolu)

    moduller = check_protected_modules(db_yolu)
    if not moduller:
        console.print("[yellow]Henüz korumalı modül yok.[/yellow]")
        console.print("[dim]Eklemek için:[/dim] [cyan]codedna protect add <dosya> --label 'Etiket'[/cyan]")
        return

    tablo = Table(
        title="[bold cyan]🛡️ Korumalı Modüller[/bold cyan]",
        border_style="dim", show_lines=True, header_style="bold",
    )
    tablo.add_column("Dosya", min_width=30)
    tablo.add_column("Etiket", min_width=16)
    tablo.add_column("Eşik", justify="center", min_width=7)
    tablo.add_column("Mevcut", justify="center", min_width=9)
    tablo.add_column("Durum", justify="center", min_width=12)

    for m in moduller:
        mevcut_str = f"{m.mevcut_skor:.1f}" if m.mevcut_skor is not None else "—"
        if m.durum == "İHLAL":
            durum_str = "[bold red]🔴 İHLAL[/bold red]"
        elif m.durum == "GÜVENLİ":
            durum_str = "[green]✅ GÜVENLİ[/green]"
        else:
            durum_str = "[dim]⚪ BİLİNMİYOR[/dim]"

        try:
            goreceli = str(Path(m.dosya_yolu).relative_to(kok))
        except ValueError:
            goreceli = m.dosya_yolu[-40:]

        tablo.add_row(goreceli, m.etiket, f"{m.esik:.1f}", mevcut_str, durum_str)

    console.print()
    console.print(tablo)
    console.print()


@protect_app.command("check")
def protect_check(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
) -> None:
    """Sadece eşik altına düşmüş (ihlaldeki) modülleri göster."""
    from codedna.protection import get_violations
    from codedna.plan import is_feature_available

    if not is_feature_available("bus_factor"):
        console.print("[bold yellow]🔒 Bu özellik Team planında mevcut.[/bold yellow]")
        raise typer.Exit(1)

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)
    init_db(db_yolu)

    ihlaller = get_violations(db_yolu)
    if not ihlaller:
        console.print("[green]✅ Tüm korumalı modüller güvende.[/green]")
        return

    console.print()
    for ihlal in ihlaller:
        skor_str = f"{ihlal.mevcut_skor:.1f}" if ihlal.mevcut_skor else "?"
        try:
            goreceli = str(Path(ihlal.dosya_yolu).relative_to(kok))
        except ValueError:
            goreceli = ihlal.dosya_yolu
        console.print(
            f"[bold red]⚠️  İHLAL:[/bold red] [cyan]{goreceli}[/cyan] — "
            f"anlama: [red]{skor_str}[/red] < eşik: [yellow]{ihlal.esik:.1f}[/yellow] "
            f"([dim]{ihlal.etiket}[/dim])"
        )
    console.print()


# ---------------------------------------------------------------------------
# codedna interview
# ---------------------------------------------------------------------------
interview_app = typer.Typer(help="Aday mülakat aracı.")
app.add_typer(interview_app, name="interview")


@interview_app.command("start")
def interview_start(
    candidate: str = typer.Option(..., "--candidate", "-c", help="Aday adı"),
    difficulty: str = typer.Option("medium", "--difficulty", "-d", help="Zorluk: easy|medium|hard"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
) -> None:
    """Yeni mülakat oturumu başlat ve anonimleştirilmiş kod göster."""
    from codedna.interview import select_candidate_file, generate_questions, start_session
    from codedna.plan import is_feature_available

    if not is_feature_available("interview_tool"):
        console.print(
            Panel(
                "[bold yellow]🔒 Bu özellik Enterprise planında mevcut.[/bold yellow]\n"
                "[dim]Yükseltmek için:[/dim] [cyan]codedna plan activate <LICENSE_KEY>[/cyan]",
                border_style="yellow",
            )
        )
        raise typer.Exit(1)

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)
    init_db(db_yolu)

    console.print()
    console.print(
        "[dim]⚠️  Bu araç insan değerlendirmesinin YERİNE GEÇMEZ — tamamlayıcı bir sinyaldir.[/dim]\n"
    )

    with console.status("[dim]Uygun dosya seçiliyor...[/dim]"):
        dosya = select_candidate_file(kok, db_yolu, difficulty)

    if not dosya:
        console.print(f"[yellow]'{difficulty}' zorluğunda uygun dosya bulunamadı.[/yellow]")
        raise typer.Exit(1)

    sorular = generate_questions(dosya.anonimlestirilmis_kod)
    session_id = start_session(candidate, dosya.dosya_yolu, sorular, db_yolu)

    console.print(
        Panel(
            f"[bold]Aday:[/bold] {candidate}\n"
            f"[bold]Zorluk:[/bold] {difficulty} · [dim]Karmaşıklık:[/dim] {dosya.karmasiklik_skoru:.0f} · [dim]Satır:[/dim] {dosya.satir_sayisi}\n"
            f"[bold]Oturum ID:[/bold] [cyan]#{session_id}[/cyan]",
            title="[bold cyan]🎯 Mülakat Başladı[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    console.print("\n[bold]─── Anonimleştirilmiş Kod ───[/bold]")
    console.print(f"[dim]{dosya.anonimlestirilmis_kod[:800]}[/dim]")
    if len(dosya.anonimlestirilmis_kod) > 800:
        console.print("[dim]... (kısaltıldı)[/dim]")

    console.print("\n[bold]─── Sorular ───[/bold]")
    for i, soru in enumerate(sorular, 1):
        console.print(f"  [bold cyan]{i}.[/bold cyan] {soru}")

    console.print(
        f"\n[dim]Değerlendirme için:[/dim] [cyan]codedna interview score {session_id} --score 4.0 --notes 'Not'[/cyan]\n"
    )


@interview_app.command("list")
def interview_list(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
    limit: int = typer.Option(10, "--limit", "-n", help="Gösterilecek oturum sayısı"),
) -> None:
    """Geçmiş mülakat oturumlarını göster."""
    from codedna.interview import get_sessions
    from codedna.plan import is_feature_available

    if not is_feature_available("interview_tool"):
        console.print("[bold yellow]🔒 Bu özellik Enterprise planında mevcut.[/bold yellow]")
        raise typer.Exit(1)

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)
    init_db(db_yolu)

    oturumlar = get_sessions(db_yolu, limit=limit)
    if not oturumlar:
        console.print("[yellow]Henüz mülakat oturumu yok.[/yellow]")
        return

    tablo = Table(
        title="[bold cyan]🎯 Mülakat Geçmişi[/bold cyan]",
        border_style="dim", show_lines=True, header_style="bold",
    )
    tablo.add_column("#", justify="right", min_width=4)
    tablo.add_column("Aday", min_width=16)
    tablo.add_column("Başlangıç", min_width=17)
    tablo.add_column("Skor", justify="center", min_width=8)
    tablo.add_column("Notlar", min_width=20)

    for o in oturumlar:
        skor_str = f"{o['skor']:.1f}/5" if o["skor"] is not None else "[dim]—[/dim]"
        tablo.add_row(
            str(o["id"]),
            o["aday"] or "?",
            o["baslangic"] or "?",
            skor_str,
            (o["notlar"] or "")[:30],
        )

    console.print()
    console.print(tablo)
    console.print()


@interview_app.command("score")
def interview_score(
    session_id: int = typer.Argument(..., help="Oturum ID'si"),
    score: float = typer.Option(..., "--score", "-s", help="0.0–5.0 arası puan"),
    notes: str = typer.Option("", "--notes", "-n", help="Değerlendirici notları"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
) -> None:
    """Mülakat oturumuna insan değerlendirmesi puanı ekle."""
    from codedna.interview import submit_score
    from codedna.plan import is_feature_available

    if not is_feature_available("interview_tool"):
        console.print("[bold yellow]🔒 Bu özellik Enterprise planında mevcut.[/bold yellow]")
        raise typer.Exit(1)

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)

    try:
        sonuc = submit_score(session_id, score, notes, db_yolu)
        console.print(
            f"[green]✓[/green] Değerlendirme kaydedildi: "
            f"Oturum [cyan]#{session_id}[/cyan] → [bold]{score:.1f}/5[/bold]"
        )
        if notes:
            console.print(f"  [dim]Not:[/dim] {notes}")
    except ValueError as e:
        console.print(f"[bold red]Hata:[/bold red] {e}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# codedna bus-factor
# ---------------------------------------------------------------------------
@app.command(name="bus-factor")
def bus_factor(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
    critical: bool = typer.Option(False, "--critical", "-c", help="Sadece kritik (bus_factor=1) dosyaları göster"),
    max_files: int = typer.Option(500, "--max", "-m", help="İşlenecek maksimum dosya sayısı"),
) -> None:
    """Repo genelinde bus factor analizi yap ve kritik sahiplik risklerini göster."""
    from codedna.bus_factor import calculate_bus_factor, get_at_risk_files, _BUYUK_REPO_ESIGI
    from codedna.plan import is_feature_available

    # Plan kontrolü
    if not is_feature_available("bus_factor"):
        console.print(
            Panel(
                "[bold yellow]🔒 Bu özellik Team planında mevcut.[/bold yellow]\n"
                "[dim]This feature is available on Team plan.[/dim]\n\n"
                "[dim]Yükseltmek için:[/dim] [cyan]codedna plan activate <LICENSE_KEY>[/cyan]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        raise typer.Exit(1)

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)
    init_db(db_yolu)

    if max_files > _BUYUK_REPO_ESIGI:
        console.print(
            f"[yellow]⚠[/yellow]  {max_files} dosya taranacak — büyük repolar için yavaş olabilir."
        )

    console.print()
    console.print("[bold cyan]🧬 CodeDNA[/bold cyan] — Bus Factor analizi çalışıyor...\n")

    with console.status("[dim]git blame çalıştırılıyor...[/dim]"):
        if critical:
            sonuclar = get_at_risk_files(kok, db_yolu)
        else:
            sonuclar = calculate_bus_factor(kok, db_yolu, max_dosya=max_files)

    if not sonuclar:
        console.print("[yellow]Analiz edilecek dosya bulunamadı.[/yellow]")
        return

    # Tablo
    tablo = Table(
        title="",
        border_style="dim",
        show_lines=True,
        header_style="bold",
    )
    tablo.add_column("Dosya", style="white", min_width=30)
    tablo.add_column("Bus Factor", justify="center", min_width=11)
    tablo.add_column("Ana Sahip", min_width=16)
    tablo.add_column("Sahiplik %", justify="right", min_width=11)
    tablo.add_column("Risk", justify="center", min_width=10)

    kritik_sayisi = 0
    for s in sonuclar:
        bf_str = str(s.bus_factor)
        if s.risk == "KRİTİK":
            bf_goster = f"[red]🚌 {bf_str}[/red]"
            risk_goster = "[bold red]KRİTİK[/bold red]"
            kritik_sayisi += 1
        elif s.risk == "RİSKLİ":
            bf_goster = f"[yellow]🚌 {bf_str}[/yellow]"
            risk_goster = "[yellow]RİSKLİ[/yellow]"
        else:
            bf_goster = f"[green]🚌 {bf_str}[/green]"
            risk_goster = "[green]GÜVENLİ[/green]"

        tablo.add_row(
            s.dosya_yolu,
            bf_goster,
            s.birincil_sahip or "?",
            f"%{s.sahiplik_yuzdesi:.1f}",
            risk_goster,
        )

    console.print(tablo)
    console.print(
        f"\n[bold]Özet:[/bold] {len(sonuclar)} dosya · "
        f"[red]{kritik_sayisi} kritik[/red] · "
        f"[dim]Eşik: anlama skoru ≥ 3.5[/dim]\n"
    )


# ---------------------------------------------------------------------------
# codedna debt
# ---------------------------------------------------------------------------
@app.command()
def debt(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
    rate: float = typer.Option(75.0, "--rate", help="Saatlik maliyet ($/saat)"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Tek dosya analizi"),
) -> None:
    """Repo genelinde teknik borç maliyeti hesapla."""
    from codedna.tech_debt import calculate_repo_debt, calculate_file_debt
    from codedna.plan import get_current_plan, Plan

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)
    init_db(db_yolu)

    mevcut_plan = get_current_plan()
    dolar_gizli = mevcut_plan == Plan.FREE  # Free planda dolar tutarı gizli

    console.print()
    console.print("[bold cyan]🧬 CodeDNA[/bold cyan] — Teknik borç hesaplanıyor...\n")

    # Tek dosya modu
    if file:
        # Göreli yolu tam yola çevir
        tam_dosya = (kok / file).resolve() if not file.is_absolute() else file
        with console.status("[dim]Analiz ediliyor...[/dim]"):
            borc = calculate_file_debt(str(tam_dosya), db_yolu, hourly_rate=rate)

        if not borc:
            console.print(f"[yellow]Uyarı:[/yellow] '{file}' için veri bulunamadı.")
            return

        risk_renk = {"KRİTİK": "red", "YÜKSEK": "yellow", "ORTA": "yellow", "DÜŞÜK": "green"}.get(
            borc.risk_seviyesi, "white"
        )
        maliyet_str = (
            f"[dim]Pro+ plan gerekli[/dim]"
            if dolar_gizli
            else f"[bold green]${borc.aylik_maliyet_usd:.2f}/ay[/bold green]"
        )

        console.print(
            Panel(
                f"[bold]Dosya:[/bold] [dim]{borc.dosya_yolu}[/dim]\n"
                f"[bold]Borç saati:[/bold] {borc.debt_saatleri:.1f} saat\n"
                f"[bold]Aylık maliyet:[/bold] {maliyet_str}\n"
                f"[bold]Risk:[/bold] [{risk_renk}]{borc.risk_seviyesi}[/{risk_renk}]\n"
                f"[bold]AI olasılığı:[/bold] %{borc.ai_olasiligi*100:.0f} · "
                f"[bold]Karmaşıklık:[/bold] {borc.karmasiklik:.0f} · "
                f"[bold]Satır:[/bold] {borc.toplam_satir}",
                title="[bold cyan]💰 Teknik Borç — Dosya Detayı[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        return

    # Repo genel modu
    with console.status("[dim]Tüm dosyalar analiz ediliyor...[/dim]"):
        ozet = calculate_repo_debt(kok, db_yolu, hourly_rate=rate)

    maliyet_str = (
        "[dim]🔒 Pro+ plan gerekli[/dim]"
        if dolar_gizli
        else f"[bold green]${ozet.toplam_aylik_maliyet_usd:.2f}/ay[/bold green]"
    )

    console.print(
        Panel(
            f"[bold]💰 Teknik Borç Özeti[/bold]\n\n"
            f"[bold]Toplam tahmini borç:[/bold] [cyan]{ozet.toplam_debt_saatleri:.1f} saat[/cyan]\n"
            f"[bold]Aylık maliyet:[/bold] {maliyet_str}\n"
            f"[bold]Saatlik ücret:[/bold] [dim]${rate:.0f}/saat[/dim]\n"
            f"[bold]Analiz edilen dosya:[/bold] {ozet.toplam_dosya}",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    if ozet.en_pahali_5:
        console.print("[bold]En maliyetli 5 dosya:[/bold]")
        tablo = Table(border_style="dim", show_lines=True, header_style="bold")
        tablo.add_column("Dosya", style="white", min_width=30)
        tablo.add_column("Borç Saati", justify="right", min_width=11)
        tablo.add_column("Aylık", justify="right", min_width=10)
        tablo.add_column("Risk", justify="center", min_width=10)

        for d in ozet.en_pahali_5:
            risk_renk = {
                "KRİTİK": "red", "YÜKSEK": "yellow",
                "ORTA": "yellow", "DÜŞÜK": "green",
            }.get(d.risk_seviyesi, "white")

            aylik = (
                "[dim]gizli[/dim]"
                if dolar_gizli
                else f"[{risk_renk}]${d.aylik_maliyet_usd:.2f}[/{risk_renk}]"
            )

            # Dosya yolunu kısalt
            try:
                goreceli = str(Path(d.dosya_yolu).relative_to(kok))
            except ValueError:
                goreceli = d.dosya_yolu[-40:]

            tablo.add_row(
                goreceli,
                f"{d.debt_saatleri:.1f} saat",
                aylik,
                f"[{risk_renk}]{d.risk_seviyesi}[/{risk_renk}]",
            )
        console.print(tablo)

    if dolar_gizli:
        console.print(
            "\n[dim]💡 Dolar tutarları Pro+ planda görünür: [cyan]codedna plan activate <KEY>[/cyan][/dim]\n"
        )
    else:
        console.print()


# ---------------------------------------------------------------------------
# codedna sprint
# ---------------------------------------------------------------------------
sprint_app = typer.Typer(help="Sprint yönetimi ve sağlık skoru.")
app.add_typer(sprint_app, name="sprint")


@sprint_app.command("create")
def sprint_olustur(
    name: str = typer.Option(..., "--name", "-n", help="Sprint ismi"),
    start: str = typer.Option(..., "--start", "-s", help="Başlangıç tarihi (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", "-e", help="Bitiş tarihi (YYYY-MM-DD)"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
) -> None:
    """Yeni sprint oluştur ve sağlık skoru hesapla."""
    from datetime import datetime as dt
    from codedna.sprint_health import calculate_sprint_health, save_sprint_result
    from codedna.plan import is_feature_available

    if not is_feature_available("sprint_health"):
        console.print(
            Panel(
                "[bold yellow]🔒 Bu özellik Team planında mevcut.[/bold yellow]\n"
                "[dim]This feature is available on Team plan.[/dim]\n\n"
                "[dim]Yükseltmek için:[/dim] [cyan]codedna plan activate <LICENSE_KEY>[/cyan]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        raise typer.Exit(1)

    # Tarihleri parse et
    try:
        baslangic = dt.fromisoformat(start)
        bitis = dt.fromisoformat(end)
    except ValueError:
        console.print(f"[bold red]Hata:[/bold red] Geçersiz tarih formatı. Kullanım: YYYY-MM-DD")
        raise typer.Exit(1)

    if bitis <= baslangic:
        console.print("[bold red]Hata:[/bold red] Bitiş tarihi başlangıçtan sonra olmalı.")
        raise typer.Exit(1)

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)
    init_db(db_yolu)

    console.print()
    console.print(f"[bold cyan]🧬 CodeDNA[/bold cyan] — [bold]{name}[/bold] sprint analizi çalışıyor...\n")

    with console.status("[dim]Commit'ler analiz ediliyor...[/dim]"):
        sonuc = calculate_sprint_health(kok, db_yolu, baslangic, bitis, name)

    sprint_id = save_sprint_result(sonuc, db_yolu)

    durum_renk = {
        "SAĞLIKLI": "green", "DİKKAT": "yellow", "RİSKLİ": "red"
    }.get(sonuc.durum, "white")

    console.print(
        Panel(
            f"[bold]Sprint:[/bold] {sonuc.sprint_adi}\n"
            f"[bold]Tarih:[/bold] {start} → {end}\n"
            f"[bold]Sağlık Skoru:[/bold] [{durum_renk}]{sonuc.health_score:.1f}/100 ({sonuc.durum})[/{durum_renk}]\n"
            f"[bold]Toplam Commit:[/bold] {sonuc.toplam_commit}\n"
            f"[bold]Ort. Anlama:[/bold] {f'{sonuc.avg_understanding:.1f}/5' if sonuc.avg_understanding else 'Veri yok'}\n"
            f"[bold]AI Oranı:[/bold] %{sonuc.ai_orani * 100:.0f} yüksek riskli\n"
            f"[bold]Borç Delta:[/bold] {sonuc.debt_delta_saati:.1f} saat/commit",
            title=f"[bold cyan]🏃 Sprint Sağlık Raporu — #{sprint_id}[/bold cyan]",
            border_style=durum_renk,
            padding=(1, 2),
        )
    )
    console.print(f"[dim]Sprint #{sprint_id} kaydedildi.[/dim]\n")


@sprint_app.command("health")
def sprint_sagligi(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
) -> None:
    """Son sprint'in sağlık skorunu göster."""
    from codedna.db import get_latest_sprint
    from codedna.plan import is_feature_available

    if not is_feature_available("sprint_health"):
        console.print(
            Panel(
                "[bold yellow]🔒 Bu özellik Team planında mevcut.[/bold yellow]\n"
                "[dim]Yükseltmek için:[/dim] [cyan]codedna plan activate <LICENSE_KEY>[/cyan]",
                border_style="yellow",
            )
        )
        raise typer.Exit(1)

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)
    init_db(db_yolu)

    sprint = get_latest_sprint(db_path=db_yolu)
    if not sprint:
        console.print("[yellow]Henüz kayıtlı sprint yok.[/yellow]")
        console.print("[dim]Oluşturmak için:[/dim] [cyan]codedna sprint create --name 'Sprint 1' --start 2026-06-01 --end 2026-06-14[/cyan]")
        return

    skor = sprint["health_score"] or 0.0
    durum = "SAĞLIKLI" if skor >= 80 else "DİKKAT" if skor >= 50 else "RİSKLİ"
    durum_renk = {"SAĞLIKLI": "green", "DİKKAT": "yellow", "RİSKLİ": "red"}[durum]

    from datetime import datetime as dt
    bas = dt.fromtimestamp(sprint["start_date"]).strftime("%Y-%m-%d") if sprint["start_date"] else "?"
    bit = dt.fromtimestamp(sprint["end_date"]).strftime("%Y-%m-%d") if sprint["end_date"] else "?"

    anlama_val = sprint["avg_understanding"]
    anlama_str = f"{anlama_val:.1f}/5" if anlama_val else "Veri yok"
    delta_val = sprint["debt_delta_hours"] or 0.0

    console.print()
    console.print(
        Panel(
            f"[bold]Sprint:[/bold] {sprint['sprint_name']}\n"
            f"[bold]Tarih:[/bold] {bas} → {bit}\n"
            f"[bold]Sağlık Skoru:[/bold] [{durum_renk}]{skor:.1f}/100 ({durum})[/{durum_renk}]\n"
            f"[bold]Ort. Anlama:[/bold] {anlama_str}\n"
            f"[bold]Borç Delta:[/bold] {delta_val:.1f} saat/commit",
            title="[bold cyan]🏃 Son Sprint Sağlığı[/bold cyan]",
            border_style=durum_renk,
            padding=(1, 2),
        )
    )


@sprint_app.command("history")
def sprint_gecmisi(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
    limit: int = typer.Option(10, "--limit", "-n", help="Gösterilecek sprint sayısı"),
) -> None:
    """Geçmiş sprint'leri tablo olarak göster."""
    from codedna.db import get_sprint_history as db_sprint_gecmisi
    from codedna.plan import is_feature_available
    from datetime import datetime as dt

    if not is_feature_available("sprint_health"):
        console.print("[bold yellow]🔒 Bu özellik Team planında mevcut.[/bold yellow]")
        raise typer.Exit(1)

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)
    init_db(db_yolu)

    sprintler = db_sprint_gecmisi(limit=limit, db_path=db_yolu)
    if not sprintler:
        console.print("[yellow]Henüz kayıtlı sprint yok.[/yellow]")
        return

    tablo = Table(
        title=f"[bold cyan]🏃 Sprint Geçmişi — Son {len(sprintler)}[/bold cyan]",
        border_style="dim",
        show_lines=True,
        header_style="bold",
    )
    tablo.add_column("Sprint", min_width=16)
    tablo.add_column("Tarih Aralığı", min_width=22)
    tablo.add_column("Sağlık", justify="center", min_width=14)
    tablo.add_column("Anlama", justify="center", min_width=10)
    tablo.add_column("Borç Delta", justify="right", min_width=11)

    for s in sprintler:
        skor = s["health_score"] or 0.0
        durum = "SAĞLIKLI" if skor >= 80 else "DİKKAT" if skor >= 50 else "RİSKLİ"
        renk = {"SAĞLIKLI": "green", "DİKKAT": "yellow", "RİSKLİ": "red"}[durum]

        bas = dt.fromtimestamp(s["start_date"]).strftime("%Y-%m-%d") if s["start_date"] else "?"
        bit = dt.fromtimestamp(s["end_date"]).strftime("%Y-%m-%d") if s["end_date"] else "?"

        anlama_str = f"{s['avg_understanding']:.1f}/5" if s["avg_understanding"] else "—"
        delta_str = f"{s['debt_delta_hours']:.1f}s" if s["debt_delta_hours"] else "—"

        tablo.add_row(
            s["sprint_name"] or "?",
            f"{bas} → {bit}",
            f"[{renk}]{skor:.0f}/100 {durum}[/{renk}]",
            anlama_str,
            delta_str,
        )

    console.print()
    console.print(tablo)
    console.print()


# ---------------------------------------------------------------------------
# codedna plan
# ---------------------------------------------------------------------------
@app.command()
def plan(
    komut: Optional[str] = typer.Argument(
        None,
        help="'activate' veya doğrudan lisans anahtarı",
    ),
    anahtar: Optional[str] = typer.Argument(
        None,
        help="Lisans anahtarı (activate ile birlikte kullanılır)",
    ),
) -> None:
    """Mevcut planı göster veya lisans anahtarı ile plan aktif et.

    Kullanım:
      codedna plan                       # mevcut planı göster
      codedna plan activate <KEY>        # lisans aktif et
      codedna plan <KEY>                 # kısa yol
    """
    from codedna.plan import (
        Plan as PlanEnum,
        get_current_plan,
        activate_license,
        get_plan_limits,
    )

    # "activate <KEY>" veya doğrudan "<KEY>" syntax'ı destekle
    lisans_anahtari: Optional[str] = None
    if komut == "activate" and anahtar:
        lisans_anahtari = anahtar
    elif komut and komut != "activate":
        lisans_anahtari = komut

    if lisans_anahtari:
        # Lisans aktifleştirme
        try:
            aktif_plan = activate_license(lisans_anahtari)
            console.print(
                Panel(
                    f"[bold green]✓ Lisans aktif edildi![/bold green]\n\n"
                    f"[bold]Plan:[/bold] [cyan]{aktif_plan.value.upper()}[/cyan]\n"
                    f"[bold]Anahtar:[/bold] [dim]{lisans_anahtari[:12]}...[/dim]",
                    border_style="green",
                    padding=(1, 2),
                )
            )
        except ValueError as e:
            console.print(f"[bold red]Hata:[/bold red] {e}")
            raise typer.Exit(1)
        return

    # Mevcut planı göster
    mevcut = get_current_plan()
    limitler = get_plan_limits()

    plan_renk = {
        PlanEnum.FREE: "dim",
        PlanEnum.PRO: "cyan",
        PlanEnum.TEAM: "green",
        PlanEnum.ENTERPRISE: "yellow",
    }.get(mevcut, "white")

    tablo = Table(border_style="dim", show_header=False, padding=(0, 1))
    tablo.add_column("Özellik", style="dim")
    tablo.add_column("Değer", style="white")

    for k, v in limitler.items():
        if isinstance(v, bool):
            goster = "[green]✓[/green]" if v else "[red]✗[/red]"
        elif isinstance(v, int) and v == -1:
            goster = "[dim]Sınırsız[/dim]"
        else:
            goster = str(v)
        tablo.add_row(k.replace("_", " ").title(), goster)

    console.print()
    console.print(
        Panel(
            f"[bold]Mevcut Plan / Current Plan:[/bold] [{plan_renk}]{mevcut.value.upper()}[/{plan_renk}]\n\n"
            + (
                "[dim]Lisans aktif etmek için:[/dim] [cyan]codedna plan activate <LICENSE_KEY>[/cyan]"
                if mevcut == PlanEnum.FREE
                else "[dim]Yükseltmek için:[/dim] [cyan]codedna plan activate <LICENSE_KEY>[/cyan]"
            ),
            title="[bold cyan]🧬 CodeDNA Plan[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print(tablo)
    console.print()


# ---------------------------------------------------------------------------
# codedna dashboard
# ---------------------------------------------------------------------------
@app.command()
def dashboard(
    api_port: int = typer.Option(8000, "--api-port", help="FastAPI port numarası"),
    ui_port: int = typer.Option(3000, "--ui-port", help="Next.js dashboard port numarası"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
) -> None:
    """FastAPI + Next.js dashboard'u başlat ve tarayıcıda aç."""
    import os
    import subprocess
    import time
    import webbrowser

    kok = repo or find_git_root() or Path.cwd()
    db_yolu = _get_db(kok)
    init_db(db_yolu)

    # dashboard/ klasörünü bul — CLI'nin bulunduğu yere göre veya CWD'ye göre
    dashboard_yollari = [
        Path(__file__).parent.parent / "dashboard",
        Path.cwd() / "dashboard",
        kok / "dashboard",
    ]
    dashboard_kok = next((p for p in dashboard_yollari if (p / "package.json").exists()), None)

    if not dashboard_kok:
        console.print(
            "[bold red]Hata:[/bold red] dashboard/ klasörü bulunamadı.\n"
            "[dim]codedna proje kökünde 'dashboard/' klasörü olmalı.[/dim]"
        )
        raise typer.Exit(1)

    console.print()
    console.print(
        Panel(
            f"[bold cyan]🧬 CodeDNA Panosu[/bold cyan] başlatılıyor...\n\n"
            f"[bold]API:[/bold]       [link]http://localhost:{api_port}[/link]\n"
            f"[bold]Dashboard:[/bold] [link]http://localhost:{ui_port}[/link]\n\n"
            "[dim]Durdurmak için Ctrl+C[/dim]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # Ortam değişkenlerini ayarla
    env = os.environ.copy()
    env["CODEDNA_REPO_PATH"] = str(kok)
    env["CODEDNA_DB_PATH"] = str(db_yolu)
    env["NEXT_PUBLIC_API_URL"] = f"http://localhost:{api_port}"

    # FastAPI sürecini başlat — venv Python'unu kullan
    import sys
    python_bin = sys.executable

    api_proc = subprocess.Popen(
        [
            python_bin, "-m", "uvicorn",
            "codedna.api:app",
            "--host", "127.0.0.1",
            "--port", str(api_port),
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Next.js npm run dev başlat — node_modules/.bin/next'i doğrudan çağır
    next_bin = dashboard_kok / "node_modules" / ".bin" / "next"
    npm_cmd = str(next_bin) if next_bin.exists() else "npm"
    ui_cmd = (
        [npm_cmd, "dev", "--port", str(ui_port)]
        if next_bin.exists()
        else ["npm", "run", "dev", "--", "--port", str(ui_port)]
    )
    ui_proc = subprocess.Popen(
        ui_cmd,
        cwd=str(dashboard_kok),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Başlaması için bekle, sonra tarayıcıyı aç
    console.print("[dim]Sunucular başlatılıyor...[/dim]")
    time.sleep(4)

    try:
        webbrowser.open(f"http://localhost:{ui_port}")
        console.print(f"[green]✓[/green] Tarayıcı açıldı: [link]http://localhost:{ui_port}[/link]")
        console.print("[dim]Ctrl+C ile durdur[/dim]\n")

        # Her iki süreci bekle
        api_proc.wait()
    except KeyboardInterrupt:
        console.print("\n[yellow]Durduruluyor...[/yellow]")
    finally:
        # Her iki süreci de temizle
        for proc in [api_proc, ui_proc]:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        console.print("[dim]CodeDNA durduruldu.[/dim]")


# ---------------------------------------------------------------------------
# codedna uninstall (bonus)
# ---------------------------------------------------------------------------
@app.command()
def uninstall(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo dizini"),
) -> None:
    """CodeDNA hook'unu kaldır."""
    kok = repo or find_git_root()
    if uninstall_hook(kok):
        console.print("[green]✓[/green] CodeDNA kaldırıldı.")
    else:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------
def _kisalt_yol(tam_yol: str, kok: str) -> str:
    """Uzun yolları repo köküne göre kısalt."""
    try:
        goreceli = Path(tam_yol).relative_to(Path(kok))
        yol_str = str(goreceli)
        if len(yol_str) > 40:
            parcalar = Path(yol_str).parts
            if len(parcalar) > 3:
                return f".../{'/'.join(parcalar[-2:])}"
        return yol_str
    except ValueError:
        return tam_yol[-40:] if len(tam_yol) > 40 else tam_yol


def _risk_etiketi(yuzde: float) -> tuple[str, str]:
    """AI yüzdesine göre risk etiketi ve renk döndür."""
    if yuzde >= 70:
        return "YÜKSEK", "red"
    elif yuzde >= 40:
        return "ORTA", "yellow"
    else:
        return "DÜŞÜK", "green"


def main() -> None:
    """CLI giriş noktası."""
    app()


if __name__ == "__main__":
    main()
