import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import type {StepBeat} from '../types';

type Props = {
  stepBeats?: StepBeat[];
};

const STEP_PULSE_WINDOW = 45;
const BASE_VIGNETTE = 0.22;
const PULSE_BOOST = 0.18;

export const PostFX: React.FC<Props> = ({stepBeats = []}) => {
  const frame = useCurrentFrame();

  let pulse = 0;
  for (const beat of stepBeats) {
    const local = frame - beat.frame;
    if (local >= -STEP_PULSE_WINDOW && local <= STEP_PULSE_WINDOW) {
      const p = interpolate(
        Math.abs(local),
        [0, STEP_PULSE_WINDOW],
        [1, 0],
        {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
      );
      pulse = Math.max(pulse, p);
    }
  }

  const vignetteStrength = BASE_VIGNETTE + pulse * PULSE_BOOST;

  return (
    <AbsoluteFill
      style={{
        pointerEvents: 'none',
        background: `radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,${vignetteStrength}) 100%)`,
        mixBlendMode: 'multiply',
      }}
    />
  );
};
