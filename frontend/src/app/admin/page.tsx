"use client";

import React, { useState, useEffect } from "react";
import {
  Activity,
  BarChart3,
  CheckCircle2,
  Lock,
  Radio,
  RefreshCw,
  Sparkles,
  Zap,
  Layers,
  Sliders,
  AlertCircle,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { AuthModal } from "@/components/admin/AuthModal";
import { AgentGraphTab } from "@/components/admin/AgentGraphTab";
import { AnalyticsTab } from "@/components/admin/AnalyticsTab";
import { CurationTab } from "@/components/admin/CurationTab";
import { FlashNewsTab } from "@/components/admin/FlashNewsTab";
import { AgentNodeDetail, CategoryPerformance, TopPost, CuratedNews } from "@/lib/adminData";

type AdminTab = "metrics" | "graph" | "curation" | "flash";

interface AdminStatusPayload {
  nodes: Record<string, AgentNodeDetail>;
  analytics: {
    kpis: {
      edr: number;
      baseTotal: number;
      baseAtiva: number;
      taxaAberturaPct: number;
      taxaCliquesPct: number;
      alcanceSocialSemanal: number;
      taxaConversaoVitrinePct: number;
    };
    funilHistorico: Array<{
      data: string;
      novos: number;
      total: number;
      aberturaPct: number;
      ctrPct: number;
    }>;
    performanceCadernos: CategoryPerformance[];
    topPosts: TopPost[];
  };
  curation: {
    publicacaoAutomaticaAtiva: boolean;
    horarioBatchBRT: string;
    items: CuratedNews[];
  };
}

export default function AdminMissionControlPage() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<AdminTab>("metrics");
  const [data, setData] = useState<AdminStatusPayload | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [toast, setToast] = useState<{ msg: string; type: "success" | "warning" | "error" } | null>(null);

  const showToast = (msg: string, type: "success" | "warning" | "error" = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  const fetchStatus = async (showNotification = false) => {
    try {
      const pin = localStorage.getItem("anj_admin_pin") || "2026";
      const res = await fetch(`/api/admin/status?token=${encodeURIComponent(pin)}`, {
        headers: {
          "Authorization": `Bearer ${pin}`,
          "x-admin-key": pin,
        },
      });

      if (res.ok) {
        const json = await res.json();
        if (json.success) {
          setData(json);
          setIsAuthenticated(true);
          if (showNotification) showToast("Telemetria e dados atualizados com sucesso!", "success");
        }
      } else if (res.status === 401) {
        setIsAuthenticated(false);
      }
    } catch (e) {
      console.error("Erro ao carregar telemetria:", e);
    } finally {
      setLoading(false);
    }
  };

  // Inicialização e Polling a cada 20 segundos
  useEffect(() => {
    const savedPin = localStorage.getItem("anj_admin_pin");
    if (savedPin) {
      setIsAuthenticated(true);
    }
    fetchStatus();

    const interval = setInterval(() => {
      fetchStatus();
    }, 20000);

    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("anj_admin_pin");
    setIsAuthenticated(false);
    showToast("Cockpit bloqueado com segurança.", "warning");
  };

  if (!isAuthenticated) {
    return <AuthModal onSuccess={() => fetchStatus(true)} />;
  }

  return (
    <main className="min-h-screen bg-[#070A0F] text-slate-100 font-sans pb-16 selection:bg-amber-500 selection:text-slate-950">
      
      {/* Toast Notification */}
      {toast && (
        <div
          className={`fixed top-5 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-2xl border text-xs font-semibold shadow-2xl flex items-center gap-2 animate-in fade-in slide-in-from-top-4 ${
            toast.type === "error"
              ? "bg-rose-950/95 border-rose-500/40 text-rose-200"
              : toast.type === "warning"
              ? "bg-amber-950/95 border-amber-500/40 text-amber-200"
              : "bg-[#0F172A]/95 border-emerald-500/40 text-emerald-300"
          }`}
        >
          {toast.type === "error" ? (
            <AlertCircle className="w-4 h-4 text-rose-400" />
          ) : toast.type === "warning" ? (
            <AlertCircle className="w-4 h-4 text-amber-400" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          )}
          <span>{toast.msg}</span>
        </div>
      )}

      {/* Header Fixo Executivo */}
      <header className="sticky top-0 z-40 bg-[#070A0F]/90 backdrop-blur-xl border-b border-white/10 px-4 sm:px-8 py-3.5">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          
          {/* Logo & Status */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 font-serif font-bold text-base shadow-lg shadow-amber-500/10">
              AN
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm sm:text-base font-bold text-white tracking-tight font-serif">
                  ALL NEWS JOURNAL
                </h1>
                <span className="hidden sm:inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  MISSION CONTROL
                </span>
              </div>
              <p className="text-[10px] text-slate-400 hidden sm:block">
                Cockpit Executivo & Governança Agêntica Multimodal
              </p>
            </div>
          </div>

          {/* Quick Controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchStatus(true)}
              title="Recarregar Telemetria"
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white border border-white/5 transition-all cursor-pointer"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={handleLogout}
              title="Bloquear Painel"
              className="p-2 rounded-xl bg-white/5 hover:bg-rose-500/20 text-slate-300 hover:text-rose-300 border border-white/5 hover:border-rose-500/30 transition-all cursor-pointer"
            >
              <Lock className="w-4 h-4" />
            </button>
          </div>

        </div>

        {/* Tab Navigation Bar (4 Abas Claras) */}
        <div className="max-w-7xl mx-auto mt-3 border-t border-white/5 pt-2">
          <nav className="flex space-x-1 sm:space-x-2 overflow-x-auto scrollbar-none py-1">
            
            <button
              onClick={() => setActiveTab("metrics")}
              className={`px-3.5 sm:px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer shrink-0 ${
                activeTab === "metrics"
                  ? "bg-amber-500/15 text-amber-300 border border-amber-500/30 shadow-lg shadow-amber-500/10"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <BarChart3 className="w-4 h-4 text-amber-400" />
              <span>Visão Geral & Métricas</span>
            </button>

            <button
              onClick={() => setActiveTab("graph")}
              className={`px-3.5 sm:px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer shrink-0 ${
                activeTab === "graph"
                  ? "bg-sky-500/15 text-sky-300 border border-sky-500/30 shadow-lg shadow-sky-500/10"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <Layers className="w-4 h-4 text-sky-400" />
              <span>Grafo de Agentes</span>
            </button>

            <button
              onClick={() => setActiveTab("curation")}
              className={`px-3.5 sm:px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer shrink-0 ${
                activeTab === "curation"
                  ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 shadow-lg shadow-emerald-500/10"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <Sliders className="w-4 h-4 text-emerald-400" />
              <span>Curadoria de Conteúdo</span>
            </button>

            <button
              onClick={() => setActiveTab("flash")}
              className={`px-3.5 sm:px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer shrink-0 ${
                activeTab === "flash"
                  ? "bg-pink-500/15 text-pink-300 border border-pink-500/30 shadow-lg shadow-pink-500/10"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <Zap className="w-4 h-4 text-pink-400" />
              <span>Flash News (Disparo)</span>
            </button>

          </nav>
        </div>
      </header>

      {/* Conteúdo Principal com base na Aba Ativa */}
      <div className="max-w-7xl mx-auto px-4 sm:px-8 pt-6">
        {loading && !data ? (
          <div className="flex flex-col items-center justify-center py-24 space-y-3">
            <RefreshCw className="w-8 h-8 text-amber-400 animate-spin" />
            <span className="text-xs font-mono text-slate-400">Sincronizando Mission Control com o cluster...</span>
          </div>
        ) : data ? (
          <>
            {activeTab === "metrics" && <AnalyticsTab analytics={data.analytics} />}
            {activeTab === "graph" && <AgentGraphTab nodesData={data.nodes} />}
            {activeTab === "curation" && (
              <CurationTab curationData={data.curation} onToast={showToast} />
            )}
            {activeTab === "flash" && <FlashNewsTab onToast={showToast} />}
          </>
        ) : (
          <div className="text-center py-20 text-rose-400 text-xs">
            Falha ao carregar dados do cluster. Verifique a rota /api/admin/status.
          </div>
        )}
      </div>

    </main>
  );
}
