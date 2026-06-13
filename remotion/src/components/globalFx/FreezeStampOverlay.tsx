import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND, SPRING_SNAP} from '../../layout';
import {FONT_HEADLINE} from '../../fonts';

type Props = {
  stampText: string;
  durationFrames: number;
};

export const FreezeStampOverlay: React.FC<Props> = ({stampText, durationFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const scale = spring({
    frame,
    fps,
    config: SPRING_SNAP,
    durationInFrames: 8,
  });
  const numScale = interpolate(scale, [0, 1], [1.4, 1]);
  const rotate = interpolate(scale, [0, 1], [-3, 0]);
  const opacity = interpolate(frame, [0, 3, durationFrames - 4, durationFrames], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        pointerEvents: 'none',
        opacity,
        zIndex: 25,
      }}
    >
      <span
        style={{
          fontFamily: FONT_HEADLINE,
          fontSize: 180,
          fontWeight: 400,
          color: BRAND.amber,
          transform: `scale(${numScale}) rotate(${rotate}deg)`,
          textShadow:
            '0 4px 0 #000, 0 0 24px rgba(201,146,58,0.6), 0 0 8px rgba(0,0,0,0.95)',
        }}
      >
        {stampText}
      </span>
    </AbsoluteFill>
  );
};
