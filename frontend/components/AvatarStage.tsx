"use client";

import { useEffect, useRef, useState } from "react";

import type { TurnResult } from "@/lib/types";

type AvatarStageProps = {
  personaId: "lee-jieun" | "kim-minseok";
  personaName: string;
  emotion: TurnResult["emotion"];
  videoUrl?: string | null;
  preloadVideoUrl?: string | null;
  playbackKey?: number;
  rendering?: boolean;
  speaking?: boolean;
  preferEmbeddedAudio?: boolean;
  onVideoStart?: (usingEmbeddedAudio: boolean) => void;
  onVideoEnd?: () => void;
  onVideoError?: () => void;
};

const emotionLabel: Record<TurnResult["emotion"], string> = {
  neutral: "차분",
  sad: "슬픔",
  angry: "분노",
  anxious: "불안",
  hurt: "상처",
  withdrawn: "위축",
};

const personaImage = (personaId: AvatarStageProps["personaId"], emotion: TurnResult["emotion"]) => `/personas/${personaId}/${emotion}.png`;

export default function AvatarStage({
  personaId,
  personaName,
  emotion,
  videoUrl,
  preloadVideoUrl,
  playbackKey = 0,
  rendering = false,
  speaking = false,
  preferEmbeddedAudio = true,
  onVideoStart,
  onVideoEnd,
  onVideoError,
}: AvatarStageProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const usingEmbeddedAudioRef = useRef(false);
  const callbacksRef = useRef({ onVideoStart, onVideoEnd, onVideoError });
  const [videoPlaying, setVideoPlaying] = useState(false);

  useEffect(() => {
    callbacksRef.current = { onVideoStart, onVideoEnd, onVideoError };
  }, [onVideoStart, onVideoEnd, onVideoError]);

  useEffect(() => {
    const preload = (["neutral", "sad", "angry", "anxious", "hurt", "withdrawn"] as TurnResult["emotion"][])
      .map(value => {
        const image = new Image();
        image.src = personaImage(personaId, value);
        return image;
      });
    return () => preload.forEach(image => { image.src = ""; });
  }, [personaId]);

  useEffect(() => {
    setVideoPlaying(false);
    if (!videoUrl || !videoRef.current) return;
    const video = videoRef.current;
    let cancelled = false;
    video.currentTime = 0;
    video.muted = !preferEmbeddedAudio;
    usingEmbeddedAudioRef.current = preferEmbeddedAudio;

    const play = () => void video.play().catch(() => {
      // Some browsers block audible autoplay after the asynchronous render.
      // Fall back to a muted video and the separately prepared speech track.
      video.currentTime = 0;
      video.muted = true;
      usingEmbeddedAudioRef.current = false;
      return video.play();
    }).catch(() => {
      setVideoPlaying(false);
      callbacksRef.current.onVideoError?.();
    });

    // The fixed demonstration clip is mounted and buffered on page entry.
    // Do not call load() again when the answer arrives because that discards
    // the existing buffer and is visible as a pause in screen recordings.
    if (video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) {
      play();
    } else {
      const startWhenBuffered = () => {
        if (!cancelled) play();
      };
      video.addEventListener("canplay", startWhenBuffered, { once: true });
      if (video.readyState === HTMLMediaElement.HAVE_NOTHING) video.load();
      return () => {
        cancelled = true;
        video.removeEventListener("canplay", startWhenBuffered);
      };
    }
    return () => { cancelled = true; };
  }, [videoUrl, playbackKey]);

  useEffect(() => {
    if (videoRef.current) videoRef.current.muted = !preferEmbeddedAudio;
  }, [preferEmbeddedAudio]);

  const status = rendering
    ? "표정·입모양 준비 중"
    : videoPlaying
      ? "음성과 입모양 재생 중"
      : speaking
        ? "음성 재생 중"
        : "페르소나 준비됨";

  return (
    <div className={`avatar-stage two-d ${rendering ? "rendering" : ""} ${speaking ? "speaking" : ""}`} aria-busy={rendering}>
      <img
        className={`avatar-photo ${videoPlaying ? "hidden" : ""}`}
        src={personaImage(personaId, emotion)}
        alt={`가상 내담자 ${personaName}의 ${emotionLabel[emotion]} 표정`}
      />
      {(videoUrl || preloadVideoUrl) && (
        <video
          ref={videoRef}
          className={`avatar-video ${videoPlaying ? "visible" : ""}`}
          src={videoUrl ?? preloadVideoUrl ?? undefined}
          playsInline
          preload="auto"
          disablePictureInPicture
          onPlaying={() => {
            setVideoPlaying(true);
            callbacksRef.current.onVideoStart?.(usingEmbeddedAudioRef.current);
          }}
          onEnded={() => {
            setVideoPlaying(false);
            callbacksRef.current.onVideoEnd?.();
          }}
          onError={() => {
            setVideoPlaying(false);
            callbacksRef.current.onVideoError?.();
          }}
        />
      )}
      <div className="avatar-status"><span className="avatar-status-dot" />{status}</div>
      {rendering && (
        <div className="avatar-render-progress" role="status" aria-live="polite">
          <div><span className="avatar-render-spinner" aria-hidden="true" /><b>표정과 입모양을 준비하고 있어요</b></div>
          <i aria-hidden="true" />
          <small>응답 내용은 먼저 확인할 수 있으며, 준비가 끝나면 영상이 자동으로 재생됩니다.</small>
        </div>
      )}
    </div>
  );
}
