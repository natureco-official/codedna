/**
 * Next.js API Route — Register
 * FastAPI'ye kayıt isteği atar, başarılıysa httpOnly cookie set eder.
 */

import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const govde = await req.json().catch(() => null);
  if (!govde?.email || !govde?.password) {
    return NextResponse.json({ detail: "E-posta ve şifre zorunlu." }, { status: 422 });
  }

  let fastapiYanit: Response;
  try {
    fastapiYanit = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: govde.email, password: govde.password }),
    });
  } catch {
    return NextResponse.json({ detail: "API'ye bağlanılamadı." }, { status: 503 });
  }

  const veri = await fastapiYanit.json();

  if (!fastapiYanit.ok) {
    return NextResponse.json({ detail: veri.detail || "Hata." }, { status: fastapiYanit.status });
  }

  const yanit = NextResponse.json({
    user_id: veri.user_id,
    plan: veri.plan,
    email: govde.email,
  });

  yanit.cookies.set("codedna_token", veri.token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 7 * 24 * 3600,
    path: "/",
  });

  return yanit;
}
