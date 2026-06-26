import React from 'react';
import {Img, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT, OVERLAY_LEGIBLE, SAFE, SPRING_SNAP} from '../../layout';

const PANEL_WIDTH = 1080 - SAFE.sides * 2;

export type TweetProps = {
  handle: string;
  display_name: string;
  text: string;
  verified?: boolean;
  avatar_file?: string;
};

export const FakeTweet: React.FC<TweetProps> = ({
  handle,
  display_name,
  text,
  verified = false,
  avatar_file,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config: SPRING_SNAP, durationInFrames: 16});
  const y = interpolate(enter, [0, 1], [40, 0]);
  const opacity = interpolate(frame, [0, 10], [0, 1], {extrapolateRight: 'clamp'});
  const normalizedHandle = handle.startsWith('@') ? handle : `@${handle}`;

  return (
    <div
      style={{
        width: PANEL_WIDTH,
        paddingLeft: SAFE.sides,
        paddingRight: SAFE.sides,
        paddingTop: SAFE.top + 40,
        opacity,
        transform: `translateY(${y}px)`,
      }}
    >
      <div
        style={{
          backgroundColor: '#15202b',
          borderRadius: 16,
          padding: 24,
          border: '1px solid rgba(255,255,255,0.08)',
          boxShadow: OVERLAY_LEGIBLE.boxShadow,
          fontFamily: 'system-ui, -apple-system, sans-serif',
        }}
      >
        <div style={{display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16}}>
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: '50%',
              overflow: 'hidden',
              flexShrink: 0,
              background: 'linear-gradient(135deg, #1d9bf0, #7856ff)',
            }}
          >
            {avatar_file ? (
              <Img src={avatar_file} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
            ) : null}
          </div>
          <div>
            <div style={{display: 'flex', alignItems: 'center', gap: 6}}>
              <span style={{color: '#fff', fontWeight: 700, fontSize: FONT.body}}>
                {display_name}
              </span>
              {verified && (
                <span style={{color: '#1d9bf0', fontSize: 20}}>✓</span>
              )}
            </div>
            <span style={{color: '#8b98a5', fontSize: FONT.label}}>{normalizedHandle}</span>
          </div>
        </div>
        <p
          style={{
            color: '#e7e9ea',
            fontSize: FONT.body + 2,
            lineHeight: 1.35,
            margin: 0,
            whiteSpace: 'pre-wrap',
          }}
        >
          {text}
        </p>
      </div>
    </div>
  );
};
