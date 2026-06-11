import React from 'react';
import {Img, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {useOverlayScale} from '../../OverlayScaleContext';
import {OVERLAY_BASE, overlaySize, SPRING_SNAP} from '../../layout';
import {FunBase} from './FunBase';

type Props = {
  file: string;
  durationFrames: number;
  side?: 'left' | 'right' | 'center';
};

/** PNG meme stickers — drop files in public/stickers/ */
export const StickerSlap: React.FC<Props> = ({
  file,
  durationFrames,
  side = 'right',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const scale = useOverlayScale();
  const size = overlaySize(OVERLAY_BASE.sticker, scale);
  const slam = spring({frame, fps, config: SPRING_SNAP, durationInFrames: 10});
  const rot = -12 + slam * 12;

  return (
    <FunBase durationFrames={durationFrames} side={side} zone="corner">
      <Img
        src={staticFile(file)}
        style={{
          width: size,
          height: size,
          objectFit: 'contain',
          transform: `scale(${slam}) rotate(${rot}deg)`,
          filter: 'drop-shadow(0 8px 16px rgba(0,0,0,0.85))',
        }}
      />
    </FunBase>
  );
};
