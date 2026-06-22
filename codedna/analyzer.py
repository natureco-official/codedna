"""AST analizi ve AI imza tespiti modülü."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser, Node

# TypeScript parser — kurulu değilse JS parser'a geri dön
try:
    import tree_sitter_typescript as tstypescript
    _TS_LANG = tstypescript.language_typescript()
    _TSX_LANG = tstypescript.language_tsx()
    _TS_AVAILABLE = True
except Exception:
    _TS_LANG = tsjavascript.language()
    _TSX_LANG = tsjavascript.language()
    _TS_AVAILABLE = False

# Desteklenen dil eşlemesi
LANGUAGE_MAP: dict[str, tuple] = {
    ".py":  ("python",     tspython.language()),
    ".js":  ("javascript", tsjavascript.language()),
    ".jsx": ("javascript", tsjavascript.language()),
    ".ts":  ("typescript", _TS_LANG),
    ".tsx": ("tsx",        _TSX_LANG),
}


@dataclass
class FileAnalysisResult:
    """Tek bir dosyanın analiz sonucu."""

    file_path: str
    ai_probability: float = 0.0
    complexity_score: float = 0.0
    comment_ratio: float = 0.0
    avg_function_length: float = 0.0
    single_commit_ratio: float = 0.0
    total_lines: int = 0
    function_count: int = 0
    desteklenmiyor: bool = False
    hata: Optional[str] = None

    @property
    def complexity_label(self) -> str:
        """Karmaşıklık seviyesini metin olarak döndür."""
        if self.complexity_score < 5:
            return "Düşük"
        elif self.complexity_score < 15:
            return "Orta"
        else:
            return "Yüksek"

    @property
    def ai_color(self) -> str:
        """AI olasılığına göre renk emojisi döndür."""
        if self.ai_probability >= 0.7:
            return "🔴"
        elif self.ai_probability >= 0.4:
            return "🟡"
        else:
            return "🟢"


def _build_parser(ext: str) -> Optional[Parser]:
    """Dosya uzantısına göre tree-sitter parser oluştur."""
    if ext not in LANGUAGE_MAP:
        return None
    _, lang_obj = LANGUAGE_MAP[ext]
    language = Language(lang_obj)
    parser = Parser(language)
    return parser


def _count_lines(source: str) -> tuple[int, int]:
    """Toplam satır ve yorum satırı sayısını döndür (toplam, yorum)."""
    lines = source.splitlines()
    toplam = len(lines)
    yorum = 0
    for line in lines:
        stripped = line.strip()
        # Python, JS, TS tek satır yorumları
        if stripped.startswith("#") or stripped.startswith("//"):
            yorum += 1
        # Çok satırlı yorum içinde olup olmadığını basit regex ile yakala
        elif stripped.startswith("*") or stripped.startswith("/*") or stripped.startswith('"""') or stripped.startswith("'''"):
            yorum += 1
    return toplam, yorum


def _collect_functions(node: Node, functions: list[Node]) -> None:
    """Ağaç içindeki tüm fonksiyon düğümlerini özyinelemeli topla."""
    fonksiyon_tipleri = {
        "function_definition",      # Python
        "function_declaration",     # JS/TS
        "method_definition",        # JS/TS class method
        "method_signature",         # TS interface method
        "abstract_method_signature",# TS abstract
        "arrow_function",           # JS/TS arrow
        "function_expression",      # JS/TS
        "generator_function",       # JS/TS generator
        "generator_function_declaration",
    }
    if node.type in fonksiyon_tipleri:
        functions.append(node)
    for child in node.children:
        _collect_functions(child, functions)


