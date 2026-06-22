/**
 * Next.js API Route — /api/billing/checkout
 * Cookie'deki token'ı alıp FastAPI'ye checkout isteği proxy'ler.
 */

import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const cookieStore = cookies();
  const token = cookieStore.get("codedna_token")?.value;

  if (!token) {
    return NextResponse.json({ detail: "Giriş yapınız." }, { status: 401 });
  }

  const govde = await req.json().catch(() => null);
  if (!govde?.plan) {
    return NextResponse.json({ detail: "Plan zorunlu." }, { status: 422 });
  }

  try {
    const fastapiYanit = await fetch(`${API_URL}/billing/checkout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ plan: govde.plan }),
    });

    const veri = await fastapiYanit.json();

    if (!fastapiYanit.ok) {
      return NextResponse.json(
        { detail: veri.detail || "Checkout URL alınamadı." },
        { status: fastapiYanit.status }
      );
    }

    return NextResponse.json(veri);
  } catch {
    return NextResponse.json({ detail: "API'ye bağlanılamadı." }, { status: 503 });
  }
}
