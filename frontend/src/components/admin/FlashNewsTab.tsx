"use client";

import React, { useState } from "react";
import {
  Zap,
  Send,
  Instagram,
  Bell,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Layers,
  Radio,
} from "lucide-react";

interface FlashNewsTabProps {
  onToast: (msg: string, type?: "success" | "warning" | "error") => void;
}

export function FlashNewsTab({ onToast }: FlashNewsTabProps) {
  const [tema, setTema] = useState("");
  const [contexto, setContexto] = useState("");
  const [caderno, setCaderno] = useState("Economia");
  const [tom, setTom] = useState("Analítico e Sóbrio (Padrão ANJ)");
  const [destinos, setDestinos] = useState({
    instagram: true,
    story: true,
    push: false,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastDispatched, setLastDispatched] = useState<any | null>(null);

  const cadernos = [
    "Economia",
    "IA & Tecnologia",
    "Mundo",
    "Política",
    "Wellness",
    "Ciência",
    "Cinema & Cultura",
    "Fofoca & Bastidores",
  ];

  const tons = [
    "Analítico e Sóbrio (Padrão ANJ)",
    "Urgente / Breaking News",
    "Alerta de Mercado Financeiro",
    "Neutro & Institucional",
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tema.trim() || !contexto.trim()) {
      onToast("Preencha a manchete bruta e o contexto dos fatos.", "warning");
      return;
    }

    setIsSubmitting(true);

    try {
      const res = await fetch("/api/admin/flash-news", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tema,
          contexto,
          caderno,
          tom,
          destinos,
        }),
      });

      const data = await res.json();
      if (res.ok && data.success) {
        onToast(data.message, "success");
        setLastDispatched(data.payload);
        setTema("");
        setContexto("");
      } else {
        onToast(data.error || "Falha ao despachar Flash News.", "error");
      }
    } catch (err) {
      onToast("Erro de conexão ao enviar Flash News.", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-8">
      
      {/* 1. Header Banner */}
      <div className="bg-gradient-to-r from-amber-500/15 via-[#0D131C] to-blue-500/15 p-6 rounded-3xl border border-amber-500/30 shadow-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30 mb-2">
            <Zap className="w-3.5 h-3.5" />
            <span>Extraordinary Pipeline</span>
          </div>
          <h2 className="text-xl md:text-2xl font-bold text-white font-serif tracking-tight">
            Flash News Dispatcher (Disparo Extraordinário)
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
            Aciona imediatamente o Gemini Flash para pesquisar, redigir no padrão editorial rígido (85-105 palavras, 3 períodos) e despachar para as redes e newsletter sem esperar o batch diário das 05:20.
          </p>
        </div>

        <div className="bg-[#141C28] p-3 rounded-2xl border border-white/5 text-center shrink-0">
          <span className="text-[10px] font-mono uppercase text-slate-400">Latência de Disparo</span>
          <div className="text-sm font-mono font-bold text-emerald-400 mt-0.5">&lt; 15 segundos</div>
        </div>
      </div>

      {/* 2. Formulário Dedicado */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Coluna 1 & 2: Formulário */}
        <div className="lg:col-span-2 bg-[#0D131C] p-6 sm:p-8 rounded-3xl border border-white/10 shadow-2xl space-y-6">
          <form onSubmit={handleSubmit} className="space-y-5">
            
            {/* Input: Tema / Manchete Bruta */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                <span>Manchete Bruta / Tema Central</span>
                <span className="text-amber-400">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="Ex: Copom convoca reunião extraordinária e altera projeção de juros"
                value={tema}
                onChange={(e) => setTema(e.target.value)}
                className="w-full px-4 py-3 rounded-xl bg-[#141C28] border border-white/15 text-white text-xs sm:text-sm placeholder-slate-500 focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-400/20 transition-all font-medium"
              />
            </div>

            {/* Textarea: Contexto / Descrição dos Fatos */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <span>Contexto Factual & Dados Brutos</span>
                  <span className="text-amber-400">*</span>
                </label>
                <span className="text-[10px] text-slate-400">Links, valores, causas e desdobramentos</span>
              </div>
              <textarea
                rows={5}
                required
                placeholder="Cole aqui os dados crus, comunicados oficiais ou links da notícia. O Gemini Flash extrairá apenas os 3 períodos fundamentais (O Fato, A Causa e O Impacto)."
                value={contexto}
                onChange={(e) => setContexto(e.target.value)}
                className="w-full p-4 rounded-xl bg-[#141C28] border border-white/15 text-white text-xs sm:text-sm placeholder-slate-500 focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-400/20 transition-all leading-relaxed font-sans"
              />
            </div>

            {/* Selects: Caderno Prioritário & Tom Editorial */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Caderno Prioritário</label>
                <select
                  value={caderno}
                  onChange={(e) => setCaderno(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#141C28] border border-white/15 text-white text-xs focus:border-amber-400 focus:outline-none cursor-pointer"
                >
                  {cadernos.map((c) => (
                    <option key={c} value={c} className="bg-[#0D131C] text-white">
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Tom de Voz</label>
                <select
                  value={tom}
                  onChange={(e) => setTom(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#141C28] border border-white/15 text-white text-xs focus:border-amber-400 focus:outline-none cursor-pointer"
                >
                  {tons.map((t) => (
                    <option key={t} value={t} className="bg-[#0D131C] text-white">
                      {t}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Checkboxes de Destino */}
            <div className="space-y-2.5 pt-2">
              <label className="text-xs font-bold text-white uppercase tracking-wider">
                Canais de Distribuição da Flash News
              </label>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <label className="flex items-center gap-2.5 p-3 rounded-xl bg-[#141C28] border border-white/10 hover:border-pink-500/40 cursor-pointer transition-colors">
                  <input
                    type="checkbox"
                    checked={destinos.instagram}
                    onChange={(e) => setDestinos({ ...destinos, instagram: e.target.checked })}
                    className="w-4 h-4 rounded text-pink-500 focus:ring-0 bg-[#0A0E14] border-white/20"
                  />
                  <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                    <Instagram className="w-3.5 h-3.5 text-pink-400" />
                    <span>Post Feed (IG)</span>
                  </div>
                </label>

                <label className="flex items-center gap-2.5 p-3 rounded-xl bg-[#141C28] border border-white/10 hover:border-purple-500/40 cursor-pointer transition-colors">
                  <input
                    type="checkbox"
                    checked={destinos.story}
                    onChange={(e) => setDestinos({ ...destinos, story: e.target.checked })}
                    className="w-4 h-4 rounded text-purple-500 focus:ring-0 bg-[#0A0E14] border-white/20"
                  />
                  <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                    <Radio className="w-3.5 h-3.5 text-purple-400" />
                    <span>Story 9:16</span>
                  </div>
                </label>

                <label className="flex items-center gap-2.5 p-3 rounded-xl bg-[#141C28] border border-white/10 hover:border-amber-500/40 cursor-pointer transition-colors">
                  <input
                    type="checkbox"
                    checked={destinos.push}
                    onChange={(e) => setDestinos({ ...destinos, push: e.target.checked })}
                    className="w-4 h-4 rounded text-amber-500 focus:ring-0 bg-[#0A0E14] border-white/20"
                  />
                  <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                    <Bell className="w-3.5 h-3.5 text-amber-400" />
                    <span>Push Relâmpago</span>
                  </div>
                </label>
              </div>
            </div>

            {/* Botão de Disparo */}
            <div className="pt-4 border-t border-white/5">
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-4 px-6 rounded-2xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 disabled:opacity-40 text-slate-950 font-black text-xs uppercase tracking-widest transition-all shadow-xl shadow-amber-500/20 flex items-center justify-center gap-2 cursor-pointer active:scale-[0.99]"
              >
                {isSubmitting ? (
                  <span>Disparando Esteira Agêntica...</span>
                ) : (
                  <>
                    <Zap className="w-4 h-4 fill-current" />
                    <span>Processar & Publicar Flash News</span>
                  </>
                )}
              </button>
            </div>

          </form>
        </div>

        {/* Coluna 3: Painel Informativo & Último Disparo */}
        <div className="space-y-6">
          
          {/* Card de Regras Editoriais */}
          <div className="bg-[#0D131C] p-6 rounded-3xl border border-white/10 shadow-xl space-y-4">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span>Diretrizes Rígidas do Gemini Flash</span>
            </h3>

            <ul className="text-xs text-slate-300 space-y-2.5 leading-relaxed">
              <li className="flex items-start gap-2">
                <span className="text-amber-400 font-bold">1.</span>
                <span><strong>Extensão Obrigatória:</strong> Rigorosamente entre 85 e 105 palavras.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-400 font-bold">2.</span>
                <span><strong>Três Períodos:</strong> O Fato (quem/o que), A Causa (números/porquê), O Impacto (consequência).</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-400 font-bold">3.</span>
                <span><strong>Limpeza Total:</strong> Elimina créditos, nomes de agências e menções a fotógrafos.</span>
              </li>
            </ul>
          </div>

          {/* Último Disparo Executado */}
          {lastDispatched && (
            <div className="bg-[#0D131C] p-6 rounded-3xl border border-emerald-500/30 shadow-xl space-y-3 animate-in fade-in">
              <div className="flex items-center justify-between text-emerald-400 text-xs font-bold">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Último Disparo Enviado</span>
                </span>
                <span className="font-mono text-[10px] text-slate-400">
                  {lastDispatched.trackingId}
                </span>
              </div>

              <h4 className="text-xs font-bold text-white font-serif">
                {lastDispatched.tema}
              </h4>

              <div className="text-[11px] text-slate-400 space-y-1">
                <div>Caderno: <span className="text-slate-200">{lastDispatched.caderno}</span></div>
                <div>Status: <span className="text-emerald-400 font-semibold">{lastDispatched.status}</span></div>
              </div>
            </div>
          )}

        </div>

      </div>

    </div>
  );
}
