"use client";

import React, { useState, useEffect } from "react";
import {
  CheckCircle2,
  Clock,
  Edit3,
  Instagram,
  Trash2,
  Sliders,
  Check,
  AlertTriangle,
  X,
  Sparkles,
} from "lucide-react";
import { CuratedNews } from "@/lib/adminData";

interface CurationTabProps {
  curationData: {
    publicacaoAutomaticaAtiva: boolean;
    horarioBatchBRT: string;
    items: CuratedNews[];
  };
  onToast: (msg: string, type?: "success" | "warning" | "error") => void;
}

export function CurationTab({ curationData, onToast }: CurationTabProps) {
  const [autoPublish, setAutoPublish] = useState(curationData.publicacaoAutomaticaAtiva);
  const [newsList, setNewsList] = useState<CuratedNews[]>(curationData.items);
  const [editingItem, setEditingItem] = useState<CuratedNews | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editText, setEditText] = useState("");
  const [timeLeft, setTimeLeft] = useState({ hours: 7, minutes: 28, seconds: 40 });

  // Contador regressivo em tempo real para o batch matinal (05:20 BRT)
  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      const target = new Date();
      target.setHours(5, 20, 0, 0);
      if (now > target) {
        target.setDate(target.getDate() + 1);
      }
      const diffMs = target.getTime() - now.getTime();
      const hours = Math.floor(diffMs / (1000 * 60 * 60));
      const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);
      setTimeLeft({ hours, minutes, seconds });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const handleToggleAutoPublish = async () => {
    const newState = !autoPublish;
    setAutoPublish(newState);

    try {
      const res = await fetch("/api/admin/editorial", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ acao: "toggle_autopublish", ativo: newState }),
      });
      const data = await res.json();
      if (data.success) {
        onToast(data.message, newState ? "success" : "warning");
      }
    } catch (e) {
      onToast("Erro ao alterar publicação automática.", "error");
    }
  };

  const handleApproveInstagram = async (id: string) => {
    try {
      const res = await fetch("/api/admin/editorial", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ acao: "aprovar_instagram", noticiaId: id }),
      });
      const data = await res.json();
      if (data.success) {
        setNewsList((prev) =>
          prev.map((item) =>
            item.id === id ? { ...item, status: "Agendado", aprovadoInstagram: true } : item
          )
        );
        onToast(data.message, "success");
      }
    } catch (e) {
      onToast("Erro ao aprovar matéria para Instagram.", "error");
    }
  };

  const handleDiscard = async (id: string) => {
    try {
      const res = await fetch("/api/admin/editorial", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ acao: "descartar_noticia", noticiaId: id }),
      });
      const data = await res.json();
      if (data.success) {
        setNewsList((prev) => prev.filter((item) => item.id !== id));
        onToast(data.message, "warning");
      }
    } catch (e) {
      onToast("Erro ao descartar matéria.", "error");
    }
  };

  const handleOpenEdit = (item: CuratedNews) => {
    setEditingItem(item);
    setEditTitle(item.titulo);
    setEditText(item.resumo);
  };

  const handleSaveEdit = async () => {
    if (!editingItem) return;

    try {
      const res = await fetch("/api/admin/editorial", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          acao: "editar_noticia",
          noticiaId: editingItem.id,
          titulo: editTitle,
          resumo: editText,
        }),
      });
      const data = await res.json();
      if (data.success) {
        const words = editText.trim().split(/\s+/).length;
        setNewsList((prev) =>
          prev.map((item) =>
            item.id === editingItem.id
              ? {
                  ...item,
                  titulo: editTitle,
                  resumo: editText,
                  contagemPalavras: words,
                  complianceJev: words >= 85 && words <= 105,
                }
              : item
          )
        );
        onToast(data.message, "success");
        setEditingItem(null);
      }
    } catch (e) {
      onToast("Erro ao salvar edição.", "error");
    }
  };

  const editWordCount = editText.trim() ? editText.trim().split(/\s+/).length : 0;
  const isCompliant = editWordCount >= 85 && editWordCount <= 105;

  return (
    <div className="space-y-6">
      
      {/* 1. Header Control Bar & Countdown Timer */}
      <div className="bg-[#0D131C] p-5 md:p-6 rounded-3xl border border-white/10 shadow-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        
        {/* Toggle Switch */}
        <div className="flex items-center gap-4">
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={autoPublish}
              onChange={handleToggleAutoPublish}
              className="sr-only peer"
            />
            <div className="w-13 h-7 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-emerald-500"></div>
          </label>
          <div>
            <div className="text-sm font-bold text-white flex items-center gap-2">
              <span>Publicação Automática Ativa</span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                  autoPublish
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                }`}
              >
                {autoPublish ? "LIGADA" : "PAUSADA"}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Se você não intervir até o fim do timer, o sistema mantém o fluxo automatizado padrão.
            </p>
          </div>
        </div>

        {/* Live Countdown Timer Badge */}
        <div className="bg-[#141C28] px-4 py-2.5 rounded-2xl border border-white/5 flex items-center gap-3 shrink-0">
          <Clock className="w-4 h-4 text-amber-400 animate-pulse" />
          <div>
            <div className="text-[10px] font-mono text-slate-400 uppercase">
              Próximo Disparo Diário (05:20 BRT)
            </div>
            <div className="text-sm font-mono font-bold text-amber-300">
              {String(timeLeft.hours).padStart(2, "0")}h {String(timeLeft.minutes).padStart(2, "0")}m{" "}
              {String(timeLeft.seconds).padStart(2, "0")}s
            </div>
          </div>
        </div>

      </div>

      {/* 2. Grade de Notícias do Dia */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {newsList.map((item) => (
          <div
            key={item.id}
            className="bg-[#0D131C] border border-white/10 rounded-2xl overflow-hidden shadow-xl flex flex-col justify-between hover:border-slate-700 transition-all"
          >
            {/* Header do Card */}
            <div className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  {item.caderno}
                </span>

                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      item.complianceJev
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    }`}
                  >
                    {item.contagemPalavras} palavras {item.complianceJev ? "✓" : "⚠️"}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-white/5 text-slate-300 border border-white/5">
                    {item.status}
                  </span>
                </div>
              </div>

              {/* Título & Resumo */}
              <h4 className="text-sm font-bold text-white font-serif leading-snug">
                {item.titulo}
              </h4>
              <p className="text-xs text-slate-300 leading-relaxed font-sans line-clamp-4">
                {item.resumo}
              </p>
            </div>

            {/* Ações por Notícia */}
            <div className="p-3 bg-[#111722] border-t border-white/5 flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => handleApproveInstagram(item.id)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                    item.aprovadoInstagram
                      ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                      : "bg-pink-500/15 hover:bg-pink-500/25 text-pink-300 border border-pink-500/30"
                  }`}
                  title="Aprovar para publicação no Instagram"
                >
                  <Instagram className="w-3.5 h-3.5" />
                  <span>{item.aprovadoInstagram ? "Aprovado IG" : "Aprovar IG"}</span>
                </button>

                <button
                  onClick={() => handleOpenEdit(item)}
                  className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-semibold flex items-center gap-1.5 border border-white/5 transition-all cursor-pointer"
                >
                  <Edit3 className="w-3.5 h-3.5 text-amber-400" />
                  <span>Editar</span>
                </button>
              </div>

              <button
                onClick={() => handleDiscard(item.id)}
                className="p-2 rounded-xl text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                title="Descartar ou Pular Matéria"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

          </div>
        ))}
      </div>

      {/* 3. Modal de Edição de Notícia */}
      {editingItem && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-3xl bg-[#0D131C] border border-white/15 p-6 shadow-2xl space-y-4">
            
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[10px] font-mono uppercase text-amber-400 font-bold">
                  {editingItem.caderno}
                </span>
                <h3 className="text-base font-bold text-white font-serif">
                  Ajuste Editorial Pré-Disparo
                </h3>
              </div>
              <button
                onClick={() => setEditingItem(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Input Headline */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-semibold text-slate-300">
                Headline / Manchete
              </label>
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#141C28] border border-white/10 text-white text-xs focus:border-amber-400 focus:outline-none"
              />
            </div>

            {/* Textarea Resumo */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-semibold text-slate-300">
                  Resumo Oficial (Diretriz: 85 a 105 palavras em 3 períodos)
                </label>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                    isCompliant
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                  }`}
                >
                  {editWordCount} palavras {isCompliant ? "✓" : "(fora de 85-105)"}
                </span>
              </div>
              <textarea
                rows={5}
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                className="w-full p-3.5 rounded-xl bg-[#141C28] border border-white/10 text-white text-xs font-sans leading-relaxed focus:border-amber-400 focus:outline-none"
              />
            </div>

            {/* Action Buttons */}
            <div className="pt-2 flex justify-end gap-2">
              <button
                onClick={() => setEditingItem(null)}
                className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-xs text-slate-300 font-semibold"
              >
                Cancelar
              </button>
              <button
                onClick={handleSaveEdit}
                className="px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs uppercase tracking-wider transition-all shadow-lg shadow-amber-500/20"
              >
                Salvar Alterações
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
