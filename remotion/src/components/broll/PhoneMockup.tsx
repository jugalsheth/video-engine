import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../../layout';
import {BrollBase} from './BrollBase';

export const PhoneMockup: React.FC<{durationFrames: number}> = ({durationFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const badge = spring({frame: frame - 15, fps, config: {damping: 200, stiffness: 120}, durationInFrames: 10});

  return (
    <BrollBase durationFrames={durationFrames}>
      <svg width="100%" height="180" viewBox="0 0 200 180">
        <rect x="50" y="10" width="100" height="160" rx="12" fill="#1a1a1a" stroke={BRAND.cyan} strokeWidth="2" />
        <rect x="60" y="30" width="80" height="100" fill="#0C0B09" />
        <rect x="65" y="40" width="70" height="12" fill={BRAND.text} opacity="0.3" />
        <rect x="65" y="58" width="50" height="8" fill={BRAND.text} opacity="0.2" />
        <circle cx="130" cy="25" r={8 * badge} fill="#ff4444" />
      </svg>
    </BrollBase>
  );
};
