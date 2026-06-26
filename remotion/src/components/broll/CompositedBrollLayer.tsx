import React from 'react';
import {Sequence} from 'remotion';
import {CompositedBroll} from './CompositedBroll';
import {isCompositedMoment} from '../../utils/brollLayouts';
import type {BrollMoment} from '../../types';

type Props = {
  moments: BrollMoment[];
};

export const CompositedBrollLayer: React.FC<Props> = ({moments}) => {
  const composited = moments.filter(isCompositedMoment);

  return (
    <>
      {composited.map((moment) => {
        const duration = Math.max(1, moment.end_frame - moment.start_frame);
        return (
          <Sequence
            key={`composited-${moment.start_frame}-${moment.type}`}
            from={moment.start_frame}
            durationInFrames={duration}
            layout="none"
          >
            <CompositedBroll moment={moment} />
          </Sequence>
        );
      })}
    </>
  );
};
