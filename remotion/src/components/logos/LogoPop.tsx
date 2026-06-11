import React from 'react';
import {Img, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND, SAFE, SPRING_CAPCUT} from '../../layout';

type Props = {
  logoFile: string;
  label?: string;
  durationFrames: number;
  side?: 'left' | 'right';
};

export const LogoPop: React.FC<Props> = ({
  logoFile,
  label,
  durationFrames,
  side = 'right',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const entrance = spring({frame, fps, config: SPRING_CAPCUT, durationInFrames: 7});
  const exit = spring({
    frame: Math.max(0, frame - (durationFrames - 6)),
    fps,
    config: SPRING_CAPCUT,
    durationInFrames: 5,
  });
  const opacity = frame < durationFrames - 6 ? entrance : 1 - exit;
  const scale = 0.4 + entrance * 0.6;
  const wiggle = Math.sin(frame * 0.85) * (1 - exit) * 6;

  const alignItems = side === 'left' ? 'flex-start' : 'flex-end';

  return (
    <div
      style={{
        position: 'absolute',
        top: SAFE.top + 48,
        left: side === 'left' ? SAFE.sides : undefined,
        right: side === 'right' ? SAFE.sides : undefined,
        display: 'flex',
        flexDirection: 'column',
        alignItems,
        gap: 6,
        opacity,
        transform: `scale(${scale}) rotate(${wiggle * 0.25}deg)`,
        pointerEvents: 'none',
        zIndex: 40,
      }}
    >
      <div
        style={{
          backgroundColor: 'rgba(10, 10, 14, 0.88)',
          border: `2px solid ${BRAND.cyan}`,
          borderRadius: 14,
          padding: '10px 14px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.55)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minWidth: 72,
          minHeight: 72,
        }}
      >
        <Img
          src={staticFile(`logos/${logoFile}`)}
          style={{
            width: 52,
            height: 52,
            objectFit: 'contain',
            filter:
              'brightness(0) invert(1) drop-shadow(0 2px 4px rgba(0,0,0,0.4))',
          }}
        />
      </div>
      {label ? (
        <span
          style={{
            fontFamily: 'system-ui, -apple-system, sans-serif',
            fontSize: 11,
            fontWeight: 800,
            letterSpacing: 0.6,
            textTransform: 'uppercase',
            color: BRAND.cyan,
            textShadow: '0 2px 6px rgba(0,0,0,0.9)',
          }}
        >
          {label}
        </span>
      ) : null}
    </div>
  );
};
