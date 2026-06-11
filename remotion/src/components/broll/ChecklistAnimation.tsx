import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../../layout';
import {BrollBase} from './BrollBase';

const ITEMS = ['Update profile', 'Build portfolio', 'Ship project'];

export const ChecklistAnimation: React.FC<{durationFrames: number}> = ({durationFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <BrollBase durationFrames={durationFrames}>
      {ITEMS.map((item, i) => {
        const delay = i * 12;
        const p = spring({frame: frame - delay, fps, config: {damping: 200, stiffness: 100}, durationInFrames: 14});
        const check = interpolate(p, [0, 1], [0, 1]);
        return (
          <div key={item} style={{display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10, opacity: p}}>
            <div style={{
              width: 28, height: 28, borderRadius: '50%', backgroundColor: BRAND.cyan,
              color: BRAND.text, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900,
            }}>{i + 1}</div>
            <span style={{color: BRAND.text, fontSize: 16, fontWeight: 600}}>{item}</span>
            <span style={{color: BRAND.cyan, marginLeft: 'auto'}}>{check > 0.5 ? '✓' : ''}</span>
          </div>
        );
      })}
    </BrollBase>
  );
};
