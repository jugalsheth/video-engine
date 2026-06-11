import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND, SPRING_DEFAULT} from '../../layout';
import {FunBase} from './FunBase';

type Props = {
  text: string;
  durationFrames: number;
  side?: 'left' | 'right' | 'center';
};

export const SpeechBubble: React.FC<Props> = ({text, durationFrames, side = 'right'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: SPRING_DEFAULT, durationInFrames: 14});

  return (
    <FunBase durationFrames={durationFrames} side={side} zone="top">
      <div
        style={{
          position: 'relative',
          backgroundColor: '#FFF8E7',
          color: '#1a1a1a',
          padding: '14px 20px',
          borderRadius: 20,
          border: '3px solid #000',
          fontFamily: 'Comic Sans MS, Chalkboard SE, cursive',
          fontSize: 22,
          fontWeight: 800,
          maxWidth: 280,
          transform: `scale(${pop})`,
          boxShadow: '4px 4px 0 #000',
        }}
      >
        {text}
        <div
          style={{
            position: 'absolute',
            bottom: -14,
            [side === 'left' ? 'left' : 'right']: 24,
            width: 0,
            height: 0,
            borderLeft: '10px solid transparent',
            borderRight: '10px solid transparent',
            borderTop: `14px solid ${BRAND.amber}`,
          }}
        />
      </div>
    </FunBase>
  );
};
