"""Kullanıcı kimlik doğrulama — kayıt, giriş, JWT oturum yönetimi."""

from __future__ import annotations

import hashlib
import os
import re
import time
from pathlib import Path
from typing import Optional

import bcrypt
import jwt

from codedna.db import get_connection

# ---------------------------------------------------------------------------
# Yapılandırma
# ---------------------------------------------------------------------------

# JWT secret MUTLAKA ortam değişkeninden okunmalı — koda gömülmemeli
JWT_SECRET: Optional[str] = os.environ.get("CODEDNA_JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 7   # 7 gün

# Auth veritabanı yolu — repo db'sinden ayrı
_AUTH_DB_VARSAYILAN = Path.home() / ".codedna" / "auth.db"


def _auth_db() -> Path:
    """Auth veritabanı yolunu döndür (ortam değişkeninden veya varsayılan)."""
    env = os.environ.get("CODEDNA_AUTH_DB_PATH")
    return Path(env).resolve() if env else _AUTH_DB_VARSAYILAN


def _jwt_secret_kontrol() -> str:
    """
    JWT secret'ın var olduğunu doğrula.
    Production'da secret olmadan uygulama başlamamalı.
    """
    secret = JWT_SECRET or os.environ.get("CODEDNA_JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "CODEDNA_JWT_SECRET ortam değişkeni tanımlanmamış. "
            "Production'da bu değer zorunludur. "
            "Geliştirme için: export CODEDNA_JWT_SECRET=guclu-rastgele-deger"
        )
    return secret


# ---------------------------------------------------------------------------
# Auth DB şeması
# ---------------------------------------------------------------------------

def init_auth_db(db_path: Optional[Path] = None) -> None:
    """Kullanıcı ve oturum tablolarını oluştur (yoksa)."""
    yol = db_path or _auth_db()
    yol.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(yol) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                plan TEXT DEFAULT 'free',
                lemonsqueezy_customer_id TEXT,
                lemonsqueezy_subscription_id TEXT,
                subscription_status TEXT DEFAULT 'none',
                created_at INTEGER,
                updated_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                created_at INTEGER,
                expires_at INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)


# ---------------------------------------------------------------------------
# Şifre işlemleri
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """bcrypt ile şifreyi hash'le."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Şifreyi hash ile güvenli biçimde karşılaştır."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Token yardımcıları
# ---------------------------------------------------------------------------

def _token_hash(token: str) -> str:
    """Token'ı SHA-256 ile hash'le — DB'de token'ın kendisi SAKLANMAZ."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _jwt_olustur(user_id: int, email: str, plan: str) -> str:
    """JWT token üret."""
    secret = _jwt_secret_kontrol()
    su_an = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": email,
        "plan": plan,
        "iat": su_an,
        "exp": su_an + JWT_EXPIRY_HOURS * 3600,
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def _jwt_coz(token: str) -> Optional[dict]:
    """JWT token'ı çöz, geçersizse None döndür."""
    secret = _jwt_secret_kontrol()
    try:
        return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ---------------------------------------------------------------------------
# Kayıt / Giriş / Çıkış
# ---------------------------------------------------------------------------

_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def register_user(
    email: str,
    password: str,
    db_path: Optional[Path] = None,
) -> dict:
    """
    Yeni kullanıcı kaydı yap.

    Kurallar:
      - E-posta formatı geçerli olmalı
      - Şifre en az 8 karakter
      - E-posta zaten kayıtlıysa hata

    Args:
        email: Kullanıcı e-postası
        password: Düz metin şifre (kayıt sonrası saklanmaz)
        db_path: Auth DB yolu

    Returns:
        {"user_id", "token", "plan"} sözlüğü
    """
    yol = db_path or _auth_db()
    init_auth_db(yol)

    # Girdi doğrulama
    email = email.strip().lower()
    if not _EMAIL_REGEX.match(email):
        raise ValueError("Geçersiz e-posta formatı.")
    if len(password) < 8:
        raise ValueError("Şifre en az 8 karakter olmalı.")

    sifre_hash = hash_password(password)
    su_an = int(time.time())

    try:
        with get_connection(yol) as conn:
            cur = conn.execute(
                """
                INSERT INTO users (email, password_hash, plan, subscription_status, created_at, updated_at)
                VALUES (?, ?, 'free', 'none', ?, ?)
                """,
                (email, sifre_hash, su_an, su_an),
            )
            user_id = cur.lastrowid or 0
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            raise ValueError("Bu e-posta adresi zaten kayıtlı.")
        raise

    token = _jwt_olustur(user_id, email, "free")
    _oturum_kaydet(user_id, token, yol)

    return {"user_id": user_id, "token": token, "plan": "free"}


