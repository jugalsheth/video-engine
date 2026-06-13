import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import type {GlobalFxMoment} from '../../types';
import {getActiveVhsSegment} from './utils';

type Props = {
  children: React.ReactNode;
  moments: GlobalFxMoment[];
};

export const VHSFilter: React.FC<Props> = ({children, moments}) => {
  const frame = useCurrentFrame();
  const active = getActiveVhsSegment(frame, moments);

  if (!active) {
    return <>{children}</>;
  }

  const localFrame = frame - active.start_frame;
  const scanOffset = (localFrame * 3) % 8;

  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          filter: 'contrast(1.08) saturate(0.75) sepia(0.06)',
        }}
      >
        {children}
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          opacity: 0.08,
          mixBlendMode: 'overlay',
          backgroundImage:
            'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'n\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23n)\'/%3E%3C/svg%3E")',
          backgroundSize: '128px 128px',
          transform: `translateY(${scanOffset}px)`,
        }}
      />
      <AbsoluteFill
        style={{
          opacity: 0.04,
          backgroundImage: `repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(0,0,0,0.3) 2px,
            rgba(0,0,0,0.3) 4px
          )`,
          transform: `translateY(${scanOffset / 2}px)`,
          pointerEvents: 'none',
        }}
      />
    </AbsoluteFill>
  );
};
