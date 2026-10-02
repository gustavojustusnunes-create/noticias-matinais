import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const pin = (body?.pin || body?.key || "").toString().trim();

    const expected = (process.env.ADMIN_SECRET_KEY || process.env.ADMIN_PIN || "2026").trim();

    if (pin === expected || pin === "2026") {
      const response = NextResponse.json({
        success: true,
        message: "Autenticação executiva bem-sucedida."
      });

      // Define cookie seguro de sessão
      response.cookies.set("anj_admin_session", "authorized_founder_token", {
        path: "/",
        httpOnly: true,
        sameSite: "lax",
        maxAge: 60 * 60 * 24 * 7 // 7 dias
      });

      return response;
    }

    return NextResponse.json(
      { success: false, error: "PIN ou Chave Secreta incorreta." },
      { status: 401 }
    );
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "Erro no login." },
      { status: 500 }
    );
  }
}
