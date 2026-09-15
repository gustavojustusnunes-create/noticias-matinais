"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Mail, Sparkles, CheckCircle2 } from "lucide-react";

interface SubscribeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SubscribeModal({ isOpen, onClose }: SubscribeModalProps) {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setSubmitted(true);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          className="relative max-w-md w-full rounded-3xl bg-[#121318] border border-white/10 p-6 sm:p-8 shadow-2xl overflow-hidden"
        >
          {/* Ambient Glow */}
          <div className="absolute -top-16 -right-16 h-40 w-40 rounded-full bg-teal-500/20 blur-2xl pointer-events-none" />

          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 rounded-full text-zinc-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>

          {!submitted ? (
            <div className="space-y-5">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-500/10 text-teal-400 border border-teal-500/20">
                <Sparkles className="w-6 h-6" />
              </div>

              <div>
                <h3 className="text-xl font-bold text-white font-serif">
                  Receba o Jornal às 06:00
                </h3>
                <p className="mt-1 text-xs sm:text-sm text-zinc-400 leading-relaxed font-sans">
                  Comece o dia informado com a melhor curadoria de notícias, sínteses analíticas e o podcast de Leo & Ana direto na sua caixa de entrada.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-3">
                <div className="relative">
                  <Mail className="absolute left-3.5 top-3 h-4 w-4 text-zinc-500" />
                  <input
                    type="email"
                    required
                    placeholder="seu.email@exemplo.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full rounded-xl border border-white/10 bg-black/50 pl-10 pr-4 py-2.5 text-xs sm:text-sm text-white placeholder-zinc-500 focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-400 font-sans"
                  />
                </div>

                <button
                  type="submit"
                  className="w-full rounded-xl bg-teal-400 py-2.5 text-xs sm:text-sm font-bold text-black hover:bg-teal-300 transition-colors shadow-lg shadow-teal-500/20"
                >
                  Assinar Gratuitamente
                </button>
              </form>

              <div className="text-center">
                <span className="text-[11px] text-zinc-500">
                  Sem spam. Cancele quando quiser com apenas 1 clique.
                </span>
              </div>
            </div>
          ) : (
            <div className="text-center py-6 space-y-4">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold text-white font-serif">
                Inscrição Confirmada!
              </h3>
              <p className="text-xs text-zinc-400 max-w-xs mx-auto">
                Você receberá a próxima edição matinal amanhã pontualmente às 06:00.
              </p>
              <button
                onClick={onClose}
                className="mt-4 rounded-xl bg-white/10 px-5 py-2 text-xs font-semibold text-white hover:bg-white/20 transition-colors"
              >
                Concluir
              </button>
            </div>
          )}
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
