import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

function resolveLogPath(rel: string): string {
  const p1 = path.resolve(process.cwd(), rel);
  if (fs.existsSync(p1)) return p1;
  const p2 = path.resolve(process.cwd(), "..", rel);
  if (fs.existsSync(p2)) return p2;
  return p1;
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { tema, contexto, caderno, tom, destinos } = body;

    if (!tema || !contexto) {
      return NextResponse.json(
        { success: false, error: "Tema e contexto são obrigatórios para o disparo extraordinário." },
        { status: 400 }
      );
    }

    const trackingId = `flash-${Date.now()}`;
    const payload = {
      trackingId,
      criadoEm: new Date().toISOString(),
      tema: tema.trim(),
      contexto: contexto.trim(),
      caderno: caderno || "Geral",
      tom: tom || "Analítico e Sóbrio",
      destinos: destinos || { instagram: true, story: true, push: false },
      status: "QUEUED_FOR_EXECUTION",
    };

    // 1. Persistir na fila ondemand local
    try {
      const queuePath = resolveLogPath("logs/ondemand_queue.json");
      const dir = path.dirname(queuePath);
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

      let currentQueue: any[] = [];
      if (fs.existsSync(queuePath)) {
        currentQueue = JSON.parse(fs.readFileSync(queuePath, "utf-8"));
      }
      currentQueue.push(payload);
      fs.writeFileSync(queuePath, JSON.stringify(currentQueue, null, 2), "utf-8");
    } catch (fsErr) {
      console.warn("[flash-news] Aviso ao gravar fila ondemand:", fsErr);
    }

    // 2. Disparar GitHub Actions se token estiver configurado
    const ghToken = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
    const repo = process.env.GITHUB_REPOSITORY || "gustavojustusnunes-create/noticias-matinais";
    let githubDispatched = false;

    if (ghToken) {
      try {
        const ghRes = await fetch(
          `https://api.github.com/repos/${repo}/dispatches`,
          {
            method: "POST",
            headers: {
              "Accept": "application/vnd.github.v3+json",
              "Authorization": `Bearer ${ghToken}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              event_type: "flash_news_dispatch",
              client_payload: payload,
            }),
          }
        );

        if (ghRes.ok || ghRes.status === 204) {
          githubDispatched = true;
        } else {
          console.warn("[flash-news] Resposta do GitHub Actions:", ghRes.status, await ghRes.text());
        }
      } catch (ghErr) {
        console.warn("[flash-news] Falha ao acionar GitHub Actions:", ghErr);
      }
    }

    return NextResponse.json({
      success: true,
      trackingId,
      githubDispatched,
      message: githubDispatched
        ? "🚀 Flash News enviada com sucesso! GitHub Actions acionada para síntese Gemini Flash e distribuição."
        : "✅ Flash News enfileirada com sucesso na esteira local de processamento.",
      payload,
    });
  } catch (error: any) {
    console.error("[api/admin/flash-news] Erro:", error);
    return NextResponse.json(
      { success: false, error: error?.message || "Erro ao despachar Flash News." },
      { status: 500 }
    );
  }
}
