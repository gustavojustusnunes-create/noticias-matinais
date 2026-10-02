import { NextResponse } from "next/server";
import { getAgentNodesData, getAnalyticsData, getTodayCurationNews } from "@/lib/adminData";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const nodes = getAgentNodesData();
    const analytics = getAnalyticsData();
    const curation = getTodayCurationNews();

    return NextResponse.json({
      success: true,
      timestamp: new Date().toISOString(),
      nodes,
      analytics,
      curation
    });
  } catch (error: any) {
    console.error("[api/admin/status] Erro:", error);
    return NextResponse.json(
      { success: false, error: error?.message || "Erro ao obter telemetria." },
      { status: 500 }
    );
  }
}
