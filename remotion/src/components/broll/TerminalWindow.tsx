import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {BRAND} from '../../layout';
import {BrollBase} from './BrollBase';

const CODE = '$ python pipeline.py --run';

export const TerminalWindow: React.FC<{durationFrames: number}> = ({durationFrames}) => {
  const frame = useCurrentFrame();
  const chars = Math.floor(interpolate(frame, [0, 40], [0, CODE.length], {extrapolateRight: 'clamp'}));
  const cursor = frame % 20 < 10;

  return (
    <BrollBase durationFrames={durationFrames}>
      <div style={{backgroundColor: '#0a0a0a', padding: 12, borderRadius: 4, fontFamily: 'monospace'}}>
        <div style={{color: '#4ade80', fontSize: 14}}>{CODE.slice(0, chars)}{cursor ? '▋' : ' '}</div>
        <div style={{color: BRAND.text, fontSize: 12, marginTop: 8, opacity: 0.6}}>Running...</div>
      </div>
    </BrollBase>
  );
};
