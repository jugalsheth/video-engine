import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND, CAPTION_VIRAL, FONT, SAFE, SPRING_DEFAULT} from '../layout';
import {FONT_BODY, FONT_HEADLINE} from '../fonts';

type Props = {
  text: string;
  subtitle?: string;
  titleVerticalPosition?: number;
  phase?: string;
};

export const TitleCard: React.FC<Props> = ({
  text,
  subtitle = '',
  titleVerticalPosition = 15,
  phase = 'hook',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const isLowerThird = phase === 'crust';
  const entrance = spring({frame, fps, config: SPRING_DEFAULT, durationInFrames: 8});
  const scale = interpolate(entrance, [0, 1], [isLowerThird ? 1.2 : 3, 1]);
  const opacity = interpolate(entrance, [0, 1], [0, 1]);

  return (
    <AbsoluteFill
      style={{
        justifyContent: isLowerThird ? 'flex-end' : 'flex-start',
        alignItems: isLowerThird ? 'flex-start' : 'center',
        paddingTop: isLowerThird ? undefined : `${titleVerticalPosition}%`,
        paddingBottom: isLowerThird ? '22%' : undefined,
        paddingLeft: SAFE.sides,
        paddingRight: SAFE.sides,
        pointerEvents: 'none',
        opacity,
      }}
    >
      <div
        style={{
          transform: `scale(${scale})`,
          width: isLowerThird ? '92%' : '85%',
          maxWidth: FRAME_WIDTH - SAFE.sides * 2,
          backgroundColor: isLowerThird ? BRAND.bg : 'transparent',
          padding: isLowerThird ? '12px 18px' : '20px 28px',
          textAlign: 'center',
        }}
      >
        <h1
          style={{
            margin: 0,
            color: BRAND.text,
            fontFamily: FONT_HEADLINE,
            fontWeight: 400,
            fontSize: FONT.headline + 24,
            lineHeight: 0.95,
            textTransform: 'uppercase',
            letterSpacing: 1,
            textShadow: isLowerThird ? undefined : CAPTION_VIRAL.textShadow,
          }}
        >
          {text}
        </h1>
        {subtitle ? (
          <p
            style={{
              margin: '12px 0 0',
              color: BRAND.cyan,
              fontFamily: FONT_BODY,
              fontSize: FONT.body,
              fontWeight: 700,
              textShadow: isLowerThird ? undefined : CAPTION_VIRAL.textShadow,
            }}
          >
            {subtitle}
          </p>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

const FRAME_WIDTH = 1080;
