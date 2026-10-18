"use client";

import { useEffect, useRef, useState } from "react";

const UNLOCK_EVENTS = ["pointerdown", "touchend", "keydown"] as const;

export function SaleVideo() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playbackError, setPlaybackError] = useState<string | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    let visible = false;
    let disposed = false;
    let audioAllowed = false;
    let userMuted = false;
    let expectedMuted = video.muted;

    const setMuted = (muted: boolean) => {
      expectedMuted = muted;
      video.muted = muted;
    };

    const isAbort = (error: unknown) => error instanceof DOMException && error.name === "AbortError";
    const isBlocked = (error: unknown) => error instanceof DOMException && error.name === "NotAllowedError";

    const removeUnlockListeners = () => {
      UNLOCK_EVENTS.forEach((name) => document.removeEventListener(name, unlockAudio, true));
    };

    function unlockAudio() {
      audioAllowed = true;
      removeUnlockListeners();
      if (!userMuted) setMuted(false);
      updatePlayback();
    }

    function updatePlayback() {
      if (!visible || document.hidden) {
        video!.pause();
        return;
      }

      setMuted(userMuted);
      video!.play().then(() => setPlaybackError(null)).catch((error: unknown) => {
        if (disposed || !visible || document.hidden || isAbort(error)) return;
        if (!isBlocked(error) || video!.muted) {
          setPlaybackError("Video could not start automatically. Use the video controls to play.");
          return;
        }
        if (!audioAllowed) {
          UNLOCK_EVENTS.forEach((name) => document.addEventListener(name, unlockAudio, true));
        }
        setMuted(true);
        video!.play().catch((mutedError: unknown) => {
          if (disposed || !visible || document.hidden || isAbort(mutedError)) return;
          setPlaybackError("Video could not start automatically. Use the video controls to play.");
        });
      });
    }

    const onVolumeChange = () => {
      // volumechange is async; ignore states set by this component.
      if (video.muted === expectedMuted) return;
      expectedMuted = video.muted;
      userMuted = video.muted;
      if (!video.muted) {
        audioAllowed = true;
        removeUnlockListeners();
      }
    };

    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting && entry.intersectionRatio >= 0.15;
      updatePlayback();
    }, { threshold: [0, 0.15] });

    observer.observe(video);
    video.addEventListener("volumechange", onVolumeChange);
    document.addEventListener("visibilitychange", updatePlayback);

    return () => {
      disposed = true;
      observer.disconnect();
      removeUnlockListeners();
      video.removeEventListener("volumechange", onVolumeChange);
      document.removeEventListener("visibilitychange", updatePlayback);
      video.pause();
    };
  }, []);

  return (
    <div id="sale_video" className="overflow-hidden rounded-[2rem] border border-black/5 bg-white shadow-[0_32px_90px_rgba(15,23,42,0.10)]">
      <video
        ref={videoRef}
        src="/videos/sale_video.mp4"
        loop
        playsInline
        controls
        preload="auto"
        className="aspect-[4/5] w-full bg-black object-cover"
        aria-label="LalahariHealth doctor consultation overview video"
        onPlay={() => setPlaybackError(null)}
        onError={() => setPlaybackError("The video could not be loaded. Please reload the page to try again.")}
      />
      {playbackError && <p role="status" className="p-4 text-sm text-ink">{playbackError}</p>}
    </div>
  );
}