import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../../layout';
import {BrollBase} from './BrollBase';

export const NeuralNetwork: React.FC<{durationFrames: number}> = ({durationFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame, fps, config: {damping: 200, stiffness: 100}, durationInFrames: 20});
  const pulse = interpolate(frame % 30, [0, 15, 30], [0.3, 1, 0.3]);

  const layers = [[50, 70], [160, 50], [160, 90], [270, 70]];

  return (
    <BrollBase durationFrames={durationFrames}>
      <svg width="100%" height="140" viewBox="0 0 320 140" opacity={p}>
        {layers.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="14" fill={BRAND.cyan} opacity={pulse} />
        ))}
        <line x1="64" y1="70" x2="146" y2="50" stroke={BRAND.cyan} strokeWidth="2" opacity={pulse} />
        <line x1="64" y1="70" x2="146" y2="90" stroke={BRAND.cyan} strokeWidth="2" opacity={pulse} />
        <line x1="174" y1="50" x2="256" y2="70" stroke={BRAND.amber} strokeWidth="2" opacity={pulse} />
        <line x1="174" y1="90" x2="256" y2="70" stroke={BRAND.amber} strokeWidth="2" opacity={pulse} />
      </svg>
    </BrollBase>
  );
};
