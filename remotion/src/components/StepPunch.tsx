import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import type {StepBeat} from '../types';

type Props = {
  beats: StepBeat[];
};

/** CapCut-style micro-flash + streak on each "step 1/2/3" beat */
export const StepPunch: React.FC<Props> = ({beats}) => {
  const frame = useCurrentFrame();

  let flash = 0;
  let streak = 0;
  let ring = 0;

  for (const beat of beats) {
    const local = frame - beat.frame;
    if (local < 0 || local > 12) continue;
    flash = Math.max(
      flash,
      interpolate(local, [0, 1, 3, 12], [0, 0.7, 0.2, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      }),
    );
    streak = Math.max(
      streak,
      interpolate(local, [0, 2, 8], [0, 0.7, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      }),
    );
    ring = Math.max(
      ring,
      interpolate(local, [0, 3, 12], [0.6, 0.35, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      }),
    );
  }

  if (flash <= 0 && streak <= 0) return null;

  return (
    <AbsoluteFill style={{pointerEvents: 'none', zIndex: 25}}>
      <AbsoluteFill
        style={{
          backgroundColor: '#FFFFFF',
          opacity: flash * 0.45,
          mixBlendMode: 'overlay',
        }}
      />
      <AbsoluteFill
        style={{
          background: `linear-gradient(105deg, transparent 38%, rgba(0,212,255,${streak * 0.5}) 50%, transparent 62%)`,
          opacity: streak,
          mixBlendMode: 'screen',
          filter: `blur(${streak * 4}px)`,
        }}
      />
      <AbsoluteFill
        style={{
          boxShadow: `inset 0 0 ${90 * ring}px rgba(0,0,0,${0.5 * ring})`,
        }}
      />
    </AbsoluteFill>
  );
};
