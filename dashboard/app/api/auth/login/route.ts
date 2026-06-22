/**
 * Next.js API Route — Login
 * FastAPI'ye istek atar, dönen JWT'yi httpOnly cookie olarak set eder.
 * Client-side JS token'a asla erişemez.
 */

import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const govde = await req.json().catch(() => null);
  if (!govde?.email || !govde?.password) {
    return NextResponse.json({ detail: "E-posta ve şifre zorunlu." }, { status: 422 });
  }

  // FastAPI'ye ilet
  let fastapiYanit: Response;
  try {
    fastapiYanit = await fetch(`${API_URL}/auth/login`, {
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

  // Token'ı httpOnly cookie olarak set et — client JS göremez
  const yanit = NextResponse.json({
    user_id: veri.user_id,
    plan: veri.plan,
    subscription_status: veri.subscription_status,
    email: govde.email,
  });

  yanit.cookies.set("codedna_token", veri.token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 7 * 24 * 3600,  // 7 gün
    path: "/",
  });

  return yanit;
}
