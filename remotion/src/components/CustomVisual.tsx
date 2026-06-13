import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {BRAND, FONT, OVERLAY_LEGIBLE, SAFE} from '../layout';
import {FONT_BODY, FONT_HEADLINE} from '../fonts';

type Props = {
  description: string;
  assetPath: string;
  assetStatus: string;
};

export const CustomVisual: React.FC<Props> = ({description, assetPath, assetStatus}) => {
  if (assetStatus !== 'ready') {
    return null;
  }

  const candidates = ['asset.png', 'asset.jpg', 'asset.webp', 'visual.png', 'visual.mp4'];
  const base = assetPath.replace(/\/$/, '');

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          position: 'absolute',
          right: SAFE.horizontal,
          top: '28%',
          maxWidth: '42%',
          backgroundColor: OVERLAY_LEGIBLE.background,
          borderRadius: 12,
          padding: 16,
          border: `2px solid ${BRAND.cyan}`,
          boxShadow: '0 8px 32px rgba(0,0,0,0.45)',
        }}
      >
        {candidates.map((name) => (
          <Img
            key={name}
            src={staticFile(`${base}/${name}`)}
            style={{
              maxWidth: '100%',
              maxHeight: 280,
              objectFit: 'contain',
              display: 'block',
            }}
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
        ))}
        {description ? (
          <p
            style={{
              margin: '8px 0 0',
              fontFamily: FONT_BODY,
              fontSize: FONT.caption,
              color: BRAND.white,
              textAlign: 'center',
            }}
          >
            {description}
          </p>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
