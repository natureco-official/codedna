/**
 * CodeDNA Auth client helpers.
 *
 * Security note:
 *   Storing JWT tokens in localStorage is vulnerable to XSS attacks.
 *   This implementation uses httpOnly cookies:
 *   - Stores the token where client-side JS cannot access it
 *   - Cookie set/delete operations go through Next.js API routes
 *   - The client side only knows whether the user is logged in
 */

export interface UserData {
  user_id: number;
  email: string;
  plan: string;
  subscription_status: string;
}

/** Log in — via Next.js API route (sets httpOnly cookie) */
export async function login(
  email: string,
  password: string
): Promise<{ success: boolean; error?: string; user?: UserData }> {
  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      credentials: "include",
    });

    const data = await res.json();

    if (!res.ok) {
      return { success: false, error: data.detail || "Login failed." };
    }

    return { success: true, user: data };
  } catch {
    return { success: false, error: "Could not connect to API." };
  }
}

/** Register — via Next.js API route */
export async function register(
  email: string,
  password: string
): Promise<{ success: boolean; error?: string; user?: UserData }> {
  try {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      credentials: "include",
    });

    const data = await res.json();

    if (!res.ok) {
      return { success: false, error: data.detail || "Registration failed." };
    }

    return { success: true, user: data };
  } catch {
    return { success: false, error: "Could not connect to API." };
  }
}

/** Log out — clear cookie */
export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", {
    method: "POST",
    credentials: "include",
  });
}

/** Fetch current user info (via cookie) */
export async function getCurrentUser(): Promise<UserData | null> {
  try {
    const res = await fetch("/api/auth/me", {
      credentials: "include",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}


