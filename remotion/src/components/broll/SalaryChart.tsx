import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../../layout';
import {BrollBase} from './BrollBase';

export const SalaryChart: React.FC<{durationFrames: number}> = ({durationFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame, fps, config: {damping: 200, stiffness: 100}, durationInFrames: 30});
  const h1 = interpolate(p, [0, 1], [0, 120]);
  const h2 = interpolate(p, [0, 1], [0, 40]);

  return (
    <BrollBase durationFrames={durationFrames}>
      <svg width="100%" height="160" viewBox="0 0 300 160">
        <rect x="60" y={140 - h1} width="60" height={h1} fill={BRAND.cyan} />
        <rect x="180" y={140 - h2} width="60" height={h2} fill={BRAND.amber} />
        <text x="90" y="155" fill={BRAND.text} fontSize="12" textAnchor="middle">Switcher</text>
        <text x="210" y="155" fill={BRAND.text} fontSize="12" textAnchor="middle">Stayer</text>
      </svg>
      <p style={{color: BRAND.text, fontSize: 14, margin: '8px 0 0', textAlign: 'center'}}>
        14-20% vs 3%
      </p>
    </BrollBase>
  );
};
