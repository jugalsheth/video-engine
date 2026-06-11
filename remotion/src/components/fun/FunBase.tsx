import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {SAFE, SPRING_CAPCUT} from '../../layout';

type Props = {
  children: React.ReactNode;
  durationFrames: number;
  side?: 'left' | 'right' | 'center';
  zone?: 'top' | 'corner' | 'mid';
};

export const FunBase: React.FC<Props> = ({
  children,
  durationFrames,
  side = 'right',
  zone = 'corner',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const entrance = spring({frame, fps, config: SPRING_CAPCUT, durationInFrames: 6});
  const exit = spring({
    frame: Math.max(0, frame - (durationFrames - 6)),
    fps,
    config: SPRING_CAPCUT,
    durationInFrames: 5,
  });
  const opacity = frame < durationFrames - 6 ? entrance : 1 - exit;
  const scale = 0.35 + entrance * 0.65;
  const wiggle = Math.sin(frame * 0.9) * (1 - exit) * 8;

  const alignItems =
    side === 'left' ? 'flex-start' : side === 'right' ? 'flex-end' : 'center';
  const paddingTop =
    zone === 'top' ? '28%' : zone === 'mid' ? '45%' : SAFE.top + 20;

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-start',
        alignItems,
        paddingTop,
        paddingLeft: SAFE.sides,
        paddingRight: SAFE.sides,
        pointerEvents: 'none',
        opacity,
        transform: `scale(${scale}) rotate(${wiggle * 0.3}deg)`,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
