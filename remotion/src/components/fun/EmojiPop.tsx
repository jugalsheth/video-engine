import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {useOverlayScale} from '../../OverlayScaleContext';
import {OVERLAY_BASE, overlaySize, SPRING_SNAP} from '../../layout';
import {FunBase} from './FunBase';

type Props = {
  emoji: string;
  durationFrames: number;
  side?: 'left' | 'right' | 'center';
  mood?: string;
};

export const EmojiPop: React.FC<Props> = ({
  emoji,
  durationFrames,
  side = 'right',
  mood = 'medium',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const gfx = useOverlayScale();
  const pop = spring({frame, fps, config: SPRING_SNAP, durationInFrames: 12});
  const bounce = Math.sin(frame * 0.35) * 8 * pop;
  const size = overlaySize(
    mood === 'chaos' ? OVERLAY_BASE.emojiSizeChaos : OVERLAY_BASE.emojiSize,
    gfx,
  );

  return (
    <FunBase durationFrames={durationFrames} side={side}>
      <div
        style={{
          fontSize: size * pop,
          transform: `translateY(${bounce}px) rotate(${-10 + pop * 10}deg)`,
          filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.8))',
        }}
      >
        {emoji}
      </div>
    </FunBase>
  );
};
