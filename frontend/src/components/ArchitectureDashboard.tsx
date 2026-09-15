"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Lock, Unlock, ShieldCheck, Cpu, Activity, RefreshCw, CheckCircle2, AlertCircle } from "lucide-react";

export function ArchitectureDashboard() {
  const [password, setPassword] = useState("");
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [isShaking, setIsShaking] = useState(false);

  const handleUnlock = (e: React.FormEvent) => {
    e.preventDefault();
    if (password === "3344") {
      setIsUnlocked(true);
      setErrorMsg("");
    } else {
      setErrorMsg("Senha incorreta. Acesso negado.");
      setIsShaking(true);
      setTimeout(() => setIsShaking(false), 500);
    }
  };

  const agents = [
    {
      name: "Agente Supervisor & Watchdog",
      role: "Auto-recuperação & Telemetria em tempo real",
      status: "online",
      detail: "Monitora filas, memória e integridade das edições diárias",
      model: "Autonomous Self-Healing",
    },
    {
      name: "Agente Coletor Multi-Fontes",
      role: "Extração RSS & Web Scraping (G1, Olhar Digital, etc.)",
      status: "online",
      detail: "Filtragem semântica e deduplicação pré-seleção",
      model: "Deduplication Engine",
    },
    {
      name: "Agente Redator & Tradutor",
      role: "Síntese jornalística profunda e imparcial",
      status: "online",
      detail: "Geração de cadernos e manchete editorial matinal",
      model: "Claude 3.5 Sonnet / Gemini 2.0 Flash",
    },
    {
      name: "Agente de Imagens & Design",
      role: "Curadoria visual com texto integrado",
      status: "online",
      detail: "Resolução inteligente com fallback de alta definição",
      model: "Image Pipeline",
    },
    {
      name: "Agente Podcast Neurais (Leo & Ana)",
      role: "Roteirização e síntese vocal com edge-tts",
      status: "online",
      detail: "pt-BR-AntonioNeural (Leo) & pt-BR-FranciscaNeural (Ana)",
      model: "Neural Audio Concatenator",
    },
    {
      name: "Agente de Publicação & Distribuição",
      role: "Disparo no Instagram, Feed RSS e Portal Web",
      status: "scheduled",
      detail: "Disparo agendado diariamente às 06:00 BRT",
      model: "Scheduler 06:00 BRT",
    },
  ];

  return (
    <section id="arquitetura" className="py-12 border-t border-white/10 bg-[#08080a]">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-teal-400 uppercase tracking-widest mb-1">
              <Cpu className="w-4 h-4" />
              Engenharia de Sistemas
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight font-serif">
              Arquitetura de Agentes Autônomos
            </h2>
          </div>

          <div className="text-xs text-zinc-400">
            {isUnlocked ? (
              <span className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                <ShieldCheck className="w-4 h-4" /> Console Desbloqueado
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-amber-400">
                <Lock className="w-3.5 h-3.5" /> Protegido por Chave de Engenharia
              </span>
            )}
          </div>
        </div>

        {!isUnlocked ? (
          /* Password Protection Gate (User requirement: password 3344) */
          <div className="mx-auto max-w-md my-8">
            <motion.div
              animate={isShaking ? { x: [-10, 10, -10, 10, 0] } : {}}
              transition={{ duration: 0.4 }}
              className="originkit-card rounded-3xl p-8 border border-white/10 text-center space-y-6"
            >
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-500/10 border border-teal-500/20 text-teal-400">
                <Lock className="w-6 h-6" />
              </div>

              <div>
                <h3 className="text-lg font-bold text-white font-serif">
                  Acesso Restrito ao Grafo de Agentes
                </h3>
                <p className="mt-1 text-xs text-zinc-400">
                  Insira a senha de desenvolvedor para visualizar a telemetria ao vivo e o grafo do sistema.
                </p>
              </div>

              <form onSubmit={handleUnlock} className="space-y-4">
                <div>
                  <input
                    type="password"
                    placeholder="Digite a senha..."
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full rounded-xl border border-white/10 bg-black/60 px-4 py-2.5 text-center text-sm text-white placeholder-zinc-500 focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-400 font-mono tracking-widest"
                  />
                </div>

                {errorMsg && (
                  <p className="text-xs text-rose-400 flex items-center justify-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" /> {errorMsg}
                  </p>
                )}

                <button
                  type="submit"
                  className="w-full rounded-xl bg-teal-400 px-4 py-2.5 text-xs font-bold text-black hover:bg-teal-300 transition-colors shadow-lg shadow-teal-500/20"
                >
                  Desbloquear Painel
                </button>
              </form>
            </motion.div>
          </div>
        ) : (
          /* Unlocked Architecture & Agent Telemetry Dashboard */
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-8"
          >
            {/* Action Bar */}
            <div className="flex items-center justify-between bg-zinc-900/60 rounded-xl px-4 py-2.5 border border-white/5">
              <span className="text-xs text-zinc-300 flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
                Cluster de Agentes: <strong>100% Saudável</strong> (0 falhas críticas)
              </span>

              <button
                onClick={() => setIsUnlocked(false)}
                className="text-xs text-zinc-400 hover:text-white flex items-center gap-1"
              >
                <Lock className="w-3.5 h-3.5" /> Bloquear
              </button>
            </div>

            {/* Fleet Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {agents.map((agent, i) => (
                <div
                  key={i}
                  className="originkit-card rounded-2xl p-5 border border-white/10 space-y-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="text-sm font-bold text-white font-serif">
                      {agent.name}
                    </div>
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-400">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      {agent.status === "online" ? "ATIVO" : "AGENDADO"}
                    </span>
                  </div>

                  <div className="text-xs text-zinc-400">{agent.role}</div>

                  <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[11px] text-zinc-500">
                    <span>{agent.model}</span>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  </div>
                </div>
              ))}
            </div>

            {/* Architecture Pipeline Visual Diagram */}
            <div className="originkit-card rounded-3xl p-6 sm:p-8 border border-white/10 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold text-white font-serif">
                    Grafo do Fluxo de Dados & Agentes
                  </h3>
                  <p className="text-xs text-zinc-400">
                    Pipeline em tempo real desde a ingestão de fontes até a síntese e entrega
                  </p>
                </div>
                <span className="text-[11px] font-mono text-teal-400 bg-teal-500/10 px-2.5 py-1 rounded-md border border-teal-500/20">
                  v2.6 Pipeline
                </span>
              </div>

              {/* Custom SVG Architecture Graph */}
              <div className="overflow-x-auto py-6">
                <div className="min-w-[720px] mx-auto flex flex-col items-center gap-6">
                  {/* Stage 1: Sources */}
                  <div className="w-full grid grid-cols-4 gap-3">
                    {["Fontes RSS G1", "Olhar Digital IA", "Feeds Governamentais", "Portais de Cultura"].map(
                      (src, idx) => (
                        <div
                          key={idx}
                          className="bg-zinc-900/80 rounded-xl p-3 border border-white/10 text-center text-xs font-semibold text-zinc-300"
                        >
                          🌐 {src}
                        </div>
                      )
                    )}
                  </div>

                  {/* Flow Arrow */}
                  <div className="text-teal-400 text-xs font-mono">↓ Coleta Assíncrona & Sanitização ↓</div>

                  {/* Stage 2: Ingestion & Supervisor */}
                  <div className="w-full grid grid-cols-2 gap-4">
                    <div className="bg-gradient-to-r from-teal-950/40 to-emerald-950/40 border border-teal-500/30 rounded-2xl p-4 text-center">
                      <div className="text-xs font-mono uppercase text-teal-400 font-bold">
                        Agente Coletor & Deduplicador
                      </div>
                      <div className="text-[11px] text-zinc-400 mt-1">
                        Normalização e checagem de novidade de fatos
                      </div>
                    </div>

                    <div className="bg-gradient-to-r from-amber-950/40 to-orange-950/40 border border-amber-500/30 rounded-2xl p-4 text-center">
                      <div className="text-xs font-mono uppercase text-amber-400 font-bold">
                        Supervisor & Watchdog
                      </div>
                      <div className="text-[11px] text-zinc-400 mt-1">
                        Monitor de integridade e auto-recuperação
                      </div>
                    </div>
                  </div>

                  {/* Flow Arrow */}
                  <div className="text-teal-400 text-xs font-mono">↓ Síntese Editorial com IA Generativa ↓</div>

                  {/* Stage 3: LLM Synthesis & Voice */}
                  <div className="w-full grid grid-cols-3 gap-3">
                    <div className="bg-zinc-900/80 rounded-xl p-4 border border-white/10 text-center">
                      <div className="text-xs font-bold text-white">Redação Jornalística</div>
                      <div className="text-[11px] text-teal-400 font-mono mt-1">Claude 3.5 / Gemini</div>
                    </div>

                    <div className="bg-zinc-900/80 rounded-xl p-4 border border-white/10 text-center">
                      <div className="text-xs font-bold text-white">Curadoria & Imagens</div>
                      <div className="text-[11px] text-teal-400 font-mono mt-1">Layout com Tipografia</div>
                    </div>

                    <div className="bg-zinc-900/80 rounded-xl p-4 border border-white/10 text-center">
                      <div className="text-xs font-bold text-white">Podcast Leo & Ana</div>
                      <div className="text-[11px] text-teal-400 font-mono mt-1">Edge-TTS Neural Audio</div>
                    </div>
                  </div>

                  {/* Flow Arrow */}
                  <div className="text-teal-400 text-xs font-mono">↓ Persistência & Publicação Diária (06:00 BRT) ↓</div>

                  {/* Stage 4: Output Destinations */}
                  <div className="w-full grid grid-cols-3 gap-3">
                    <div className="bg-teal-500/10 border border-teal-500/30 rounded-xl p-3 text-center text-xs font-bold text-teal-300">
                      💻 Portal Web OriginKit
                    </div>
                    <div className="bg-teal-500/10 border border-teal-500/30 rounded-xl p-3 text-center text-xs font-bold text-teal-300">
                      📱 Instagram Carrossel
                    </div>
                    <div className="bg-teal-500/10 border border-teal-500/30 rounded-xl p-3 text-center text-xs font-bold text-teal-300">
                      🎙️ RSS Feed & Spotify
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </section>
  );
}
