"use client";

import React, { useState } from "react";
import { Sparkles, Radio, Shield, Bell, BookOpen } from "lucide-react";
import { motion } from "framer-motion";

interface NavbarProps {
  editionDate: string;
  dataExtenso: string;
  onOpenSubscribe: () => void;
}

export function Navbar({ editionDate, dataExtenso, onOpenSubscribe }: NavbarProps) {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-[#0a0a0c]/85 backdrop-blur-xl transition-all">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand & Live Indicator */}
        <div className="flex items-center gap-4">
          <a href="#" className="flex items-center gap-2 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-teal-400 to-emerald-700 text-black font-black text-lg shadow-md shadow-emerald-500/20 group-hover:scale-105 transition-transform">
              N
            </div>
            <div className="flex flex-col">
              <span className="text-sm sm:text-base font-bold tracking-tight text-white flex items-center gap-1.5 font-serif">
                ALL NEWS JOURNAL
                <span className="rounded bg-teal-500/10 px-1.5 py-0.5 text-[10px] font-mono font-medium text-teal-400 border border-teal-500/20">
                  ORIGINKIT
                </span>
              </span>
              <span className="text-[11px] text-zinc-400 hidden sm:inline-block truncate">
                {dataExtenso || editionDate}
              </span>
            </div>
          </a>

          {/* Live Badge */}
          <div className="hidden md:flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-400 font-medium">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
            </span>
            Edição do Dia
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="hidden lg:flex items-center gap-6 text-xs font-medium text-zinc-300">
          <a href="#manchete" className="hover:text-teal-400 transition-colors flex items-center gap-1">
            <BookOpen className="w-3.5 h-3.5 text-teal-400" />
            Manchete
          </a>
          <a href="#podcast" className="hover:text-teal-400 transition-colors flex items-center gap-1">
            <Radio className="w-3.5 h-3.5 text-teal-400" />
            Podcast Leo & Ana
          </a>
          <a href="#cadernos" className="hover:text-teal-400 transition-colors">
            Cadernos
          </a>
          <a href="#arquitetura" className="hover:text-teal-400 transition-colors flex items-center gap-1">
            <Shield className="w-3.5 h-3.5 text-amber-400" />
            Arquitetura & Agentes
          </a>
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenSubscribe}
            className="relative inline-flex items-center justify-center gap-1.5 rounded-full bg-gradient-to-r from-teal-500 to-emerald-600 px-4 py-1.5 text-xs font-semibold text-black shadow-lg shadow-teal-500/25 hover:shadow-teal-500/40 hover:brightness-110 active:scale-95 transition-all"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>Assinar Grátis</span>
          </button>
        </div>
      </div>
    </header>
  );
}
