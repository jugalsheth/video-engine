import React from 'react';
import {AbsoluteFill, interpolate, OffthreadVideo, staticFile, useCurrentFrame} from 'remotion';
import {AROLL_COMPOSITED_POSITION, AROLL_GREENSCREEN_POSITION, MEDIA_COVER_CENTER} from '../layout';
import {isCompositedMoment} from '../utils/brollLayouts';
import type {BrollMoment} from '../types';

const CROSSFADE_FRAMES = 6;

type Props = {
  brollMoments: BrollMoment[];
};

const compositedOpacity = (
  frame: number,
  moments: BrollMoment[],
): number => {
  for (const m of moments) {
    if (!isCompositedMoment(m)) continue;
    const {start_frame: start, end_frame: end} = m;
    if (frame >= start && frame < end) {
      const fadeIn = interpolate(frame, [start, start + CROSSFADE_FRAMES], [1, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });
      const fadeOut = interpolate(frame, [end - CROSSFADE_FRAMES, end], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });
      return Math.min(fadeIn, fadeOut);
    }
    if (frame >= end - CROSSFADE_FRAMES && frame < end) {
      return interpolate(frame, [end - CROSSFADE_FRAMES, end], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });
    }
    if (frame >= start - CROSSFADE_FRAMES && frame < start) {
      return interpolate(frame, [start - CROSSFADE_FRAMES, start], [1, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });
    }
  }
  return 1;
};

export const MainVideo: React.FC<Props> = ({brollMoments}) => {
  const frame = useCurrentFrame();

  const compositedActive = brollMoments.some(
    (m) =>
      isCompositedMoment(m) &&
      frame >= m.start_frame &&
      frame < m.end_frame,
  );

  const greenscreenActive = brollMoments.some(
    (m) =>
      m.layout === 'greenscreen' &&
      frame >= m.start_frame &&
      frame < m.end_frame,
  );

  const opacity = compositedActive ? 0 : compositedOpacity(frame, brollMoments);

  const objectPosition = greenscreenActive
    ? AROLL_GREENSCREEN_POSITION
    : compositedActive
      ? AROLL_COMPOSITED_POSITION
      : MEDIA_COVER_CENTER.objectPosition;

  return (
    <AbsoluteFill style={{opacity}}>
      <OffthreadVideo
        src={staticFile('source.mp4')}
        muted
        style={{
          ...MEDIA_COVER_CENTER,
          objectPosition,
        }}
      />
    </AbsoluteFill>
  );
};
