import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {useOverlayScale} from '../../OverlayScaleContext';
import {BRAND, OVERLAY_BASE, overlaySize, SPRING_SNAP} from '../../layout';
import {FunBase} from './FunBase';

type Props = {
  text: string;
  durationFrames: number;
  side?: 'left' | 'right' | 'center';
  mood?: string;
};

export const ComicSFX: React.FC<Props> = ({
  text,
  durationFrames,
  side = 'right',
  mood = 'medium',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const scale = useOverlayScale();
  const fontSize = overlaySize(
    mood === 'chaos' ? OVERLAY_BASE.comicSfxFontChaos : OVERLAY_BASE.comicSfxFont,
    scale,
  );
  const slam = spring({frame, fps, config: SPRING_SNAP, durationInFrames: 8});
  const shake = interpolate(slam, [0, 0.5, 1], [0, mood === 'chaos' ? 12 : 6, 0]);
  const rot = interpolate(slam, [0, 1], [-8, 0]);

  return (
    <FunBase durationFrames={durationFrames} side={side}>
      <div
        style={{
          transform: `translateX(${shake * (side === 'left' ? -1 : 1)}px) rotate(${rot}deg) scale(${0.5 + slam * 0.5})`,
          color: BRAND.amber,
          fontFamily: 'Impact, Haettenschweiler, sans-serif',
          fontSize,
          fontWeight: 900,
          WebkitTextStroke: '3px #000',
          textShadow: '4px 4px 0 #000, 0 0 20px rgba(201,146,58,0.6)',
          letterSpacing: 2,
        }}
      >
        {text}
      </div>
    </FunBase>
  );
};
