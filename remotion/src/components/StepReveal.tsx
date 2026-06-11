import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {BRAND, FONT, OVERLAY_LEGIBLE, SAFE, SPRING_STEP} from '../layout';

type Props = {
  stepNumber: number;
  text: string;
};

export const StepReveal: React.FC<Props> = ({stepNumber, text}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const slide = spring({frame, fps, config: SPRING_STEP, durationInFrames: 14});
  const translateX = interpolate(slide, [0, 1], [-100, 0]);
  const opacity = interpolate(slide, [0, 1], [0, 1]);
  const lineHeight = interpolate(slide, [0, 1], [0, 60 + (stepNumber - 1) * 78]);

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-start',
        alignItems: 'flex-start',
        paddingTop: SAFE.top + 80,
        paddingLeft: SAFE.sides,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: SAFE.sides + 23,
          top: SAFE.top + 60,
          width: 2,
          height: lineHeight,
          backgroundColor: BRAND.cyan,
          opacity: 0.85,
          boxShadow: '0 0 8px rgba(0,212,255,0.45)',
        }}
      />
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          opacity,
          transform: `translateX(${translateX}px)`,
          marginTop: (stepNumber - 1) * 78,
          maxWidth: 920,
        }}
      >
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: '50%',
            backgroundColor: BRAND.cyan,
            color: '#0a0a0e',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            fontSize: 24,
            fontWeight: 900,
            flexShrink: 0,
            boxShadow: OVERLAY_LEGIBLE.boxShadow,
            border: OVERLAY_LEGIBLE.pillBorder,
          }}
        >
          {stepNumber}
        </div>
        <div
          style={{
            backgroundColor: OVERLAY_LEGIBLE.pillBg,
            border: OVERLAY_LEGIBLE.pillBorder,
            borderRadius: 12,
            padding: '12px 18px',
            boxShadow: OVERLAY_LEGIBLE.boxShadow,
            backdropFilter: 'blur(6px)',
            WebkitBackdropFilter: 'blur(6px)',
            flex: 1,
          }}
        >
          <p
            style={{
              margin: 0,
              color: BRAND.text,
              fontFamily: 'system-ui, -apple-system, sans-serif',
              fontSize: FONT.step,
              fontWeight: 800,
              lineHeight: 1.2,
              letterSpacing: 0.4,
              textTransform: 'uppercase',
              textShadow: OVERLAY_LEGIBLE.textShadow,
            }}
          >
            {text}
          </p>
        </div>
      </div>
    </AbsoluteFill>
  );
};
