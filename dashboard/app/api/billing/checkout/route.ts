/**
 * Next.js API Route — Billing Checkout
 * Forwards the JWT token from cookie to FastAPI.
 */

import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  if (!body?.plan) {
    return NextResponse.json({ detail: "Plan is required." }, { status: 422 });
  }

  // Get token from cookie
  const token = req.cookies.get("codedna_token")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Token required." }, { status: 401 });
  }

  // Forward to FastAPI
  try {
    const response = await fetch(`${API_URL}/billing/checkout`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ plan: body.plan }),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { detail: data.detail || "Unknown error" },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { detail: "Cannot connect to API." },
      { status: 503 }
    );
  }
}
