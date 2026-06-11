import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../../layout';
import {BrollBase} from './BrollBase';

export const GrowthChart: React.FC<{durationFrames: number}> = ({durationFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame, fps, config: {damping: 200, stiffness: 100}, durationInFrames: 35});
  const pathLen = interpolate(p, [0, 1], [0, 1]);

  return (
    <BrollBase durationFrames={durationFrames}>
      <svg width="100%" height="140" viewBox="0 0 300 140">
        <polyline
          points="30,110 80,90 130,70 180,50 230,30 270,20"
          fill="none"
          stroke={BRAND.cyan}
          strokeWidth="4"
          strokeDasharray="400"
          strokeDashoffset={400 * (1 - pathLen)}
        />
        {[30, 80, 130, 180, 230, 270].map((x, i) => (
          <circle
            key={x}
            cx={x}
            cy={[110, 90, 70, 50, 30, 20][i]}
            r={p > i * 0.15 ? 6 : 0}
            fill={BRAND.amber}
          />
        ))}
      </svg>
    </BrollBase>
  );
};
