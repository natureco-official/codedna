"use client";

/**
 * Auth context — giriş durumunu ve kullanıcı bilgisini uygulama genelinde yönetir.
 */

import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { benimKimligim, cikisYap, KullaniciVeri } from "@/lib/auth";

interface AuthContextValue {
  kullanici: KullaniciVeri | null;
  yukleniyor: boolean;
  yenile: () => Promise<void>;
  cikis: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  kullanici: null,
  yukleniyor: true,
  yenile: async () => {},
  cikis: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [kullanici, setKullanici] = useState<KullaniciVeri | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);

  const yenile = useCallback(async () => {
    setYukleniyor(true);
    const veri = await benimKimligim();
    setKullanici(veri);
    setYukleniyor(false);
  }, []);

  const cikis = useCallback(async () => {
    await cikisYap();
    setKullanici(null);
  }, []);

  useEffect(() => {
    yenile();
  }, [yenile]);

  return (
    <AuthContext.Provider value={{ kullanici, yukleniyor, yenile, cikis }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
