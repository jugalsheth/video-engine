import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

type Props = {
  crustStartFrame: number;
};

/** Brief flash + vignette punch when content "crust" begins after hook pause */
export const CrustFlash: React.FC<Props> = ({crustStartFrame}) => {
  const frame = useCurrentFrame();
  const local = frame - crustStartFrame;
  if (local < 0 || local > 14) return null;

  const flash = interpolate(local, [0, 1, 4, 14], [0, 0.65, 0.2, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const ring = interpolate(local, [0, 4, 14], [0.8, 0.5, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <AbsoluteFill
        style={{
          backgroundColor: '#FFFFFF',
          opacity: flash * 0.5,
          mixBlendMode: 'overlay',
        }}
      />
      <AbsoluteFill
        style={{
          backgroundColor: '#00D4FF',
          opacity: flash * 0.2,
          mixBlendMode: 'screen',
        }}
      />
      <AbsoluteFill
        style={{
          boxShadow: `inset 0 0 ${120 * ring}px rgba(0,0,0,${0.65 * ring})`,
        }}
      />
    </AbsoluteFill>
  );
};
