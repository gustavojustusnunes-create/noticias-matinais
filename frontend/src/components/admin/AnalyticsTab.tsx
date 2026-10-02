"use client";

import React from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import {
  TrendingUp,
  Users,
  Mail,
  MousePointerClick,
  Share2,
  Bookmark,
  Sparkles,
  BarChart3,
  Award,
} from "lucide-react";
import { CategoryPerformance, TopPost } from "@/lib/adminData";

interface AnalyticsTabProps {
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
}

export function AnalyticsTab({ analytics }: AnalyticsTabProps) {
  const { kpis, funilHistorico, performanceCadernos, topPosts } = analytics;

  return (
    <div className="space-y-8">
      
      {/* 1. KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
        
        {/* Card 1: EDR North Star */}
        <div className="bg-gradient-to-br from-[#121926] to-[#152338] p-5 rounded-2xl border border-blue-500/30 shadow-xl space-y-2 relative overflow-hidden">
          <div className="flex items-center justify-between text-blue-400">
            <span className="text-[10px] font-mono uppercase tracking-widest font-bold">North Star Metric</span>
            <Sparkles className="w-4 h-4" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white font-mono">{kpis.edr}</span>
            <span className="text-xs text-slate-400 font-medium">/ 1.000 EDR</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-tight">
            Engaged Daily Readers: Base Ativa × Taxa de Abertura Única.
          </p>
        </div>

        {/* Card 2: Base de Assinantes */}
        <div className="bg-[#0D131C] p-5 rounded-2xl border border-white/10 shadow-xl space-y-2">
          <div className="flex items-center justify-between text-emerald-400">
            <span className="text-[10px] font-mono uppercase tracking-widest font-bold">Base Ativa</span>
            <Users className="w-4 h-4" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white font-mono">
              {kpis.baseAtiva.toLocaleString("pt-BR")}
            </span>
            <span className="text-xs text-emerald-400 font-semibold">+84 últimos 7d</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-tight">
            Assinantes com status entregue e verificado via Resend.
          </p>
        </div>

        {/* Card 3: Taxa de Abertura (Open Rate) */}
        <div className="bg-[#0D131C] p-5 rounded-2xl border border-white/10 shadow-xl space-y-2">
          <div className="flex items-center justify-between text-amber-400">
            <span className="text-[10px] font-mono uppercase tracking-widest font-bold">Taxa de Abertura</span>
            <Mail className="w-4 h-4" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white font-mono">{kpis.taxaAberturaPct}%</span>
            <span className="text-xs text-slate-400">Top 5% mercado</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-tight">
            Média dos últimos 30 disparos matinais pontuais.
          </p>
        </div>

        {/* Card 4: Cliques & Conversão */}
        <div className="bg-[#0D131C] p-5 rounded-2xl border border-white/10 shadow-xl space-y-2">
          <div className="flex items-center justify-between text-pink-400">
            <span className="text-[10px] font-mono uppercase tracking-widest font-bold">CTR & Vitrine</span>
            <MousePointerClick className="w-4 h-4" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white font-mono">{kpis.taxaCliquesPct}%</span>
            <span className="text-xs text-pink-400 font-semibold">Conv: {kpis.taxaConversaoVitrinePct}%</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-tight">
            Engajamento e captura na landing page institucional.
          </p>
        </div>

      </div>

      {/* 2. Funil de Audiência & Newsletter Chart */}
      <div className="bg-[#0D131C] p-6 rounded-3xl border border-white/10 shadow-2xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono uppercase text-amber-400 font-bold">
              <TrendingUp className="w-4 h-4" />
              Funil de Audiência & Newsletter
            </div>
            <h3 className="text-lg font-bold text-white font-serif tracking-tight mt-0.5">
              Crescimento de Novos Assinantes (Últimos 7 Dias)
            </h3>
          </div>
          <span className="text-xs font-mono text-slate-400 bg-white/5 px-3 py-1 rounded-full border border-white/5">
            Fonte: Google Sheets DB & Resend Webhooks
          </span>
        </div>

        <div className="w-full h-72 pt-4">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={funilHistorico} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorNovos" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#F59E0B" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="colorAbertura" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#38BDF8" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#38BDF8" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
              <XAxis dataKey="data" stroke="#64748B" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748B" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0F172A",
                  borderColor: "rgba(255,255,255,0.1)",
                  borderRadius: "12px",
                  fontSize: "12px",
                  color: "#F8FAFC",
                }}
              />
              <Area type="monotone" dataKey="novos" stroke="#F59E0B" strokeWidth={3} fillOpacity={1} fill="url(#colorNovos)" name="Novos Assinantes" />
              <Area type="monotone" dataKey="aberturaPct" stroke="#38BDF8" strokeWidth={2} fillOpacity={1} fill="url(#colorAbertura)" name="Taxa de Abertura (%)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 3. Matriz de Performance por Caderno (8 Temas) */}
      <div className="bg-[#0D131C] p-6 rounded-3xl border border-white/10 shadow-2xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono uppercase text-sky-400 font-bold">
              <BarChart3 className="w-4 h-4" />
              Social Performance & Retenção
            </div>
            <h3 className="text-lg font-bold text-white font-serif tracking-tight mt-0.5">
              Matriz de Performance por Caderno Editorial
            </h3>
          </div>
          <span className="text-xs text-slate-400">Comparativo de Engajamento e Compartilhamentos</span>
        </div>

        <div className="w-full h-80 pt-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={performanceCadernos} margin={{ top: 10, right: 10, left: -10, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
              <XAxis dataKey="caderno" stroke="#64748B" fontSize={10} interval={0} angle={-25} textAnchor="end" tickLine={false} />
              <YAxis stroke="#64748B" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0F172A",
                  borderColor: "rgba(255,255,255,0.1)",
                  borderRadius: "12px",
                  fontSize: "12px",
                  color: "#F8FAFC",
                }}
              />
              <Bar dataKey="engajamentoPct" fill="#3B82F6" radius={[6, 6, 0, 0]} name="Engajamento (%)" />
              <Bar dataKey="compartilhamentos" fill="#EC4899" radius={[6, 6, 0, 0]} name="Compartilhamentos" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 4. Top 5 Posts da Semana */}
      <div className="bg-[#0D131C] p-6 rounded-3xl border border-white/10 shadow-2xl space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono uppercase text-amber-400 font-bold">
              <Award className="w-4 h-4" />
              Top Stories da Semana
            </div>
            <h3 className="text-lg font-bold text-white font-serif tracking-tight mt-0.5">
              As 5 Matérias Mais Engajadas e Compartilhadas
            </h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">Instagram & X Analytics</span>
        </div>

        <div className="space-y-3">
          {topPosts.map((post, idx) => (
            <div
              key={post.id}
              className="bg-[#141C28] hover:bg-[#182333] transition-all p-4 rounded-2xl border border-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="flex items-start gap-3">
                <span className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 font-black text-sm flex items-center justify-center shrink-0">
                  #{idx + 1}
                </span>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-white/5 text-slate-300 border border-white/10">
                      {post.caderno}
                    </span>
                    <span className="text-[11px] text-slate-500">{post.data}</span>
                  </div>
                  <h4 className="text-xs sm:text-sm font-bold text-white leading-snug">
                    {post.titulo}
                  </h4>
                </div>
              </div>

              {/* Metrics Pill */}
              <div className="flex items-center gap-4 text-xs font-mono text-slate-300 shrink-0 self-end sm:self-center bg-[#0A0E14] px-4 py-2 rounded-xl border border-white/5">
                <div className="flex items-center gap-1.5" title="Alcance Total">
                  <Users className="w-3.5 h-3.5 text-blue-400" />
                  <span>{post.alcance.toLocaleString("pt-BR")}</span>
                </div>
                <div className="flex items-center gap-1.5" title="Cliques com UTM">
                  <MousePointerClick className="w-3.5 h-3.5 text-emerald-400" />
                  <span>{post.cliques}</span>
                </div>
                <div className="flex items-center gap-1.5" title="Salvamentos">
                  <Bookmark className="w-3.5 h-3.5 text-pink-400" />
                  <span>{post.salvamentos}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
