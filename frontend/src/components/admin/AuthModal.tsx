"use client";

import React, { useState } from "react";
import { Lock, ShieldCheck, Key, AlertCircle, Sparkles, ArrowRight } from "lucide-react";

interface AuthModalProps {
  onSuccess: () => void;
}

export function AuthModal({ onSuccess }: AuthModalProps) {
  const [pin, setPin] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (valueToTest?: string) => {
    const token = (valueToTest || pin).trim();
    if (!token) return;

    setLoading(true);
    setErrorMsg("");

    try {
      const res = await fetch("/api/admin/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin: token }),
      });

      const data = await res.json();
      if (res.ok && data.success) {
        localStorage.setItem("anj_admin_pin", token);
        onSuccess();
      } else {
        setErrorMsg(data.error || "PIN incorreto. (Padrão executivo: 2026)");
        setPin("");
      }
    } catch (e) {
      setErrorMsg("Erro de conexão com o servidor.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickUnlock = () => {
    setPin("2026");
    handleSubmit("2026");
  };

  return (
    <div className="fixed inset-0 z-50 bg-[#070A0F]/95 backdrop-blur-xl flex items-center justify-center p-4">
      <div className="w-full max-w-sm rounded-3xl bg-[#0D131C] border border-white/10 p-6 md:p-8 shadow-2xl text-center space-y-6">
        
        {/* Brand Icon */}
        <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-500/20 to-blue-600/20 border border-amber-500/30 flex items-center justify-center text-amber-400 font-serif font-black text-2xl shadow-lg shadow-amber-500/10">
          AN
        </div>

        <div>
          <span className="text-[10px] font-mono tracking-widest text-amber-400 uppercase font-semibold">
            All News Journal
          </span>
          <h2 className="text-xl font-bold text-white tracking-tight font-serif mt-1">
            Mission Control Center
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Autenticação restrita ao Fundador & Editor Executivo
          </p>
        </div>

        {/* Input Field */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
          className="space-y-4"
        >
          <div className="relative">
            <input
              type="password"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={6}
              autoComplete="one-time-code"
              placeholder="Digite o PIN (2026)"
              value={pin}
              onChange={(e) => {
                const val = e.target.value.replace(/\D/g, "");
                setPin(val);
                if (val.length === 4) {
                  handleSubmit(val);
                }
              }}
              autoFocus
              className="w-full text-center tracking-[0.4em] font-mono text-2xl font-bold py-3 px-4 rounded-xl bg-[#141C28] border-2 border-white/15 text-white placeholder-slate-600 focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-400/20 transition-all shadow-inner"
            />
          </div>

          {errorMsg && (
            <p className="text-xs text-rose-400 font-medium flex items-center justify-center gap-1.5 animate-shake">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{errorMsg}</span>
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !pin}
            className="w-full py-3 px-4 rounded-xl bg-amber-500 hover:bg-amber-400 disabled:opacity-40 disabled:hover:bg-amber-500 text-slate-950 font-bold text-xs uppercase tracking-wider transition-all shadow-lg shadow-amber-500/20 flex items-center justify-center gap-2 cursor-pointer"
          >
            {loading ? (
              <span>Autenticando...</span>
            ) : (
              <>
                <span>Desbloquear Cockpit</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Quick Demo Unlock Button */}
        <div className="pt-2 border-t border-white/5">
          <button
            onClick={handleQuickUnlock}
            type="button"
            className="w-full text-xs text-slate-400 hover:text-amber-300 font-medium py-2 px-3 rounded-lg bg-white/5 hover:bg-white/10 border border-white/5 transition-all flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>Preenchimento Rápido (PIN 2026)</span>
          </button>
        </div>

      </div>
    </div>
  );
}
