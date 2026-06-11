import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND, SPRING_DEFAULT} from '../../layout';
import {FunBase} from './FunBase';

type Props = {
  durationFrames: number;
  side?: 'left' | 'right' | 'center';
};

export const QuestionBounce: React.FC<Props> = ({durationFrames, side = 'right'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const bounce = spring({frame, fps, config: SPRING_DEFAULT, durationInFrames: 14});
  const y = Math.sin(frame * 0.3) * 12 * bounce;

  return (
    <FunBase durationFrames={durationFrames} side={side}>
      <div
        style={{
          fontSize: 80,
          color: BRAND.cyan,
          transform: `translateY(${y}px) scale(${bounce})`,
          WebkitTextStroke: '2px #000',
        }}
      >
        ?
      </div>
    </FunBase>
  );
};