def _calculate_cyclomatic_complexity(node: Node) -> float:
    """
    Basit cyclomatic complexity hesapla.
    Karar noktalarını (if, for, while, case, &&, ||) say.
    """
    karar_tipleri = {
        "if_statement", "elif_clause", "for_statement", "while_statement",
        "with_statement", "try_statement", "except_clause",
        "if_expression",  # Python ternary
        "switch_case", "case_clause",
        # JS/TS
        "if", "for", "while", "switch", "catch",
        "ternary_expression",
        "&&", "||", "??",
    }
    sayac = 1  # Temel yol

    def _gez(n: Node) -> None:
        nonlocal sayac
        if n.type in karar_tipleri:
            sayac += 1
        # Mantıksal operatörler
        if n.type in {"boolean_operator", "logical_expression"}:
            sayac += 1
        for child in n.children:
            _gez(child)

    _gez(node)
    return float(sayac)


def analyze_file(
    file_path: Path,
    single_commit_ratio: float = 0.0,
) -> FileAnalysisResult:
    """
    Dosyayı AST ile analiz et ve AI imza metriklerini hesapla.

    Args:
        file_path: Analiz edilecek dosyanın yolu
        single_commit_ratio: Tek commit'te gelen satır oranı (dışarıdan verilir)

    Returns:
        FileAnalysisResult nesnesi
    """
    sonuc = FileAnalysisResult(
        file_path=str(file_path),
        single_commit_ratio=single_commit_ratio,
    )

    # Dosya okunabilir mi?
    try:
        kaynak = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        sonuc.hata = f"Dosya okunamadı: {e}"
        return sonuc

    ext = file_path.suffix.lower()
    parser = _build_parser(ext)

    if parser is None:
        sonuc.desteklenmiyor = True
        return sonuc

    # Satır sayıları
    toplam_satir, yorum_satir = _count_lines(kaynak)
    sonuc.total_lines = toplam_satir
    sonuc.comment_ratio = (yorum_satir / toplam_satir) if toplam_satir > 0 else 0.0

    # AST parse
    try:
        tree = parser.parse(bytes(kaynak, "utf8"))
    except Exception as e:
        sonuc.hata = f"AST parse hatası: {e}"
        return sonuc

    # Fonksiyon analizi
    fonksiyonlar: list[Node] = []
    _collect_functions(tree.root_node, fonksiyonlar)
    sonuc.function_count = len(fonksiyonlar)

    if fonksiyonlar:
        uzunluklar = [
            f.end_point[0] - f.start_point[0] + 1
            for f in fonksiyonlar
        ]
        sonuc.avg_function_length = sum(uzunluklar) / len(uzunluklar)
    else:
        # Fonksiyon yoksa toplam satırı tek blok say
        sonuc.avg_function_length = float(toplam_satir)

    # Cyclomatic complexity (tüm dosya üzerinden)
    sonuc.complexity_score = _calculate_cyclomatic_complexity(tree.root_node)

    # AI olasılığı hesapla
    sonuc.ai_probability = _calculate_ai_probability(sonuc)

    return sonuc


def _calculate_ai_probability(sonuc: FileAnalysisResult) -> float:
    """
    Kural tabanlı AI olasılığı skoru hesapla (0.0 – 1.0).

    Kurallar:
      - comment_ratio > 0.3       → +0.20
      - avg_function_length > 50  → +0.15
      - single_commit_ratio > 0.7 → +0.30
      - complexity yüksek & tek commit → +0.25
    """
    skor = 0.0

    # Kural 1: Aşırı yorum oranı (AI kodu genelde çok yorum yazar)
    if sonuc.comment_ratio > 0.3:
        skor += 0.20

    # Kural 2: Uzun fonksiyonlar (AI genelde büyük bloklar üretir)
    if sonuc.avg_function_length > 50:
        skor += 0.15

    # Kural 3: Tek commit'te büyük değişiklik (toplu yapıştırma işareti)
    if sonuc.single_commit_ratio > 0.7:
        skor += 0.30

    # Kural 4: Yüksek karmaşıklık + tek seferlik commit
    if sonuc.complexity_score > 10 and sonuc.single_commit_ratio > 0.5:
        skor += 0.25

    # 0.0 – 1.0 arasına normalize et
    return min(skor, 1.0)
