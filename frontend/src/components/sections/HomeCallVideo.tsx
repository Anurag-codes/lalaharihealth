"use client";

import { useEffect, useRef, useState } from "react";
import { Maximize2, Pause, Play, X } from "lucide-react";

const POPUP_DISMISSED_EVENT = "lalahari:home-offer-dismissed";

export function HomeCallVideo() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isVisible, setIsVisible] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioAutoplayBlocked, setAudioAutoplayBlocked] = useState(false);

  useEffect(() => {
    const handlePopupDismissed = () => {
      setIsVisible(true);
      setIsMinimized(false);
      const playAttempt = videoRef.current?.play();
      playAttempt?.then(() => setAudioAutoplayBlocked(false)).catch(() => setAudioAutoplayBlocked(true));
    };

    window.addEventListener(POPUP_DISMISSED_EVENT, handlePopupDismissed);
    return () => window.removeEventListener(POPUP_DISMISSED_EVENT, handlePopupDismissed);
  }, []);

  const closeVideo = () => {
    videoRef.current?.pause();
    setIsPlaying(false);
    setIsVisible(false);
  };

  const togglePlayback = () => {
    const video = videoRef.current;
    if (!video) return;

    if (video.paused) {
      video.play().then(() => setAudioAutoplayBlocked(false)).catch(() => setAudioAutoplayBlocked(true));
    } else {
      video.pause();
    }
  };

  return (
    <aside
      aria-label="LalahariHealth phone consultation video"
      aria-hidden={!isVisible}
      className={`fixed bottom-24 left-3 z-[80] w-[min(88vw,22rem)] overflow-hidden rounded-xl border border-black/10 bg-white shadow-2xl transition-all duration-300 sm:bottom-5 sm:left-5 ${
        isVisible ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-4 opacity-0"
      }`}
    >
      {isMinimized ? (
        <div className="flex min-h-14 items-center gap-2 px-3 py-2">
          <button
            type="button"
            onClick={togglePlayback}
            aria-label={isPlaying ? "Pause video" : "Play video with sound"}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-white"
          >
            {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" fill="currentColor" />}
          </button>
          <span className="min-w-0 flex-1 truncate text-sm font-semibold text-ink">LalahariHealth offer</span>
          <button
            type="button"
            onClick={() => setIsMinimized(false)}
            aria-label="Restore video"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-ink/65 hover:bg-primary-light"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={closeVideo}
            aria-label="Close video"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-ink/65 hover:bg-primary-light"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      ) : (
        <>
          <div className="flex min-h-12 items-center justify-between gap-3 px-3 py-2">
            <p className="truncate text-sm font-semibold text-ink">LalahariHealth offer</p>
            <div className="flex shrink-0 items-center gap-1">
              <button
                type="button"
                onClick={() => setIsMinimized(true)}
                aria-label="Minimize video"
                className="flex h-10 w-10 items-center justify-center rounded-full text-ink/65 hover:bg-primary-light"
              >
                <span aria-hidden="true" className="text-xl leading-none">−</span>
              </button>
              <button
                type="button"
                onClick={closeVideo}
                aria-label="Close video"
                className="flex h-10 w-10 items-center justify-center rounded-full text-ink/65 hover:bg-primary-light"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>
          <div className="relative bg-black">
            <video
              ref={videoRef}
              className="aspect-video w-full object-contain"
              src="/videos/sale_video.mp4"
              controls
              playsInline
              preload="none"
              aria-label="LalahariHealth offer video"
              onPlay={() => {
                setIsPlaying(true);
                setAudioAutoplayBlocked(false);
              }}
              onPause={() => setIsPlaying(false)}
              onError={() => setIsPlaying(false)}
            />
            {audioAutoplayBlocked && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/70 p-3 text-center">
                <p className="text-sm font-medium text-white">Tap to play with sound</p>
                <button
                  type="button"
                  onClick={togglePlayback}
                  className="flex min-h-11 items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-bold text-white"
                >
                  <Play className="h-4 w-4" fill="currentColor" /> Play video
                </button>
              </div>
            )}
          </div>
        </>
      )}
      {audioAutoplayBlocked && isMinimized && (
        <p className="px-3 pb-2 text-xs text-ink/55">Tap play to start with sound.</p>
      )}
    </aside>
  );
}