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
    const { acao, noticiaId, titulo, resumo, ativo } = body;

    const overridePath = resolveLogPath("logs/curation_overrides.json");
    const dir = path.dirname(overridePath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    let overrides: Record<string, any> = {};
    if (fs.existsSync(overridePath)) {
      try {
        overrides = JSON.parse(fs.readFileSync(overridePath, "utf-8"));
      } catch (e) {
        overrides = {};
      }
    }

    if (acao === "toggle_autopublish") {
      const ksPath = resolveLogPath("logs/kill_switch.json");
      const currentKs = fs.existsSync(ksPath) ? JSON.parse(fs.readFileSync(ksPath, "utf-8")) : {};
      const novoKillSwitch = !ativo; // se autopublish ativo, kill switch desligado
      
      fs.writeFileSync(ksPath, JSON.stringify({
        kill_switch_ativo: novoKillSwitch,
        atualizado_em: new Date().toISOString(),
        alterado_por: "Mission Control Next.js"
      }, null, 2), "utf-8");

      return NextResponse.json({
        success: true,
        publicacaoAutomaticaAtiva: Boolean(ativo),
        message: ativo
          ? "✅ Publicação automática ativada. O batch será disparado no horário programado."
          : "⏸️ Publicação automática pausada. Disparos retidos para revisão manual."
      });
    }

    if (acao === "aprovar_instagram") {
      overrides[noticiaId] = {
        ...(overrides[noticiaId] || {}),
        aprovadoInstagram: true,
        status: "Agendado",
        atualizadoEm: new Date().toISOString()
      };
      fs.writeFileSync(overridePath, JSON.stringify(overrides, null, 2), "utf-8");

      return NextResponse.json({
        success: true,
        noticiaId,
        message: "📸 Notícia aprovada com sucesso para o carrossel do Instagram!"
      });
    }

    if (acao === "descartar_noticia") {
      overrides[noticiaId] = {
        ...(overrides[noticiaId] || {}),
        descartada: true,
        status: "Descartada",
        atualizadoEm: new Date().toISOString()
      };
      fs.writeFileSync(overridePath, JSON.stringify(overrides, null, 2), "utf-8");

      return NextResponse.json({
        success: true,
        noticiaId,
        message: "🗑️ Notícia pulada/descartada do lote de hoje."
      });
    }

    if (acao === "editar_noticia") {
      if (!titulo || !resumo) {
        return NextResponse.json({ success: false, error: "Título e resumo são obrigatórios." }, { status: 400 });
      }

      const words = resumo.trim().split(/\s+/).length;
      overrides[noticiaId] = {
        ...(overrides[noticiaId] || {}),
        tituloEditado: titulo.trim(),
        resumoEditado: resumo.trim(),
        contagemPalavras: words,
        complianceJev: words >= 85 && words <= 105,
        editadoPeloEditor: true,
        atualizadoEm: new Date().toISOString()
      };
      fs.writeFileSync(overridePath, JSON.stringify(overrides, null, 2), "utf-8");

      return NextResponse.json({
        success: true,
        noticiaId,
        words,
        complianceJev: words >= 85 && words <= 105,
        message: `✍️ Texto atualizado com sucesso (${words} palavras).`
      });
    }

    return NextResponse.json({ success: false, error: `Ação inválida: ${acao}` }, { status: 400 });
  } catch (error: any) {
    console.error("[api/admin/editorial] Erro:", error);
    return NextResponse.json(
      { success: false, error: error?.message || "Erro ao processar ação editorial." },
      { status: 500 }
    );
  }
}
