import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {BRAND} from '../../layout';

type Props = {
  durationFrames: number;
};

export const MangaLines: React.FC<Props> = ({durationFrames}) => {
  const frame = useCurrentFrame();
  const fade = interpolate(frame, [0, 8, durationFrames - 8, durationFrames], [0, 0.7, 0.7, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const lines = Array.from({length: 16}, (_, i) => {
    const angle = (i / 16) * 360;
    const len = 400 + (i % 3) * 80;
    return {angle, len, width: 2 + (i % 2)};
  });

  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: fade}}>
      <svg width="100%" height="100%" viewBox="0 0 1080 1920">
        {lines.map((l, i) => (
          <line
            key={i}
            x1={540}
            y1={960}
            x2={540 + Math.cos((l.angle * Math.PI) / 180) * l.len}
            y2={960 + Math.sin((l.angle * Math.PI) / 180) * l.len}
            stroke={i % 2 === 0 ? BRAND.text : BRAND.cyan}
            strokeWidth={l.width}
            opacity={0.6}
          />
        ))}
      </svg>
    </AbsoluteFill>
  );
};
