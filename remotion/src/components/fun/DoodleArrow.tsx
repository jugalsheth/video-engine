import React from 'react';
import {evolvePath, getLength} from '@remotion/paths';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND, SPRING_DEFAULT} from '../../layout';
import {FunBase} from './FunBase';

type Props = {
  durationFrames: number;
  side?: 'left' | 'right' | 'center';
};

const LEFT_PATH = 'M20,60 Q80,20 140,50 L170,40';
const RIGHT_PATH = 'M180,60 Q120,20 60,50 L30,40';

export const DoodleArrow: React.FC<Props> = ({durationFrames, side = 'left'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const path = side === 'left' ? LEFT_PATH : RIGHT_PATH;
  getLength(path);
  const draw = spring({frame, fps, config: SPRING_DEFAULT, durationInFrames: 12});
  const progress = interpolate(draw, [0, 1], [0, 1], {extrapolateRight: 'clamp'});
  const {strokeDasharray, strokeDashoffset} = evolvePath(progress, path);
  const headOpacity = interpolate(frame, [8, 12], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <FunBase durationFrames={durationFrames} side={side} zone="mid">
      <svg width="200" height="120" viewBox="0 0 200 120" style={{overflow: 'visible'}}>
        <path
          d={path}
          fill="none"
          stroke={BRAND.cyan}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
        />
        <polygon
          points={side === 'left' ? '170,40 155,35 160,50' : '30,40 45,35 40,50'}
          fill={BRAND.cyan}
          opacity={headOpacity}
        />
      </svg>
    </FunBase>
  );
};
