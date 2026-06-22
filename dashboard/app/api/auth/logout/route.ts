/**
 * Next.js API Route — Logout
 * Cookie'yi siler ve FastAPI'ye logout isteği atar.
 */

import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(_req: NextRequest) {
  const cookieStore = cookies();
  const token = cookieStore.get("codedna_token")?.value;

  // FastAPI'ye logout isteği (sessiz — hata olsa da cookie sileriz)
  if (token) {
    try {
      await fetch(`${API_URL}/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // Sessiz hata — cookie her halükarda silinir
    }
  }

  const yanit = NextResponse.json({ mesaj: "Çıkış başarılı." });
  yanit.cookies.set("codedna_token", "", {
    httpOnly: true,
    maxAge: 0,
    path: "/",
  });

  return yanit;
}