def login_user(
    email: str,
    password: str,
    db_path: Optional[Path] = None,
) -> dict:
    """
    Giriş yap ve JWT token üret.

    Güvenlik notu: Başarısız girişlerde spesifik hata döndürme
    (kullanıcı enumeration saldırısını önlemek için genel mesaj kullan).

    Args:
        email: Kullanıcı e-postası
        password: Düz metin şifre

    Returns:
        {"user_id", "token", "plan", "subscription_status"} sözlüğü
    """
    yol = db_path or _auth_db()
    init_auth_db(yol)

    email = email.strip().lower()

    with get_connection(yol) as conn:
        kullanici = conn.execute(
            "SELECT id, password_hash, plan, subscription_status FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    # Kullanıcı yoksa veya şifre yanlışsa AYNI hata — enumeration önlemi
    if not kullanici or not verify_password(password, kullanici["password_hash"]):
        raise ValueError("E-posta veya şifre hatalı.")

    token = _jwt_olustur(kullanici["id"], email, kullanici["plan"])
    _oturum_kaydet(kullanici["id"], token, yol)

    return {
        "user_id": kullanici["id"],
        "token": token,
        "plan": kullanici["plan"],
        "subscription_status": kullanici["subscription_status"],
    }


def verify_token(
    token: str,
    db_path: Optional[Path] = None,
) -> Optional[dict]:
    """
    JWT token'ı doğrula ve kullanıcı bilgisini döndür.

    Hem JWT imzasını hem de oturum tablosundaki kaydı kontrol eder.

    Returns:
        Geçerliyse {"user_id", "email", "plan"}, değilse None
    """
    yol = db_path or _auth_db()
    payload = _jwt_coz(token)
    if not payload:
        return None

    token_h = _token_hash(token)
    su_an = int(time.time())

    with get_connection(yol) as conn:
        oturum = conn.execute(
            "SELECT id FROM sessions WHERE token_hash = ? AND expires_at > ?",
            (token_h, su_an),
        ).fetchone()

    if not oturum:
        return None

    return {
        "user_id": int(payload["sub"]),
        "email": payload["email"],
        "plan": payload["plan"],
    }


def logout_user(
    token: str,
    db_path: Optional[Path] = None,
) -> bool:
    """
    Oturumu sonlandır — sessions tablosundan sil.

    Returns:
        Başarıyla silinirse True
    """
    yol = db_path or _auth_db()
    token_h = _token_hash(token)
    with get_connection(yol) as conn:
        cur = conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_h,))
    return cur.rowcount > 0


def get_user_by_id(user_id: int, db_path: Optional[Path] = None) -> Optional[dict]:
    """Kullanıcı bilgisini ID ile getir (şifre hash hariç)."""
    yol = db_path or _auth_db()
    with get_connection(yol) as conn:
        row = conn.execute(
            "SELECT id, email, plan, subscription_status, lemonsqueezy_customer_id FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "plan": row["plan"],
        "subscription_status": row["subscription_status"],
        "lemonsqueezy_customer_id": row["lemonsqueezy_customer_id"],
    }


def update_user_plan(
    user_id: int,
    plan: str,
    subscription_status: str,
    customer_id: Optional[str] = None,
    subscription_id: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Kullanıcının plan ve abonelik durumunu güncelle."""
    yol = db_path or _auth_db()
    su_an = int(time.time())
    with get_connection(yol) as conn:
        conn.execute(
            """
            UPDATE users
            SET plan = ?, subscription_status = ?,
                lemonsqueezy_customer_id = COALESCE(?, lemonsqueezy_customer_id),
                lemonsqueezy_subscription_id = COALESCE(?, lemonsqueezy_subscription_id),
                updated_at = ?
            WHERE id = ?
            """,
            (plan, subscription_status, customer_id, subscription_id, su_an, user_id),
        )


# ---------------------------------------------------------------------------
# Yardımcı — oturum kaydetme
# ---------------------------------------------------------------------------

def _oturum_kaydet(user_id: int, token: str, db_path: Path) -> None:
    """Yeni oturumu DB'ye kaydet (token'ın hash'i saklanır)."""
    su_an = int(time.time())
    bitis = su_an + JWT_EXPIRY_HOURS * 3600
    token_h = _token_hash(token)
    with get_connection(db_path) as conn:
        # Eski süresi dolmuş oturumları temizle
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (su_an,))
        conn.execute(
            "INSERT OR IGNORE INTO sessions (user_id, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (user_id, token_h, su_an, bitis),
        )
