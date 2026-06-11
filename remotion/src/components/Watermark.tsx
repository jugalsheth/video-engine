import React from 'react';
import {AbsoluteFill} from 'remotion';
import {BRAND, SAFE} from '../layout';
import {FONT_BODY} from '../fonts';

type Props = {
  handle: string;
  opacity?: number;
};

export const Watermark: React.FC<Props> = ({handle, opacity = 0.45}) => {
  if (!handle) return null;

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-end',
        alignItems: 'flex-start',
        paddingBottom: SAFE.bottom - 40,
        paddingLeft: SAFE.sides,
        pointerEvents: 'none',
        zIndex: 50,
      }}
    >
      <span
        style={{
          fontFamily: FONT_BODY,
          fontSize: 26,
          fontWeight: 600,
          color: BRAND.text,
          opacity,
          textShadow: '0 1px 4px rgba(0,0,0,0.9)',
          letterSpacing: 0.5,
        }}
      >
        {handle}
      </span>
    </AbsoluteFill>
  );
};
