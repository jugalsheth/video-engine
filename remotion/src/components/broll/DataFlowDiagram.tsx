import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../../layout';
import {BrollBase} from './BrollBase';

export const DataFlowDiagram: React.FC<{durationFrames: number}> = ({durationFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const line = spring({frame, fps, config: {damping: 200, stiffness: 100}, durationInFrames: 40});
  const dash = interpolate(line, [0, 1], [200, 0]);

  return (
    <BrollBase durationFrames={durationFrames}>
      <svg width="100%" height="140" viewBox="0 0 320 140">
        <circle cx="50" cy="70" r="20" fill={BRAND.cyan} />
        <circle cx="160" cy="70" r="20" fill={BRAND.amber} />
        <circle cx="270" cy="70" r="20" fill={BRAND.cyan} />
        <line x1="70" y1="70" x2="140" y2="70" stroke={BRAND.cyan} strokeWidth="3" strokeDasharray="200" strokeDashoffset={dash} />
        <line x1="180" y1="70" x2="250" y2="70" stroke={BRAND.cyan} strokeWidth="3" strokeDasharray="200" strokeDashoffset={dash} />
        <circle cx={70 + line * 70} cy="70" r="5" fill={BRAND.text} />
      </svg>
    </BrollBase>
  );
};
