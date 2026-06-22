"""
Basit in-memory rate limiter — brute-force koruması için.

Production-grade değil (çok process ortamında çalışmaz, sunucu yeniden
başlatıldığında sıfırlanır). Temel bir koruma katmanı sağlar.
Production için Redis tabanlı bir çözüm tercih edilmeli.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Optional


# Yapılandırma
_MAX_DENEME = 5        # Bu süre içinde maksimum başarısız deneme
_PENCERE_SANIYE = 300  # 5 dakikalık pencere
_KILIT_SANIYE = 60     # Kilitlenme süresi (saniye)


class RateLimiter:
    """Thread-safe in-memory rate limiter."""

    def __init__(
        self,
        max_deneme: int = _MAX_DENEME,
        pencere: int = _PENCERE_SANIYE,
        kilit: int = _KILIT_SANIYE,
    ) -> None:
        self._max_deneme = max_deneme
        self._pencere = pencere
        self._kilit = kilit
        # {anahtar: [(timestamp, basarisiz_mi), ...]}
        self._kayitlar: dict[str, list[tuple[int, bool]]] = defaultdict(list)
        self._kilitler: dict[str, int] = {}  # {anahtar: kilit_bitis_zamani}
        self._lock = Lock()

    def kontrol_et(self, anahtar: str) -> tuple[bool, Optional[int]]:
        """
        İsteğe izin verip vermeyeceğini kontrol et.

        Args:
            anahtar: IP adresi veya e-posta gibi tanımlayıcı

        Returns:
            (izin_var, kalan_saniye) — kilitliyse kalan_saniye > 0
        """
        su_an = int(time.time())
        with self._lock:
            # Kilit kontrolü
            kilit_bitis = self._kilitler.get(anahtar, 0)
            if su_an < kilit_bitis:
                return False, kilit_bitis - su_an

            # Eski kayıtları temizle
            pencere_basi = su_an - self._pencere
            self._kayitlar[anahtar] = [
                (ts, basarisiz)
                for ts, basarisiz in self._kayitlar[anahtar]
                if ts > pencere_basi
            ]
            return True, None

    def basarisiz_kaydet(self, anahtar: str) -> None:
        """Başarısız denemeyi kaydet, gerekirse kilitle."""
        su_an = int(time.time())
        with self._lock:
            self._kayitlar[anahtar].append((su_an, True))
            basarisiz = sum(1 for _, b in self._kayitlar[anahtar] if b)
            if basarisiz >= self._max_deneme:
                self._kilitler[anahtar] = su_an + self._kilit

    def basarili_kaydet(self, anahtar: str) -> None:
        """Başarılı girişte kaydı sıfırla."""
        with self._lock:
            self._kayitlar[anahtar] = []
            self._kilitler.pop(anahtar, None)


# Global limiter instance — login endpoint'i için
login_limiter = RateLimiter()
