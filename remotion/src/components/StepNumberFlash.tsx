import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND, SPRING_SNAP} from '../layout';
import {FONT_HEADLINE} from '../fonts';
import type {StepBeat} from '../types';

type Props = {
  beats: StepBeat[];
};

const FLASH_DURATION = 8;

export const StepNumberFlash: React.FC<Props> = ({beats}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  let activeBeat: StepBeat | null = null;
  let localFrame = 0;

  for (const beat of beats) {
    const local = frame - beat.frame;
    if (local >= 0 && local < FLASH_DURATION) {
      activeBeat = beat;
      localFrame = local;
      break;
    }
  }

  if (!activeBeat) return null;

  const scale = spring({
    frame: localFrame,
    fps,
    config: SPRING_SNAP,
    durationInFrames: 6,
  });
  const numScale = interpolate(scale, [0, 1], [2.5, 1]);
  const opacity = interpolate(localFrame, [0, 2, 6, FLASH_DURATION], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        pointerEvents: 'none',
        zIndex: 22,
        opacity,
      }}
    >
      <span
        style={{
          fontFamily: FONT_HEADLINE,
          fontSize: 320,
          fontWeight: 400,
          color: BRAND.amber,
          transform: `scale(${numScale})`,
          textShadow:
            '0 4px 0 #000, 0 0 40px rgba(201,146,58,0.8), 0 0 80px rgba(0,0,0,0.9)',
          lineHeight: 1,
        }}
      >
        {activeBeat.step}
      </span>
    </AbsoluteFill>
  );
};
