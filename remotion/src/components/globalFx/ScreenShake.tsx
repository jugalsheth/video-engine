import React from 'react';
import {noise2D} from '@remotion/noise';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import type {GlobalFxMoment} from '../../types';
import {getActiveGlobalFx} from './utils';

type Props = {
  children: React.ReactNode;
  moments: GlobalFxMoment[];
  defaultIntensity?: number;
};

export const ScreenShake: React.FC<Props> = ({
  children,
  moments,
  defaultIntensity = 2,
}) => {
  const frame = useCurrentFrame();
  const active = getActiveGlobalFx(frame, moments, 'screen_shake');

  if (!active) {
    return <>{children}</>;
  }

  const intensity = active.intensity ?? defaultIntensity;
  const dx =
    (noise2D(`shakeX-${active.start_frame}`, frame, 0) - 0.5) * intensity * 2;
  const dy =
    (noise2D(`shakeY-${active.start_frame}`, frame, 0) - 0.5) * intensity * 2;

  return (
    <AbsoluteFill style={{transform: `translate(${dx}px, ${dy}px)`}}>
      {children}
    </AbsoluteFill>
  );
};
