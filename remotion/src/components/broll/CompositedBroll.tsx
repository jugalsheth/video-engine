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
import {AROLL_COMPOSITED_POSITION, MEDIA_COVER_CENTER, PRESENTER_STRIP_SCALE, SPRING_CAPCUT, SPRING_DEFAULT} from '../../layout';
import {STRIP_HEIGHT_RATIO} from '../../utils/brollLayouts';
import type {BrollMoment} from '../../types';

type Props = {
  moment: BrollMoment;
};

const STRIP_TOP = `${(1 - STRIP_HEIGHT_RATIO) * 100}%`;

export const CompositedBroll: React.FC<Props> = ({moment}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const duration = Math.max(1, moment.end_frame - moment.start_frame);
  const layout = moment.layout ?? 'presenter_on_bg';
  const isImmersive = layout === 'immersive_flash';
  const isCutout = layout === 'presenter_cutout' && Boolean(moment.cutout_file);

  const enterSpring = spring({
    frame,
    fps,
    config: SPRING_CAPCUT,
    durationInFrames: 6,
  });
  const exitStart = Math.max(0, duration - 6);
  const exitSpring = spring({
    frame: Math.max(0, frame - exitStart),
    fps,
    config: SPRING_DEFAULT,
    durationInFrames: 6,
  });

  const enterScale = interpolate(enterSpring, [0, 1], [1.06, 1]);
  const exitScale = frame >= exitStart ? interpolate(exitSpring, [0, 1], [1, 1.03]) : 1;
  const masterScale = frame < 6 ? enterScale : exitScale;

  const bgKenBurns = interpolate(frame, [0, duration], [1.04, 1.12], {
    extrapolateRight: 'clamp',
  });

  const flashOpacity = interpolate(frame, [0, 1, 4], [0.5, 0.2, 0], {
    extrapolateRight: 'clamp',
  });

  const layerOpacity = frame < 6
    ? interpolate(enterSpring, [0, 1], [0, 1])
    : frame >= exitStart
      ? 1 - exitSpring
      : 1;

  if (!moment.image_file) {
    return null;
  }

  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: layerOpacity}}>
      <AbsoluteFill
        style={{
          transform: `scale(${masterScale * bgKenBurns})`,
          transformOrigin: 'center center',
        }}
      >
        <Img src={staticFile(moment.image_file)} style={MEDIA_COVER_CENTER} />
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          background:
            'radial-gradient(ellipse at center, transparent 45%, rgba(0,0,0,0.45) 100%)',
          pointerEvents: 'none',
        }}
      />

      {!isImmersive && isCutout && moment.cutout_file ? (
        <AbsoluteFill
          style={{
            justifyContent: 'flex-end',
            alignItems: 'center',
            paddingBottom: '4%',
          }}
        >
          <Img
            src={staticFile(moment.cutout_file)}
            style={{
              maxHeight: `${STRIP_HEIGHT_RATIO * 100 + 8}%`,
              maxWidth: '92%',
              objectFit: 'contain',
              filter: 'drop-shadow(0 12px 32px rgba(0,0,0,0.65))',
              transform: `scale(${interpolate(enterSpring, [0, 1], [0.95, 1])})`,
            }}
          />
        </AbsoluteFill>
      ) : null}

      {!isImmersive && !isCutout ? (
        <AbsoluteFill>
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: STRIP_TOP,
              bottom: 0,
              overflow: 'hidden',
              maskImage: 'linear-gradient(to bottom, transparent 0%, black 10%)',
              WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 10%)',
            }}
          >
            <OffthreadVideo
              src={staticFile('source.mp4')}
              trimBefore={moment.start_frame}
              muted
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                objectPosition: AROLL_COMPOSITED_POSITION,
                transform: `scale(${PRESENTER_STRIP_SCALE})`,
                transformOrigin: 'center bottom',
              }}
            />
          </div>
        </AbsoluteFill>
      ) : null}

      <AbsoluteFill
        style={{
          backgroundColor: '#fff',
          opacity: flashOpacity * 0.2,
          mixBlendMode: 'overlay',
          pointerEvents: 'none',
        }}
      />
    </AbsoluteFill>
  );
};
