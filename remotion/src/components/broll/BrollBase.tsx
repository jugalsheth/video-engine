import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BROLL_ZONE_TOP, BRAND, SAFE, SPRING_DEFAULT} from '../../layout';

type Props = {
  children: React.ReactNode;
  durationFrames: number;
};

export const BrollBase: React.FC<Props> = ({children, durationFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const fadeIn = spring({frame, fps, config: SPRING_DEFAULT, durationInFrames: 12});
  const fadeOut = spring({
    frame: Math.max(0, frame - (durationFrames - 12)),
    fps,
    config: SPRING_DEFAULT,
    durationInFrames: 12,
  });
  const opacity = frame < durationFrames - 12 ? fadeIn : 1 - fadeOut;

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-start',
        alignItems: 'center',
        paddingTop: '38%',
        paddingLeft: SAFE.sides,
        paddingRight: SAFE.sides,
        pointerEvents: 'none',
        opacity,
      }}
    >
      <div
        style={{
          width: '90%',
          backgroundColor: BRAND.bg,
          padding: 16,
          borderRadius: 4,
        }}
      >
        {children}
      </div>
    </AbsoluteFill>
  );
};
