import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {SAFE, SPRING_DEFAULT, SPRING_SNAP} from '../../layout';

type Props = {
  children: React.ReactNode;
  durationFrames: number;
  side?: 'left' | 'right';
  isCallback?: boolean;
};

export const RoleBase: React.FC<Props> = ({
  children,
  durationFrames,
  side = 'left',
  isCallback = false,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const entrance = spring({
    frame,
    fps,
    config: isCallback ? SPRING_SNAP : SPRING_DEFAULT,
    durationInFrames: 14,
  });
  const exit = spring({
    frame: Math.max(0, frame - (durationFrames - 12)),
    fps,
    config: SPRING_DEFAULT,
    durationInFrames: 12,
  });
  const opacity = frame < durationFrames - 12 ? entrance : 1 - exit;
  const slideX = (1 - entrance) * (side === 'left' ? -120 : 120);
  const bounce = Math.sin(frame * 0.25) * 6 * entrance * (1 - exit);

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-end',
        alignItems: side === 'left' ? 'flex-start' : 'flex-end',
        paddingBottom: SAFE.bottom + 40,
        paddingLeft: SAFE.sides,
        paddingRight: SAFE.sides,
        pointerEvents: 'none',
        opacity,
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: side === 'left' ? 'flex-start' : 'flex-end',
          transform: `translateX(${slideX}px) translateY(${bounce}px) scale(${0.85 + entrance * 0.15})`,
          transformOrigin: side === 'left' ? 'bottom left' : 'bottom right',
        }}
      >
        {children}
      </div>
    </AbsoluteFill>
  );
};
