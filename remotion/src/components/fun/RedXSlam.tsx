import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {SPRING_SNAP} from '../../layout';
import {FunBase} from './FunBase';

type Props = {
  durationFrames: number;
  side?: 'left' | 'right' | 'center';
};

export const RedXSlam: React.FC<Props> = ({durationFrames, side = 'left'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const slam = spring({frame, fps, config: SPRING_SNAP, durationInFrames: 10});
  const shake = interpolate(slam, [0, 0.5, 1], [0, 10, 0]);

  return (
    <FunBase durationFrames={durationFrames} side={side}>
      <div
        style={{
          fontSize: 100,
          transform: `scale(${slam}) rotate(${-15 + slam * 15}deg) translateX(${shake}px)`,
          filter: 'drop-shadow(0 0 12px rgba(255,0,0,0.5))',
        }}
      >
        ❌
      </div>
    </FunBase>
  );
};
