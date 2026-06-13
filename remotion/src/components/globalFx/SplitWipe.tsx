import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

type Props = {
  durationFrames: number;
  direction?: 'left-to-right' | 'right-to-left';
};

export const SplitWipe: React.FC<Props> = ({
  durationFrames,
  direction = 'left-to-right',
}) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, durationFrames], [0, 100], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const clipPath =
    direction === 'left-to-right'
      ? `inset(0 ${100 - progress}% 0 0)`
      : `inset(0 0 0 ${100 - progress}%)`;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#0C0B09',
        clipPath,
        zIndex: 30,
        pointerEvents: 'none',
      }}
    />
  );
};
