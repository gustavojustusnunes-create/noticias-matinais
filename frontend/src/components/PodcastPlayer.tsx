"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  RotateCcw,
  Sparkles,
  Download,
  Headphones,
  Mic,
} from "lucide-react";
import { motion } from "framer-motion";

interface PodcastPlayerProps {
  editionDate: string;
  dataExtenso: string;
}

export function PodcastPlayer({ editionDate, dataExtenso }: PodcastPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [hasError, setHasError] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioSrc = `/api/podcast/${editionDate}`;

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleLoadedMetadata = () => {
      setDuration(audio.duration || 0);
      setHasError(false);
    };

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    const handleError = () => {
      setHasError(true);
      setIsPlaying(false);
    };

    audio.addEventListener("loadedmetadata", handleLoadedMetadata);
    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("error", handleError);

    return () => {
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("error", handleError);
    };
  }, [audioSrc]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current
        .play()
        .then(() => setIsPlaying(true))
        .catch((err) => {
          console.error("Playback error:", err);
          setHasError(true);
        });
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  };

  const handleSpeedCycle = () => {
    const speeds = [1, 1.25, 1.5, 2.0];
    const nextIdx = (speeds.indexOf(playbackRate) + 1) % speeds.length;
    const nextSpeed = speeds[nextIdx];
    setPlaybackRate(nextSpeed);
    if (audioRef.current) {
      audioRef.current.playbackRate = nextSpeed;
    }
  };

  const toggleMute = () => {
    if (!audioRef.current) return;
    const nextMute = !isMuted;
    setIsMuted(nextMute);
    audioRef.current.muted = nextMute;
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setVolume(val);
    if (audioRef.current) {
      audioRef.current.volume = val;
      if (val > 0 && isMuted) {
        setIsMuted(false);
        audioRef.current.muted = false;
      }
    }
  };

  const restartAudio = () => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = 0;
    setCurrentTime(0);
    if (!isPlaying) {
      audioRef.current.play().then(() => setIsPlaying(true));
    }
  };

  const formatTime = (secs: number) => {
    if (isNaN(secs) || secs <= 0) return "0:00";
    const minutes = Math.floor(secs / 60);
    const seconds = Math.floor(secs % 60);
    return `${minutes}:${seconds < 10 ? "0" : ""}${seconds}`;
  };

  return (
    <section id="podcast" className="py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="relative rounded-3xl originkit-card p-6 sm:p-10 overflow-hidden border border-teal-500/20 bg-gradient-to-br from-[#0e171b] via-[#0d1215] to-[#0a0a0c]">
          {/* Ambient glow decoration */}
          <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-teal-500/10 blur-3xl pointer-events-none" />
          <div className="absolute -left-24 -bottom-24 h-72 w-72 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />

          {/* Hidden audio element */}
          <audio ref={audioRef} src={audioSrc} preload="metadata" />

          <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            {/* Host info & Show Title */}
            <div className="lg:col-span-5 space-y-4">
              <div className="inline-flex items-center gap-2 rounded-full bg-teal-500/10 border border-teal-500/30 px-3 py-1 text-xs font-semibold text-teal-400">
                <Headphones className="w-3.5 h-3.5" />
                PODCAST DIÁRIO MATINAL
              </div>

              <h2 className="text-2xl sm:text-3xl font-bold text-white font-serif tracking-tight">
                All News Journal Cast
              </h2>

              <p className="text-sm text-zinc-300 leading-relaxed font-sans">
                Acompanhe o briefing com os âncoras neurais <strong>Leo</strong> & <strong>Ana</strong>,
                que debatem os fatos mais importantes do dia de forma dinâmica, inteligente e descomplicada.
              </p>

              {/* Host Avatars */}
              <div className="flex items-center gap-4 pt-2">
                <div className="flex -space-x-3">
                  <div className="relative flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-tr from-sky-600 to-teal-400 text-white font-bold text-xs border-2 border-[#0e171b] shadow-md">
                    Leo
                  </div>
                  <div className="relative flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-tr from-emerald-500 to-teal-200 text-slate-950 font-bold text-xs border-2 border-[#0e171b] shadow-md">
                    Ana
                  </div>
                </div>
                <div className="text-xs">
                  <div className="font-semibold text-white">Leo & Ana</div>
                  <div className="text-zinc-400 text-[11px]">Vozes Neurais de Alta Definição</div>
                </div>
              </div>
            </div>

            {/* Audio Control Panel */}
            <div className="lg:col-span-7 bg-black/40 rounded-2xl p-6 border border-white/10 backdrop-blur-md space-y-5">
              {/* Animated Visualizer Bars */}
              <div className="flex items-center justify-center gap-1 h-12">
                {[16, 28, 40, 24, 36, 48, 20, 32, 44, 28, 16, 38, 46, 22, 34, 40, 18].map(
                  (baseHeight, i) => (
                    <motion.span
                      key={i}
                      className="w-1.5 rounded-full bg-gradient-to-t from-teal-500 to-emerald-300"
                      animate={{
                        height: isPlaying
                          ? [
                              `${Math.max(8, baseHeight * 0.4)}px`,
                              `${Math.min(48, baseHeight * 1.2)}px`,
                              `${Math.max(8, baseHeight * 0.6)}px`,
                            ]
                          : "6px",
                      }}
                      transition={{
                        repeat: Infinity,
                        duration: 0.6 + (i % 5) * 0.1,
                        ease: "easeInOut",
                      }}
                    />
                  )
                )}
              </div>

              {/* Scrubber / Progress Bar */}
              <div className="space-y-1.5">
                <input
                  type="range"
                  min={0}
                  max={duration || 100}
                  step={0.1}
                  value={currentTime}
                  onChange={handleSeek}
                  className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-teal-400"
                />
                <div className="flex justify-between text-xs text-zinc-400 font-mono">
                  <span>{formatTime(currentTime)}</span>
                  <span>{formatTime(duration)}</span>
                </div>
              </div>

              {/* Main Playback Buttons */}
              <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
                <div className="flex items-center gap-3">
                  <button
                    onClick={restartAudio}
                    className="p-2 text-zinc-400 hover:text-white transition-colors"
                    title="Reiniciar"
                  >
                    <RotateCcw className="w-4 h-4" />
                  </button>

                  <button
                    onClick={togglePlay}
                    className="flex h-12 w-12 items-center justify-center rounded-full bg-teal-400 text-black font-bold shadow-lg shadow-teal-500/30 hover:scale-105 active:scale-95 transition-all"
                  >
                    {isPlaying ? (
                      <Pause className="w-5 h-5 fill-current" />
                    ) : (
                      <Play className="w-5 h-5 fill-current ml-0.5" />
                    )}
                  </button>

                  <button
                    onClick={handleSpeedCycle}
                    className="rounded-lg border border-white/10 px-2.5 py-1 text-xs font-mono font-medium text-zinc-300 hover:text-white hover:border-teal-500/50 transition-colors"
                    title="Velocidade de reprodução"
                  >
                    {playbackRate}x
                  </button>
                </div>

                {/* Volume slider & Direct Download */}
                <div className="flex items-center gap-3">
                  <div className="hidden sm:flex items-center gap-2">
                    <button
                      onClick={toggleMute}
                      className="text-zinc-400 hover:text-white transition-colors"
                    >
                      {isMuted || volume === 0 ? (
                        <VolumeX className="w-4 h-4" />
                      ) : (
                        <Volume2 className="w-4 h-4" />
                      )}
                    </button>
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={isMuted ? 0 : volume}
                      onChange={handleVolumeChange}
                      className="w-16 h-1 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-teal-400"
                    />
                  </div>

                  <a
                    href={audioSrc}
                    download={`podcast_${editionDate}.mp3`}
                    className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-zinc-300 hover:text-white hover:bg-white/10 transition-colors"
                    title="Baixar MP3"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Baixar</span>
                  </a>
                </div>
              </div>

              {hasError && (
                <div className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg p-2.5 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 flex-shrink-0" />
                  <span>
                    O áudio desta edição está sendo finalizado em segundo plano. Tente novamente em instantes!
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
