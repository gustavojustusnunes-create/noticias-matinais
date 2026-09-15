"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, ExternalLink, Flame, Clock, Newspaper } from "lucide-react";
import { NewsItem } from "../types";

interface HeroTickerProps {
  headline: string;
  editorial: string;
  featuredNews: { item: NewsItem; category: string }[];
  allHeadlines: string[];
}

export function HeroTicker({
  headline,
  editorial,
  featuredNews,
  allHeadlines,
}: HeroTickerProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  const activeNews = featuredNews[currentIndex] || {
    item: {
      titulo: headline,
      link: "#",
      imagem: "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80",
      resumo: editorial,
    },
    category: "DESTAQUE",
  };

  // 5-second automatic rotation
  useEffect(() => {
    if (isPaused || featuredNews.length <= 1) return;
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % featuredNews.length);
    }, 5000);
    return () => clearInterval(interval);
  }, [isPaused, featuredNews.length]);

  return (
    <section id="manchete" className="relative pt-6 pb-12 overflow-hidden">
      {/* Editorial Header */}
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mb-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-white/10 pb-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-teal-400 uppercase tracking-widest mb-1">
              <Flame className="w-4 h-4 text-orange-500 animate-pulse" />
              Cobertura Matinal
            </div>
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-black text-white tracking-tight font-serif">
              A Síntese da Manhã
            </h1>
          </div>
          <p className="max-w-xl text-sm text-zinc-400 italic">
            "{editorial}"
          </p>
        </div>
      </div>

      {/* Main Feature Carousel Card */}
      <div
        className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8"
        onMouseEnter={() => setIsPaused(true)}
        onMouseLeave={() => setIsPaused(false)}
      >
        <div className="relative rounded-3xl overflow-hidden originkit-card border border-white/10 shadow-2xl min-h-[480px] md:min-h-[520px] flex flex-col justify-end">
          {/* Animated Background Image */}
          <AnimatePresence mode="wait">
            <motion.div
              key={currentIndex}
              initial={{ opacity: 0, scale: 1.05 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              className="absolute inset-0 z-0"
            >
              <img
                src={
                  activeNews.item.imagem ||
                  "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80"
                }
                alt={activeNews.item.titulo}
                className="h-full w-full object-cover object-center filter brightness-[0.75]"
                onError={(e) => {
                  (e.target as HTMLImageElement).src =
                    "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?auto=format&fit=crop&w=1200&q=80";
                }}
              />
              {/* Gradient masks */}
              <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0c] via-[#0a0a0c]/60 to-transparent" />
              <div className="absolute inset-0 bg-gradient-to-r from-[#0a0a0c]/80 via-transparent to-transparent hidden md:block" />
            </motion.div>
          </AnimatePresence>

          {/* Content Over the Image */}
          <div className="relative z-10 p-6 sm:p-10 md:p-14 max-w-4xl">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentIndex}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.4 }}
                className="space-y-4"
              >
                {/* Highlight Keyword Pill (User requirement: "com uma palavra com imagem no fundo") */}
                <div className="flex flex-wrap items-center gap-2.5">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-teal-500/90 text-black px-3.5 py-1 text-xs font-black uppercase tracking-wider shadow-lg shadow-teal-500/30">
                    <Newspaper className="w-3.5 h-3.5" />
                    {activeNews.category}
                  </span>
                  <span className="flex items-center gap-1 text-xs text-zinc-300 bg-black/50 backdrop-blur-md px-3 py-1 rounded-full border border-white/10">
                    <Clock className="w-3.5 h-3.5 text-teal-400" />
                    Troca a cada 5s
                  </span>
                  <span className="text-xs text-zinc-400 hidden sm:inline">
                    {currentIndex + 1} de {featuredNews.length} destaques
                  </span>
                </div>

                {/* Headline */}
                <h2 className="text-2xl sm:text-3xl md:text-4xl font-extrabold text-white leading-tight font-serif drop-shadow-md">
                  {activeNews.item.titulo}
                </h2>

                {/* Description Excerpt */}
                <p className="text-sm sm:text-base text-zinc-300 line-clamp-3 md:line-clamp-4 leading-relaxed font-sans max-w-3xl drop-shadow">
                  {activeNews.item.resumo}
                </p>

                {/* Action Link */}
                <div className="pt-2 flex items-center gap-4">
                  {activeNews.item.link && (
                    <a
                      href={activeNews.item.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 rounded-xl bg-white text-black px-5 py-2.5 text-xs sm:text-sm font-bold shadow-xl hover:bg-zinc-200 transition-transform active:scale-95"
                    >
                      Ler Matéria Completa
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </div>
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Navigation Controls & Progress Dots */}
          <div className="relative z-10 flex items-center justify-between border-t border-white/10 bg-black/40 backdrop-blur-md px-6 py-3">
            <div className="flex items-center gap-1.5">
              {featuredNews.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => setCurrentIndex(idx)}
                  className={`h-1.5 transition-all rounded-full ${
                    idx === currentIndex
                      ? "w-8 bg-teal-400"
                      : "w-2 bg-white/20 hover:bg-white/40"
                  }`}
                  aria-label={`Slide ${idx + 1}`}
                />
              ))}
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() =>
                  setCurrentIndex(
                    (prev) => (prev - 1 + featuredNews.length) % featuredNews.length
                  )
                }
                className="rounded-full p-2 text-zinc-300 hover:text-white hover:bg-white/10 transition-colors"
                aria-label="Anterior"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <button
                onClick={() =>
                  setCurrentIndex((prev) => (prev + 1) % featuredNews.length)
                }
                className="rounded-full p-2 text-zinc-300 hover:text-white hover:bg-white/10 transition-colors"
                aria-label="Próximo"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* OriginKit Continuous Marquee Ticker */}
      {allHeadlines.length > 0 && (
        <div className="mt-8 border-y border-white/5 bg-zinc-950/80 py-2.5 overflow-hidden flex items-center">
          <div className="flex-shrink-0 bg-teal-500/20 text-teal-400 border border-teal-500/30 font-mono text-[11px] font-bold px-3 py-1 ml-4 rounded-md uppercase tracking-wider z-10 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-teal-400 animate-ping inline-block" />
            URGENTE
          </div>
          <div className="flex whitespace-nowrap overflow-hidden [mask-image:linear-gradient(to_right,transparent,white_5%,white_95%,transparent)] w-full">
            <div className="flex animate-marquee gap-8 items-center text-xs text-zinc-300 font-medium pl-6">
              {allHeadlines.concat(allHeadlines).map((hl, i) => (
                <div key={i} className="flex items-center gap-4">
                  <span className="text-zinc-500">•</span>
                  <span className="hover:text-teal-300 transition-colors cursor-default">
                    {hl}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
