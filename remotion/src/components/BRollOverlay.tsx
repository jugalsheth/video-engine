import React from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame} from 'remotion';

type Props = {
  src: string;
  durationFrames: number;
};

export const BRollOverlay: React.FC<Props> = ({src, durationFrames}) => {
  const frame = useCurrentFrame();
  const fadeInEnd = Math.min(12, Math.floor(durationFrames * 0.2));
  const fadeOutStart = Math.max(durationFrames - 12, fadeInEnd + 1);

  const opacity = interpolate(
    frame,
    [0, fadeInEnd, fadeOutStart, durationFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-start',
        alignItems: 'flex-end',
        paddingTop: 100,
        paddingRight: 40,
        pointerEvents: 'none',
      }}
    >
      <Img
        src={src}
        style={{
          width: '28%',
          opacity,
          objectFit: 'contain',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        }}
      />
    </AbsoluteFill>
  );
};
