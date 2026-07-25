/**
 * Next.js API Route — Register
 * Sends registration request to FastAPI, sets httpOnly cookie on success.
 */

import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  if (!body?.email || !body?.password) {
    return NextResponse.json({ detail: "Email and password required." }, { status: 422 });
  }

  let fastapiResponse: Response;
  try {
    fastapiResponse = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: body.email, password: body.password }),
    });
  } catch {
    return NextResponse.json({ detail: "Cannot connect to API." }, { status: 503 });
  }

  const data = await fastapiResponse.json();

  if (!fastapiResponse.ok) {
    return NextResponse.json({ detail: data.detail || "Error." }, { status: fastapiResponse.status });
  }

  const response = NextResponse.json({
    user_id: data.user_id,
    plan: data.plan,
    email: body.email,
  });

  response.cookies.set("codedna_token", data.token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 7 * 24 * 3600,
    path: "/",
  });

  return response;
}
