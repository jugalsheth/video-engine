import React from 'react';
import {Freeze, useCurrentFrame} from 'remotion';
import type {GlobalFxMoment} from '../../types';
import {getFreezeStampAtFrame} from './utils';

type Props = {
  children: React.ReactNode;
  moments: GlobalFxMoment[];
};

/** Holds video at freeze_stamp start_frame while timeline continues. */
export const VideoFreezeWrap: React.FC<Props> = ({children, moments}) => {
  const frame = useCurrentFrame();
  const active = getFreezeStampAtFrame(frame, moments);

  return (
    <Freeze frame={active?.start_frame ?? frame} active={active !== null}>
      {children}
    </Freeze>
  );
};
