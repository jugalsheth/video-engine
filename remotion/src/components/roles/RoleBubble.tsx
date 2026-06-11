import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {useOverlayScale} from '../../OverlayScaleContext';
import {BRAND, OVERLAY_BASE, overlaySize, SPRING_DEFAULT} from '../../layout';

type Props = {
  text: string;
  side?: 'left' | 'right';
  accent?: string;
};

export const RoleBubble: React.FC<Props> = ({
  text,
  side = 'left',
  accent = BRAND.amber,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame: frame - 4, fps, config: SPRING_DEFAULT, durationInFrames: 12});
  const scale = useOverlayScale();
  const fontSize = overlaySize(OVERLAY_BASE.roleBubbleFont, scale);
  const maxWidth = overlaySize(OVERLAY_BASE.roleBubbleMaxWidth, scale);

  return (
    <div
      style={{
        position: 'relative',
        backgroundColor: '#FFF8E7',
        color: '#1a1a1a',
        padding: '10px 16px',
        borderRadius: 16,
        border: '3px solid #000',
        fontFamily: 'Comic Sans MS, Chalkboard SE, cursive',
        fontSize,
        fontWeight: 900,
        maxWidth,
        marginBottom: 8,
        transform: `scale(${Math.max(0, pop)})`,
        boxShadow: '3px 3px 0 #000',
        alignSelf: side === 'left' ? 'flex-start' : 'flex-end',
      }}
    >
      {text}
      <div
        style={{
          position: 'absolute',
          bottom: -10,
          [side === 'left' ? 'left' : 'right']: 28,
          width: 0,
          height: 0,
          borderLeft: '8px solid transparent',
          borderRight: '8px solid transparent',
          borderTop: `12px solid ${accent}`,
        }}
      />
    </div>
  );
};
