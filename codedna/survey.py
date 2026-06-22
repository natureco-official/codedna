"""Commit anlama anketi modülü."""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt
from rich.text import Text

console = Console()


def _skor_al(soru: str, soru_no: int) -> Optional[int]:
    """
    1-5 arasında geçerli bir skor al.
    Boş bırakılırsa None döner (anket atlandı).
    """
    try:
        deger = IntPrompt.ask(
            f"  [bold cyan]{soru_no}.[/bold cyan] {soru} [dim]\\[1-5][/dim]",
            default=0,
        )
        if deger == 0:
            return None
        return max(1, min(5, deger))
    except (KeyboardInterrupt, EOFError):
        return None


def run_survey(commit_hash: str) -> Optional[float]:
    """
    Post-commit hook sonrası 3 soruluk anlama anketi çalıştır.

    Args:
        commit_hash: Anketin bağlandığı commit hash'i

    Returns:
        Ortalama anlama skoru (1.0-5.0), kullanıcı atlarsa None
    """
    console.print()
    console.print(
        Panel(
            Text.from_markup(
                f"[bold yellow]CodeDNA[/bold yellow] — Commit [dim]{commit_hash[:8]}[/dim] için hızlı anlama anketi\n"
                "[dim]Enter ile atlayabilirsin (0 = atla)[/dim]"
            ),
            border_style="yellow",
            padding=(0, 2),
        )
    )

    sorular = [
        "Bu değişikliği 3 ay sonra açıklayabilir misin?",
        "Bir hata çıksa debug edebilir misin?",
        "Başkası sorsa, nasıl çalıştığını anlatabilir misin?",
    ]

    skorlar: list[int] = []
    for i, soru in enumerate(sorular, start=1):
        skor = _skor_al(soru, i)
        if skor is None:
            # Kullanıcı atladı
            console.print("  [dim]Anket atlandı.[/dim]")
            return None
        skorlar.append(skor)

    if not skorlar:
        return None

    ortalama = sum(skorlar) / len(skorlar)

    # Skora göre renk ve mesaj
    if ortalama >= 4.0:
        renk = "green"
        etiket = "Harika 💪"
    elif ortalama >= 2.5:
        renk = "yellow"
        etiket = "Orta seviye 🤔"
    else:
        renk = "red"
        etiket = "Risk var ⚠️"

    console.print(
        f"\n  Anlama skoru: [bold {renk}]{ortalama:.1f}/5[/bold {renk}] — {etiket}\n"
    )

    return ortalama
