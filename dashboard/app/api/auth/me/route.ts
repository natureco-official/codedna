/**
 * Next.js API Route — /api/auth/me
 * Proxies user info from FastAPI using the cookie token.
 */

import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(_req: NextRequest) {
  const cookieStore = cookies();
  const token = cookieStore.get("codedna_token")?.value;

  if (!token) {
    return NextResponse.json({ detail: "Not logged in." }, { status: 401 });
  }

  try {
    const response = await fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      return NextResponse.json({ detail: "Invalid session." }, { status: 401 });
    }

    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ detail: "Cannot connect to API." }, { status: 503 });
  }
}
