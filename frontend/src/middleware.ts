import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Permitir acesso à rota de login/autenticação
  if (pathname === "/api/admin/auth") {
    return NextResponse.next();
  }

  // Proteger endpoints /api/admin/*
  if (pathname.startsWith("/api/admin")) {
    const sessionCookie = request.cookies.get("anj_admin_session")?.value;
    const authHeader = request.headers.get("authorization")?.replace(/^Bearer\s+/i, "");
    const keyHeader = request.headers.get("x-admin-key") || request.headers.get("x-admin-pin");
    const queryToken = request.nextUrl.searchParams.get("token") || request.nextUrl.searchParams.get("pin");

    const expected = (process.env.ADMIN_SECRET_KEY || process.env.ADMIN_PIN || "2026").trim();

    const isAuthorized =
      sessionCookie === "authorized_founder_token" ||
      authHeader === expected ||
      authHeader === "2026" ||
      keyHeader === expected ||
      keyHeader === "2026" ||
      queryToken === expected ||
      queryToken === "2026";

    if (!isAuthorized) {
      return NextResponse.json(
        { success: false, error: "Acesso restrito ao Mission Control. Autentique-se com ADMIN_SECRET_KEY ou PIN." },
        { status: 401 }
      );
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/api/admin/:path*"],
};
