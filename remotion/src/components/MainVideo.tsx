import React from 'react';
import {AbsoluteFill, OffthreadVideo, staticFile, useCurrentFrame} from 'remotion';
import {AROLL_GREENSCREEN_POSITION, MEDIA_COVER_CENTER} from '../layout';
import type {BrollMoment} from '../types';

type Props = {
  brollMoments: BrollMoment[];
};

export const MainVideo: React.FC<Props> = ({brollMoments}) => {
  const frame = useCurrentFrame();

  const greenscreenActive = brollMoments.some(
    (m) =>
      m.layout === 'greenscreen' &&
      frame >= m.start_frame &&
      frame < m.end_frame,
  );

  return (
    <AbsoluteFill>
      <OffthreadVideo
        src={staticFile('source.mp4')}
        style={{
          ...MEDIA_COVER_CENTER,
          objectPosition: greenscreenActive
            ? AROLL_GREENSCREEN_POSITION
            : MEDIA_COVER_CENTER.objectPosition,
        }}
      />
    </AbsoluteFill>
  );
};
