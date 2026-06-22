/**
 * CodeDNA Auth istemci yardımcıları.
 *
 * Güvenlik notu:
 *   JWT token'ı localStorage'da saklamak XSS saldırılarına açıktır.
 *   Bu implementasyon httpOnly cookie kullanır:
 *   - Token'ı client-side JS'den erişilemez yerde saklar
 *   - Cookie set/delete işlemleri Next.js API route'ları üzerinden yapılır
 *   - Client tarafı yalnızca "giriş yapılmış mı" durumunu bilir
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface KullaniciVeri {
  user_id: number;
  email: string;
  plan: string;
  subscription_status: string;
}

export interface AbonelikVeri {
  plan: string;
  subscription_status: string;
  lemonsqueezy_customer_id: string | null;
}

/** Giriş yap — Next.js API route üzerinden (httpOnly cookie set eder) */
export async function girisYap(
  email: string,
  password: string
): Promise<{ basarili: boolean; hata?: string; kullanici?: KullaniciVeri }> {
  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      credentials: "include",
    });

    const veri = await res.json();

    if (!res.ok) {
      return { basarili: false, hata: veri.detail || "Giriş başarısız." };
    }

    return { basarili: true, kullanici: veri };
  } catch {
    return { basarili: false, hata: "API'ye bağlanılamadı." };
  }
}

/** Kayıt ol — Next.js API route üzerinden */
export async function kayitOl(
  email: string,
  password: string
): Promise<{ basarili: boolean; hata?: string; kullanici?: KullaniciVeri }> {
  try {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      credentials: "include",
    });

    const veri = await res.json();

    if (!res.ok) {
      return { basarili: false, hata: veri.detail || "Kayıt başarısız." };
    }

    return { basarili: true, kullanici: veri };
  } catch {
    return { basarili: false, hata: "API'ye bağlanılamadı." };
  }
}

/** Çıkış yap — cookie'yi temizle */
export async function cikisYap(): Promise<void> {
  await fetch("/api/auth/logout", {
    method: "POST",
    credentials: "include",
  });
}

/** Mevcut kullanıcı bilgisini getir (cookie ile) */
export async function benimKimligim(): Promise<KullaniciVeri | null> {
  try {
    const res = await fetch("/api/auth/me", {
      credentials: "include",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

/** Doğrudan FastAPI'ye checkout URL isteği at */
export async function checkoutUrlAl(
  plan: string,
  token: string
): Promise<string | null> {
  try {
    const res = await fetch(`${API_URL}/billing/checkout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ plan }),
    });
    if (!res.ok) return null;
    const veri = await res.json();
    return veri.checkout_url ?? null;
  } catch {
    return null;
  }
}

/** Abonelik durumunu getir */
export async function abonelikDurumu(token: string): Promise<AbonelikVeri | null> {
  try {
    const res = await fetch(`${API_URL}/billing/subscription`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
