"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ExternalLink, Layers, ArrowUpRight, Share2, Check, X, BookOpen } from "lucide-react";
import { NewsItem } from "../types";

interface NewsGridProps {
  cadernos: Record<string, NewsItem[]>;
}

export function NewsGrid({ cadernos }: NewsGridProps) {
  const categories = ["Todos", ...Object.keys(cadernos)];
  const [activeCategory, setActiveCategory] = useState("Todos");
  const [selectedNews, setSelectedNews] = useState<NewsItem | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Flatten or filter items
  const allItems: { item: NewsItem; category: string }[] = [];
  Object.entries(cadernos).forEach(([cat, list]) => {
    list.forEach((item) => {
      allItems.push({ item, category: cat });
    });
  });

  const filteredItems =
    activeCategory === "Todos"
      ? allItems
      : allItems.filter((i) => i.category === activeCategory);

  const handleShare = (link: string, title: string) => {
    if (navigator.share) {
      navigator.share({ title, url: link }).catch(() => {});
    } else {
      navigator.clipboard.writeText(link);
      setCopiedId(link);
      setTimeout(() => setCopiedId(null), 2000);
    }
  };

  return (
    <section id="cadernos" className="py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-teal-400 uppercase tracking-widest mb-1">
              <Layers className="w-4 h-4" />
              Edição Completa
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight font-serif">
              Cadernos & Destaques
            </h2>
          </div>

          <div className="text-xs text-zinc-400">
            Mostrando <strong>{filteredItems.length}</strong> artigos selecionados
          </div>
        </div>

        {/* Category Filters Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-4 scrollbar-none">
          {categories.map((cat) => {
            const isActive = activeCategory === cat;
            return (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`relative px-4 py-2 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                  isActive
                    ? "text-black font-bold"
                    : "text-zinc-400 hover:text-white bg-white/5 hover:bg-white/10"
                }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeFilterPill"
                    className="absolute inset-0 rounded-full bg-teal-400 shadow-md shadow-teal-500/30"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <span className="relative z-10">{cat}</span>
              </button>
            );
          })}
        </div>

        {/* News Grid */}
        <motion.div layout className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-6">
          <AnimatePresence>
            {filteredItems.map(({ item, category }, idx) => (
              <motion.article
                layout
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.96 }}
                transition={{ duration: 0.3 }}
                key={`${category}-${idx}-${item.titulo.slice(0, 15)}`}
                className="group relative rounded-2xl originkit-card overflow-hidden flex flex-col justify-between border border-white/10 hover:border-teal-500/30 transition-all cursor-pointer"
                onClick={() => setSelectedNews(item)}
              >
                {/* Image Section */}
                <div className="relative h-48 sm:h-52 w-full overflow-hidden bg-zinc-900">
                  <img
                    src={
                      item.imagem ||
                      "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?auto=format&fit=crop&w=800&q=80"
                    }
                    alt={item.titulo}
                    loading="lazy"
                    className="h-full w-full object-cover object-center group-hover:scale-105 transition-transform duration-500 filter brightness-90"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src =
                        "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=800&q=80";
                    }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-[#0e1014] via-transparent to-transparent" />
                  
                  {/* Category Pill on Image */}
                  <span className="absolute top-3 left-3 rounded-md bg-black/70 backdrop-blur-md px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-teal-300 border border-white/10">
                    {category}
                  </span>
                </div>

                {/* Content Section */}
                <div className="p-5 flex-1 flex flex-col justify-between space-y-3">
                  <div>
                    <h3 className="text-base sm:text-lg font-bold text-white group-hover:text-teal-300 transition-colors font-serif line-clamp-2">
                      {item.titulo}
                    </h3>
                    <p className="mt-2 text-xs sm:text-sm text-zinc-400 line-clamp-3 leading-relaxed font-sans">
                      {item.resumo || "Clique para ler os detalhes da cobertura desta notícia."}
                    </p>
                  </div>

                  {/* Card Footer Actions */}
                  <div className="flex items-center justify-between pt-3 border-t border-white/5 text-xs text-zinc-400">
                    <span className="flex items-center gap-1 group-hover:text-teal-400 transition-colors">
                      <span>Ver matéria</span>
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </span>

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleShare(item.link, item.titulo);
                      }}
                      className="p-1.5 rounded-lg hover:bg-white/10 text-zinc-400 hover:text-white transition-colors"
                      title="Compartilhar link"
                    >
                      {copiedId === item.link ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Share2 className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>
              </motion.article>
            ))}
          </AnimatePresence>
        </motion.div>

        {/* Modal Story Reader */}
        <AnimatePresence>
          {selectedNews && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                className="relative max-w-2xl w-full rounded-3xl bg-[#121318] border border-white/10 p-6 sm:p-8 shadow-2xl overflow-hidden max-h-[90vh] overflow-y-auto"
              >
                {/* Close Button */}
                <button
                  onClick={() => setSelectedNews(null)}
                  className="absolute top-4 right-4 p-2 rounded-full bg-white/10 text-zinc-300 hover:text-white hover:bg-white/20 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>

                {/* News Image */}
                {selectedNews.imagem && (
                  <div className="h-56 sm:h-72 w-full rounded-2xl overflow-hidden mb-6 bg-zinc-900">
                    <img
                      src={selectedNews.imagem}
                      alt={selectedNews.titulo}
                      className="h-full w-full object-cover"
                    />
                  </div>
                )}

                {/* Headline */}
                <h2 className="text-xl sm:text-2xl font-black text-white font-serif mb-4 leading-snug">
                  {selectedNews.titulo}
                </h2>

                {/* Full Resumo */}
                <div className="text-sm sm:text-base text-zinc-300 leading-relaxed font-sans space-y-4 mb-8">
                  <p>{selectedNews.resumo}</p>
                </div>

                {/* Bottom Bar */}
                <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-white/10">
                  <span className="text-xs text-zinc-500 font-mono">
                    All News Journal • Curadoria IA
                  </span>
                  {selectedNews.link && (
                    <a
                      href={selectedNews.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 rounded-xl bg-teal-400 text-black px-4 py-2 text-xs font-bold hover:bg-teal-300 transition-colors"
                    >
                      Acessar Fonte Original
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
