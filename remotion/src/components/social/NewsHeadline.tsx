import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND, FONT, OVERLAY_LEGIBLE, SAFE, SPRING_SNAP} from '../../layout';

export type HeadlineProps = {
  source: string;
  headline: string;
  subheadline?: string;
};

export const NewsHeadline: React.FC<HeadlineProps> = ({source, headline, subheadline}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config: SPRING_SNAP, durationInFrames: 14});
  const scale = interpolate(enter, [0, 1], [0.92, 1]);
  const opacity = interpolate(frame, [0, 8], [0, 1], {extrapolateRight: 'clamp'});

  return (
    <div
      style={{
        paddingLeft: SAFE.sides,
        paddingRight: SAFE.sides,
        paddingTop: SAFE.top + 60,
        opacity,
        transform: `scale(${scale})`,
      }}
    >
      <div
        style={{
          backgroundColor: OVERLAY_LEGIBLE.pillBg,
          border: OVERLAY_LEGIBLE.pillBorder,
          borderRadius: 12,
          padding: '28px 32px',
          boxShadow: OVERLAY_LEGIBLE.boxShadow,
        }}
      >
        <div
          style={{
            color: BRAND.amber,
            fontSize: FONT.label,
            fontWeight: 800,
            letterSpacing: 2,
            textTransform: 'uppercase',
            marginBottom: 12,
          }}
        >
          {source}
        </div>
        <h2
          style={{
            color: BRAND.text,
            fontSize: FONT.headline - 4,
            fontWeight: 900,
            lineHeight: 1.15,
            margin: 0,
            textShadow: OVERLAY_LEGIBLE.textShadow,
          }}
        >
          {headline}
        </h2>
        {subheadline ? (
          <p
            style={{
              color: 'rgba(245,240,232,0.75)',
              fontSize: FONT.body - 4,
              marginTop: 14,
              marginBottom: 0,
              lineHeight: 1.3,
            }}
          >
            {subheadline}
          </p>
        ) : null}
      </div>
    </div>
  );
};
