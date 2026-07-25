/**
 * Next.js API Route — Logout
 * Deletes cookie and sends logout request to FastAPI.
 */

import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(_req: NextRequest) {
  const cookieStore = cookies();
  const token = cookieStore.get("codedna_token")?.value;

  // Send logout request to FastAPI (silent — we delete cookie even on error)
  if (token) {
    try {
      await fetch(`${API_URL}/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // Silent error — cookie is deleted regardless
    }
  }

  const response = NextResponse.json({ message: "Logout successful." });
  response.cookies.set("codedna_token", "", {
    httpOnly: true,
    maxAge: 0,
    path: "/",
  });

  return response;
}
