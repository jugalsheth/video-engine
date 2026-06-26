import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT, OVERLAY_LEGIBLE, SAFE, SPRING_SNAP} from '../../layout';

export type ReactionProps = {
  emoji: string;
  label?: string;
  image_file?: string;
};

export const ReactionCutaway: React.FC<ReactionProps> = ({emoji, label}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config: SPRING_SNAP, durationInFrames: 10});
  const scale = interpolate(enter, [0, 1], [0.4, 1.15]);
  const settle = interpolate(frame, [12, 22], [1.15, 1], {extrapolateRight: 'clamp'});
  const finalScale = frame < 12 ? scale : settle;
  const opacity = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        paddingTop: SAFE.top + 200,
        opacity,
        transform: `scale(${finalScale})`,
      }}
    >
      <div style={{fontSize: 160, lineHeight: 1, filter: 'drop-shadow(0 8px 24px rgba(0,0,0,0.6))'}}>
        {emoji}
      </div>
      {label ? (
        <div
          style={{
            marginTop: 24,
            fontSize: FONT.headline,
            fontWeight: 900,
            color: '#F5F0E8',
            textTransform: 'uppercase',
            letterSpacing: 2,
            textShadow: OVERLAY_LEGIBLE.textShadow,
            textAlign: 'center',
            paddingLeft: SAFE.sides,
            paddingRight: SAFE.sides,
          }}
        >
          {label}
        </div>
      ) : null}
    </div>
  );
};
