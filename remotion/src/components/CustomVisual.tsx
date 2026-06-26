import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND, FRAME, OVERLAY_LEGIBLE, SAFE, SPRING_SNAP} from '../layout';

type Props = {
  description: string;
  assetPath: string;
  assetStatus: string;
  assetFilename?: string;
  layout?: 'hero' | 'corner';
};

export const CustomVisual: React.FC<Props> = ({
  assetPath,
  assetStatus,
  assetFilename,
  layout = 'hero',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  if (assetStatus !== 'ready') {
    return null;
  }

  const base = assetPath.replace(/\/$/, '');
  const filename =
    assetFilename ||
    (['asset.png', 'asset.jpg', 'asset.webp', 'visual.png'].find(Boolean) ?? 'asset.png');

  const enter = spring({frame, fps, config: SPRING_SNAP, durationInFrames: 14});
  const scale = interpolate(enter, [0, 1], [0.88, 1]);
  const opacity = interpolate(frame, [0, 8], [0, 1], {extrapolateRight: 'clamp'});

  const isHero = layout !== 'corner';
  const panelWidth = isHero ? FRAME.width - SAFE.sides * 2 : Math.round(FRAME.width * 0.88);
  const imageMaxHeight = isHero ? 920 : 640;

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-start',
        alignItems: 'center',
        pointerEvents: 'none',
        paddingTop: isHero ? SAFE.top + 24 : '28%',
      }}
    >
      <div
        style={{
          width: panelWidth,
          backgroundColor: OVERLAY_LEGIBLE.pillBg,
          borderRadius: 16,
          padding: isHero ? 20 : 14,
          border: OVERLAY_LEGIBLE.pillBorder,
          boxShadow: OVERLAY_LEGIBLE.boxShadow,
          transform: `scale(${scale})`,
          opacity,
        }}
      >
        <Img
          src={staticFile(`${base}/${filename}`)}
          style={{
            width: '100%',
            maxHeight: imageMaxHeight,
            objectFit: 'contain',
            display: 'block',
            borderRadius: 8,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
