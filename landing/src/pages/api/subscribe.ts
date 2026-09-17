export const prerender = false;

export async function POST({ request }: { request: Request }) {
  try {
    const body = await request.json();
    const email = body?.email?.trim();

    if (!email || !email.includes("@")) {
      return new Response(
        JSON.stringify({ success: false, error: "E-mail inválido." }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    // 1. Tenta encaminhar para Webhook do Google Apps Script ou API Resend se variável existir
    const webhookUrl = process.env.GOOGLE_SHEETS_WEBHOOK_URL || process.env.WEBHOOK_SUBSCRIBE_URL;
    const resendApiKey = process.env.RESEND_API_KEY;

    if (webhookUrl) {
      try {
        await fetch(webhookUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email,
            origem: "landing_page_astro",
            data: new Date().toISOString()
          })
        });
      } catch (e) {
        console.warn("⚠️ Falha no webhook externo:", e);
      }
    }

    if (resendApiKey) {
      try {
        await fetch("https://api.resend.com/emails", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${resendApiKey}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            from: "All News Journal <onboarding@resend.dev>",
            to: email,
            subject: "Bem-vindo ao All News Journal",
            html: `<p>Olá!</p><p>Sua inscrição no <strong>All News Journal</strong> foi confirmada. A partir de amanhã, você receberá nossa edição executiva pontualmente às 06:15 com os resumos e o podcast matinal.</p>`
          })
        });
      } catch (e) {
        console.warn("⚠️ Falha ao disparar boas-vindas Resend:", e);
      }
    }

    return new Response(
      JSON.stringify({
        success: true,
        message: "Inscrição confirmada com sucesso!"
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  } catch (error) {
    return new Response(
      JSON.stringify({ success: false, error: "Erro interno no servidor." }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}
