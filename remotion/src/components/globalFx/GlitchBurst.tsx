import React from 'react';
import {AbsoluteFill, random, useCurrentFrame} from 'remotion';
import type {GlobalFxMoment} from '../../types';
import {getActiveGlobalFx} from './utils';

type Props = {
  children: React.ReactNode;
  moments: GlobalFxMoment[];
  defaultIntensity?: number;
};

export const GlitchBurst: React.FC<Props> = ({
  children,
  moments,
  defaultIntensity = 0.6,
}) => {
  const frame = useCurrentFrame();
  const active = getActiveGlobalFx(frame, moments, 'glitch_burst');

  if (!active) {
    return <>{children}</>;
  }

  const intensity = active.intensity ?? defaultIntensity;
  const offset = intensity * 4;
  const seed = `glitch-${active.start_frame}`;
  const jitter = (random(seed) - 0.5) * 2;

  return (
    <AbsoluteFill>
      <svg width="0" height="0" style={{position: 'absolute'}}>
        <defs>
          <filter id={`glitch-r-${active.start_frame}`}>
            <feColorMatrix
              type="matrix"
              values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"
            />
            <feOffset dx={offset + jitter} result="red" />
          </filter>
          <filter id={`glitch-g-${active.start_frame}`}>
            <feColorMatrix
              type="matrix"
              values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0"
            />
          </filter>
          <filter id={`glitch-b-${active.start_frame}`}>
            <feColorMatrix
              type="matrix"
              values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0"
            />
            <feOffset dx={-(offset + jitter)} result="blue" />
          </filter>
          <filter id={`glitch-blur-${active.start_frame}`}>
            <feGaussianBlur stdDeviation="1.5" />
          </filter>
        </defs>
      </svg>
      <AbsoluteFill style={{filter: `url(#glitch-blur-${active.start_frame})`}}>
        <AbsoluteFill
          style={{
            filter: `url(#glitch-r-${active.start_frame})`,
            mixBlendMode: 'screen',
          }}
        >
          {children}
        </AbsoluteFill>
        <AbsoluteFill style={{mixBlendMode: 'screen'}}>{children}</AbsoluteFill>
        <AbsoluteFill
          style={{
            filter: `url(#glitch-b-${active.start_frame})`,
            mixBlendMode: 'screen',
          }}
        >
          {children}
        </AbsoluteFill>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
