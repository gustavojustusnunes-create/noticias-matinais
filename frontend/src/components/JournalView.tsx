"use client";

import React, { useState } from "react";
import { Edition, NewsItem } from "../types";
import { Navbar } from "./Navbar";
import { HeroTicker } from "./HeroTicker";
import { PodcastPlayer } from "./PodcastPlayer";
import { NewsGrid } from "./NewsGrid";
import { ArchitectureDashboard } from "./ArchitectureDashboard";
import { SubscribeModal } from "./SubscribeModal";
import { Footer } from "./Footer";

interface JournalViewProps {
  edition: Edition;
}

export function JournalView({ edition }: JournalViewProps) {
  const [isSubscribeOpen, setIsSubscribeOpen] = useState(false);

  // Extract featured items for the 5-second Hero spotlight
  const featuredNews: { item: NewsItem; category: string }[] = [];
  const allHeadlines: string[] = [];

  if (edition.cadernos) {
    Object.entries(edition.cadernos).forEach(([cat, items]) => {
      items.forEach((item) => {
        allHeadlines.push(item.titulo);
        if (item.imagem && item.imagem.startsWith("http")) {
          featuredNews.push({ item, category: cat });
        }
      });
    });
  }

  // Fallback if no images found
  if (featuredNews.length === 0) {
    featuredNews.push({
      item: {
        titulo: edition.manchete,
        link: "#",
        imagem: "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80",
        resumo: edition.editorial,
      },
      category: "MANCHETE",
    });
  }

  return (
    <div className="flex flex-col min-h-screen originkit-grid">
      <Navbar
        editionDate={edition.data}
        dataExtenso={edition.data_extenso}
        onOpenSubscribe={() => setIsSubscribeOpen(true)}
      />

      <main className="flex-1">
        {/* 1. Hero with 5-second rotating news, background image with word overlay, and marquee */}
        <HeroTicker
          headline={edition.manchete}
          editorial={edition.editorial}
          featuredNews={featuredNews}
          allHeadlines={allHeadlines}
        />

        {/* 2. Interactive Podcast Player (Leo & Ana edge-tts audio) */}
        <PodcastPlayer
          editionDate={edition.data}
          dataExtenso={edition.data_extenso}
        />

        {/* 3. Bento News Grid with animated cadernos tabs */}
        <NewsGrid cadernos={edition.cadernos} />

        {/* 4. Architecture & Agent Telemetry Dashboard (Protected by 3344) */}
        <ArchitectureDashboard />
      </main>

      <Footer />

      <SubscribeModal
        isOpen={isSubscribeOpen}
        onClose={() => setIsSubscribeOpen(false)}
      />
    </div>
  );
}
