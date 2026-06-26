import React from 'react';
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {useOverlayScale} from '../../OverlayScaleContext';
import {MEDIA_COVER_CENTER, OVERLAY_BASE, overlaySize, SAFE, SPRING_DEFAULT} from '../../layout';
import {legacyBrollTopPercent} from '../../utils/layoutZones';
import type {BrollMoment} from '../../types';

type Props = {
  moment: BrollMoment;
};

const useKenBurns = (frame: number, duration: number) => {
  const kenBurns = interpolate(frame, [0, duration], [1.05, 1.18], {
    extrapolateRight: 'clamp',
  });
  const panX = interpolate(frame, [0, duration], [-2, 3], {extrapolateRight: 'clamp'});
  return {kenBurns, panX};
};

export const LegacyBrollCard: React.FC<Props> = ({moment}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const duration = moment.end_frame - moment.start_frame;
  const scale = useOverlayScale();
  const brollHeight = overlaySize(OVERLAY_BASE.brollHeight, scale);
  const {kenBurns, panX} = useKenBurns(frame, duration);

  const fadeIn = spring({frame, fps, config: SPRING_DEFAULT, durationInFrames: 12});
  const fadeOut = spring({
    frame: Math.max(0, frame - (duration - 12)),
    fps,
    config: SPRING_DEFAULT,
    durationInFrames: 12,
  });
  const opacity = frame < duration - 12 ? fadeIn : 1 - fadeOut;

  const hasImage = Boolean(moment.image_file);
  const hasClip = Boolean(moment.clip_file);
  if (!hasImage && !hasClip) {
    return null;
  }

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-start',
        alignItems: 'center',
        paddingTop: `${legacyBrollTopPercent()}%`,
        paddingLeft: SAFE.sides,
        paddingRight: SAFE.sides,
        pointerEvents: 'none',
        opacity,
      }}
    >
      <div
        style={{
          width: `${OVERLAY_BASE.brollWidthPct}%`,
          height: brollHeight,
          borderRadius: 6,
          overflow: 'hidden',
          boxShadow: '0 12px 40px rgba(0,0,0,0.75)',
          border: '2px solid rgba(201,146,58,0.4)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          backgroundColor: '#0C0B09',
        }}
      >
        {hasImage ? (
          <Img
            src={staticFile(moment.image_file!)}
            style={{
              ...MEDIA_COVER_CENTER,
              transform: `scale(${kenBurns}) translateX(${panX}%)`,
            }}
          />
        ) : (
          <OffthreadVideo
            src={staticFile(moment.clip_file!)}
            muted
            style={{
              ...MEDIA_COVER_CENTER,
              transform: `scale(${kenBurns}) translateX(${panX}%)`,
            }}
          />
        )}
      </div>
    </AbsoluteFill>
  );
};
