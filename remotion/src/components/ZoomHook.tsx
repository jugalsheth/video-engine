import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {ZoomScaleProvider} from '../ZoomScaleContext';
import {SPRING_SNAP} from '../layout';
import type {StepBeat, VideoBeats} from '../types';

type Props = {
  children: React.ReactNode;
  zoomIntensity?: number;
  closerStartFrame?: number;
  totalFrames: number;
  videoBeats?: VideoBeats;
  stepBeats?: StepBeat[];
  closerEndScale?: number;
};

export const ZoomHook: React.FC<Props> = ({
  children,
  zoomIntensity = 1.18,
  closerStartFrame,
  totalFrames,
  videoBeats,
  stepBeats = [],
  closerEndScale,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const hookEnd = videoBeats?.hook_end ?? 32;
  const crustStart = videoBeats?.crust_start ?? hookEnd + 12;
  const setupZoom = videoBeats?.setup_zoom ?? 1.05;
  const crustPeak = videoBeats?.crust_zoom_peak ?? Math.max(zoomIntensity, 1.32);
  const crustSettle = videoBeats?.crust_settle ?? 1.1;

  const snapEnd = 6;
  const holdEnd = 12;
  const easeEnd = 32;

  let scale = 1;

  // Opening snap (frame 0)
  if (frame <= snapEnd) {
    const p = spring({frame, fps, config: SPRING_SNAP, durationInFrames: snapEnd});
    scale = interpolate(p, [0, 1], [1, zoomIntensity]);
  } else if (frame <= holdEnd) {
    scale = zoomIntensity;
  } else if (frame <= easeEnd) {
    const p = spring({
      frame: frame - holdEnd,
      fps,
      config: {damping: 200, stiffness: 100},
      durationInFrames: easeEnd - holdEnd,
    });
    scale = interpolate(p, [0, 1], [zoomIntensity, setupZoom]);
  }
  // Hook setup: hold subtle zoom through promise ("break it down...")
  else if (frame < crustStart) {
    const breathe = Math.sin((frame / fps) * 1.2) * 0.015;
    scale = setupZoom + breathe;
  }
  // Crust punch: aggressive zoom when actual content begins
  else if (frame < crustStart + 10) {
    const p = spring({
      frame: frame - crustStart,
      fps,
      config: SPRING_SNAP,
      durationInFrames: 10,
    });
    scale = interpolate(p, [0, 1], [setupZoom, crustPeak]);
  } else if (frame < crustStart + 22) {
    scale = crustPeak;
  } else if (frame < crustStart + 45) {
    const p = spring({
      frame: frame - (crustStart + 22),
      fps,
      config: {damping: 200, stiffness: 90},
      durationInFrames: 23,
    });
    scale = interpolate(p, [0, 1], [crustPeak, crustSettle]);
  } else if (closerStartFrame && frame >= closerStartFrame) {
    const closerDur = totalFrames - closerStartFrame;
    const p = spring({
      frame: frame - closerStartFrame,
      fps,
      config: {damping: 200, stiffness: 100},
      durationInFrames: Math.min(60, closerDur),
    });
    scale = interpolate(p, [0, 1], [crustSettle, closerEndScale ?? zoomIntensity]);
  } else {
    scale = crustSettle;
  }

  // CapCut step punches: quick snap-zoom on each "step 1/2/3"
  let stepBoost = 0;
  for (const beat of stepBeats) {
    const local = frame - beat.frame;
    if (local < 0 || local > 14) continue;
    const p = spring({
      frame: local,
      fps,
      config: SPRING_SNAP,
      durationInFrames: 9,
    });
    const bump = interpolate(p, [0, 1], [0.1, 0]);
    stepBoost = Math.max(stepBoost, bump);
  }
  scale += stepBoost;

  return (
    <ZoomScaleProvider scale={scale}>
      <AbsoluteFill
        style={{
          transform: `scale(${scale})`,
          transformOrigin: 'center 38%',
        }}
      >
        {children}
      </AbsoluteFill>
    </ZoomScaleProvider>
  );
};
