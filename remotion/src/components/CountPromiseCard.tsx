import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND, CAPTION_VIRAL, SPRING_SNAP} from '../layout';
import {FONT_HEADLINE} from '../fonts';

type Props = {
  text: string;
};

const DURATION_FRAMES = 45;

export const CountPromiseCard: React.FC<Props> = ({text}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  if (frame > DURATION_FRAMES) return null;

  const entrance = spring({frame, fps, config: SPRING_SNAP, durationInFrames: 8});
  const scale = interpolate(entrance, [0, 1], [2.2, 1]);
  const opacity = interpolate(frame, [0, 6, DURATION_FRAMES - 8, DURATION_FRAMES], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        pointerEvents: 'none',
        zIndex: 30,
        opacity,
      }}
    >
      <span
        style={{
          fontFamily: FONT_HEADLINE,
          fontSize: 120,
          fontWeight: 400,
          color: BRAND.amber,
          textTransform: 'uppercase',
          transform: `scale(${scale})`,
          textShadow: CAPTION_VIRAL.textShadow,
          letterSpacing: 2,
        }}
      >
        {text}
      </span>
    </AbsoluteFill>
  );
};
