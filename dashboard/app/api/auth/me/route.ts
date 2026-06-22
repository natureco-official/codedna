/**
 * Next.js API Route — /api/auth/me
 * Cookie'deki token ile FastAPI'den kullanıcı bilgisini proxy'ler.
 */

import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(_req: NextRequest) {
  const cookieStore = cookies();
  const token = cookieStore.get("codedna_token")?.value;

  if (!token) {
    return NextResponse.json({ detail: "Giriş yapılmamış." }, { status: 401 });
  }

  try {
    const yanit = await fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!yanit.ok) {
      return NextResponse.json({ detail: "Geçersiz oturum." }, { status: 401 });
    }

    return NextResponse.json(await yanit.json());
  } catch {
    return NextResponse.json({ detail: "API'ye bağlanılamadı." }, { status: 503 });
  }
}
