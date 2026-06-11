import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND, SPRING_DEFAULT} from '../../layout';
import {FunBase} from './FunBase';

type Props = {
  durationFrames: number;
  side?: 'left' | 'right' | 'center';
};

export const DoodleArrow: React.FC<Props> = ({durationFrames, side = 'left'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const draw = spring({frame, fps, config: SPRING_DEFAULT, durationInFrames: 20});
  const dash = interpolate(draw, [0, 1], [120, 0]);

  return (
    <FunBase durationFrames={durationFrames} side={side} zone="mid">
      <svg width="200" height="120" viewBox="0 0 200 120" style={{overflow: 'visible'}}>
        <path
          d={side === 'left' ? 'M20,60 Q80,20 140,50 L170,40' : 'M180,60 Q120,20 60,50 L30,40'}
          fill="none"
          stroke={BRAND.cyan}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray="120"
          strokeDashoffset={dash}
        />
        <polygon
          points={side === 'left' ? '170,40 155,35 160,50' : '30,40 45,35 40,50'}
          fill={BRAND.cyan}
          opacity={draw}
        />
      </svg>
    </FunBase>
  );
};
