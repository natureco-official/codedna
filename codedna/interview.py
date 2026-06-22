"""
Aday değerlendirme — kodbase anlama testi.

ÖNEMLİ UYARI:
  Bu araç insan değerlendirmesinin YERİNE GEÇMEZ. Tamamlayıcı bir sinyaldir.
  Tek başına işe alım kararı için kullanılmamalıdır.
  Otomatik puanlama bu fazda eklenmiyor — insan değerlendiricisi skorу manuel girer.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from codedna.db import get_connection

# Zorluk → karmaşıklık skoru eşikleri
_ZORLU_ESIKLER = {
    "easy":   (0.0, 5.0),   # düşük karmaşıklık
    "medium": (5.0, 15.0),  # orta karmaşıklık
    "hard":   (15.0, 999.),  # yüksek karmaşıklık
}

# Anonimleştirme: yaygın tanımlayıcı kalıpları jenerik isimlerle değiştir
_ANONIMLESTIME_KALIPLARI: list[tuple[str, str]] = [
    (r'\b(payment|charge|invoice|billing)\b', 'transaction'),
    (r'\b(user|account|customer|member)\b', 'entity'),
    (r'\b(password|secret|token|key|credential)\b', 'credential'),
    (r'\b(database|db|repository|repo|store)\b', 'storage'),
    (r'\b(email|phone|address|contact)\b', 'contact_info'),
]


@dataclass
class MulakatDosyasi:
    """Mülakat için seçilmiş dosya bilgisi."""

    dosya_yolu: str
    anonimlestirilmis_kod: str
    karmasiklik_skoru: float
    zorluk: str
    satir_sayisi: int


def _kod_anonimize_et(kod: str) -> str:
    """
    Kaynak kodu anonimleştir — iş mantığını açık eden tanımlayıcıları
    jenerik isimlerle değiştir. Kod yapısını ve mantığını korur.

    Args:
        kod: Ham kaynak kodu

    Returns:
        Anonimleştirilmiş kod
    """
    sonuc = kod
    for kalip, yeni in _ANONIMLESTIME_KALIPLARI:
        sonuc = re.sub(kalip, yeni, sonuc, flags=re.IGNORECASE)
    return sonuc


def select_candidate_file(
    repo_path: Path,
    db_path: Path,
    difficulty: str = "medium",
) -> Optional[MulakatDosyasi]:
    """
    Repo'dan mülakat için uygun bir dosya seç.

    Seçim kriterleri:
      - İstenen zorluk aralığındaki karmaşıklık skoru
      - Korumalı modüller HİÇBİR ZAMAN seçilmez
      - En az 20, en fazla 200 satır
      - Desteklenen uzantı (.py, .js, .ts)

    Args:
        repo_path: Git repo kök dizini
        db_path: SQLite veritabanı yolu
        difficulty: "easy" | "medium" | "hard"

    Returns:
        MulakatDosyasi nesnesi veya uygun dosya yoksa None
    """
    from codedna.scorer import scan_repository
    from codedna.protection import check_protected_modules

    alt_esik, ust_esik = _ZORLU_ESIKLER.get(difficulty, _ZORLU_ESIKLER["medium"])

    # Korumalı modülleri al — bunlar asla seçilmez
    korunanlari = {
        m.dosya_yolu
        for m in check_protected_modules(db_path)
    }

    taranan = scan_repository(repo_path, max_files=200)

    uygun = [
        s for s in taranan
        if alt_esik <= s.complexity_score < ust_esik
        and s.file_path not in korunanlari
        and 20 <= s.total_lines <= 200
    ]

    if not uygun:
        return None

    # En ortanca karmaşıklığa sahip dosyayı seç (çok kolay/zor olmasın)
    uygun.sort(key=lambda s: abs(s.complexity_score - (alt_esik + ust_esik) / 2))
    secilen = uygun[0]

    try:
        kod = Path(secilen.file_path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    anonimlestirilmis = _kod_anonimize_et(kod)

    return MulakatDosyasi(
        dosya_yolu=secilen.file_path,
        anonimlestirilmis_kod=anonimlestirilmis,
        karmasiklik_skoru=round(secilen.complexity_score, 1),
        zorluk=difficulty,
        satir_sayisi=secilen.total_lines,
    )


def generate_questions(code: str) -> list[str]:
    """
    Koddan otomatik 3 anlama sorusu üret.

    Şablon tabanlı üretim — AI çağrısı gerektirmez, kod yapısından çıkarım.
    Üretilen sorular her zaman genel, spesifik iş mantığına bağlı değil.

    Args:
        code: Kaynak kodu (anonimleştirilmiş olabilir)

    Returns:
        3 soruluk liste
    """
    satirlar = code.splitlines()
    fonksiyon_sayisi = sum(
        1 for s in satirlar
        if re.match(r'\s*(def |function |async function )', s)
    )
    kos_sayisi = sum(
        1 for s in satirlar
        if re.search(r'\b(if|else|elif|for|while|try|except|catch)\b', s)
    )
    donduruyor_mu = any("return " in s for s in satirlar)

    sorular = [
        "Bu kodu okuduğunuzda ana fonksiyonun/metodun birincil amacı ne?",
        f"Bu kod {fonksiyon_sayisi} fonksiyon/metod içeriyor. "
        f"Hangisi en kritik iş mantığını taşıyor ve neden?",
    ]

    if kos_sayisi > 3:
        sorular.append(
            f"Kodda {kos_sayisi} dal/koşul var. Hangi koşul en önemli hata senaryosunu ele alıyor?"
        )
    elif donduruyor_mu:
        sorular.append(
            "Bu fonksiyon hangi koşulda beklenmedik bir değer döndürebilir? "
            "Bu durumu nasıl debug ederdiniz?"
        )
    else:
        sorular.append(
            "Bu koda bir test yazmanız gerekse, önce hangi davranışı test ederdiniz?"
        )

    return sorular[:3]


def start_session(
    candidate_name: str,
    file_path: str,
    questions: list[str],
    db_path: Path,
    created_by: str = "system",
) -> int:
    """
    Yeni mülakat oturumu başlat.

    Args:
        candidate_name: Aday adı
        file_path: Test edilen dosyanın yolu
        questions: Sorulan soru listesi
        db_path: SQLite veritabanı yolu
        created_by: Oturumu başlatan kişi

    Returns:
        Yeni oturum id'si
    """
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO interview_sessions
                (candidate_name, file_path, started_at, questions_json, created_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                candidate_name,
                file_path,
                int(time.time()),
                json.dumps(questions, ensure_ascii=False),
                created_by,
            ),
        )
        return cur.lastrowid or 0


def submit_score(
    session_id: int,
    score: float,
    evaluator_notes: str,
    db_path: Path,
) -> dict:
    """
    İnsan değerlendiricinin verdiği puanı kaydet.

    Otomatik puanlama kasıtlı olarak yok — yanıltıcı olabileceğinden
    bu fazda insan değerlendirmesi zorunlu tutulmuştur.

    Args:
        session_id: Oturum id'si
        score: 0.0–5.0 arası puan
        evaluator_notes: Değerlendirici notları
        db_path: SQLite veritabanı yolu

    Returns:
        Güncellenen oturum özeti
    """
    if not (0.0 <= score <= 5.0):
        raise ValueError(f"Skor 0.0–5.0 arasında olmalı, gelen: {score}")

    su_an = int(time.time())
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            UPDATE interview_sessions
            SET comprehension_score = ?,
                evaluator_notes     = ?,
                completed_at        = ?
            WHERE id = ?
            """,
            (score, evaluator_notes, su_an, session_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Oturum #{session_id} bulunamadı.")

    return {
        "session_id": session_id,
        "comprehension_score": score,
        "evaluator_notes": evaluator_notes,
        "mesaj": "Değerlendirme kaydedildi.",
    }


def get_sessions(db_path: Path, limit: int = 20) -> list[dict]:
    """Geçmiş mülakat oturumlarını döndür."""
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, candidate_name, file_path, started_at, completed_at,
                       comprehension_score, evaluator_notes, created_by
                FROM interview_sessions
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    except Exception:
        return []

    def _ts(ts: Optional[int]) -> Optional[str]:
        if not ts:
            return None
        from datetime import datetime
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

    return [
        {
            "id": r["id"],
            "aday": r["candidate_name"],
            "dosya_yolu": r["file_path"],
            "baslangic": _ts(r["started_at"]),
            "bitis": _ts(r["completed_at"]),
            "skor": r["comprehension_score"],
            "notlar": r["evaluator_notes"],
            "olusturan": r["created_by"],
        }
        for r in rows
    ]
