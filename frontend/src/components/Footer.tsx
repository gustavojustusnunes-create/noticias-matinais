import React from "react";
import { Sparkles, Radio, Shield, Heart } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-white/10 bg-[#060608] py-12 text-zinc-400 text-xs">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-teal-400 text-black font-black text-sm">
                N
              </div>
              <span className="text-base font-bold text-white font-serif">
                ALL NEWS JOURNAL
              </span>
            </div>
            <p className="text-zinc-400 max-w-sm leading-relaxed">
              Jornalismo autônomo matinal alimentado por múltiplos agentes de inteligência artificial.
              Edições geradas diariamente às 06:00 com sínteses balanceadas, podcast neural e publicação multiplataforma.
            </p>
          </div>

          <div>
            <h4 className="text-white font-semibold mb-3 uppercase tracking-wider text-[11px] font-mono">
              Seções
            </h4>
            <ul className="space-y-2">
              <li><a href="#manchete" className="hover:text-teal-400 transition-colors">Manchete do Dia</a></li>
              <li><a href="#podcast" className="hover:text-teal-400 transition-colors">Podcast Leo & Ana</a></li>
              <li><a href="#cadernos" className="hover:text-teal-400 transition-colors">Cadernos Editoriais</a></li>
              <li><a href="#arquitetura" className="hover:text-teal-400 transition-colors">Painel de Agentes (Senha 3344)</a></li>
            </ul>
          </div>

          <div>
            <h4 className="text-white font-semibold mb-3 uppercase tracking-wider text-[11px] font-mono">
              Origem
            </h4>
            <p className="text-zinc-500 leading-relaxed text-[11px]">
              Desenvolvido com OriginKit (Next.js 15, Tailwind CSS, Framer Motion) integrado com Claude 3.5 Sonnet, Gemini e Edge-TTS.
            </p>
          </div>
        </div>

        <div className="border-t border-white/5 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-zinc-500">
          <p>© {new Date().getFullYear()} All News Journal. Todos os direitos reservados.</p>
          <div className="flex items-center gap-2 text-[11px]">
            <span>Curadoria Editorial Inteligente</span>
            <span>•</span>
            <span className="text-teal-400">Edição Ativa</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
