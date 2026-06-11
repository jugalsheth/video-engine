import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

type Props = {
  word: string;
  color?: string;
};

export const WordHighlight: React.FC<Props> = ({word, color = '#00D4FF'}) => {
  const frame = useCurrentFrame();
  const flash = interpolate(frame, [0, 4, 12], [0.3, 1, 0.6], {
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-end',
        alignItems: 'center',
        paddingBottom: '22%',
        pointerEvents: 'none',
      }}
    >
      <span
        style={{
          color,
          fontFamily:
            'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
          fontSize: 52,
          fontWeight: 800,
          opacity: flash,
          textTransform: 'uppercase',
          letterSpacing: 2,
        }}
      >
        {word}
      </span>
    </AbsoluteFill>
  );
};
