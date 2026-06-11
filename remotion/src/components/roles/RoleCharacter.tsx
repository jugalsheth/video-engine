import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {useOverlayScale} from '../../OverlayScaleContext';
import {OVERLAY_BASE, overlaySize, SPRING_DEFAULT, SPRING_SNAP} from '../../layout';

type Props = {
  role: string;
  pose: string;
};

const PALETTE: Record<string, {body: string; accent: string; eye: string}> = {
  victim: {body: '#7B68A6', accent: '#4A3F6B', eye: '#F5F0E8'},
  hype: {body: '#E8A838', accent: '#C9923A', eye: '#1a1a1a'},
  skeptic: {body: '#5A6A7A', accent: '#3D4A56', eye: '#F5F0E8'},
  expert: {body: '#2A8FA8', accent: '#00D4FF', eye: '#F5F0E8'},
  gremlin: {body: '#4CAF50', accent: '#2E7D32', eye: '#FFEB3B'},
};

export const RoleCharacter: React.FC<Props> = ({role, pose}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const colors = PALETTE[role] ?? PALETTE.skeptic;
  const gfx = useOverlayScale();
  const size = overlaySize(OVERLAY_BASE.roleCharacter, gfx);

  const bounce = spring({frame, fps, config: SPRING_DEFAULT, durationInFrames: 20});
  const wobble = Math.sin(frame * 0.3) * 3;

  let bodyY = 0;
  let bodyRot = 0;
  let armL = -35;
  let armR = 35;
  let eyeScaleY = 1;
  let mouthPath = 'M35,58 Q50,68 65,58';

  switch (pose) {
    case 'melting':
      bodyY = interpolate(bounce, [0, 1], [0, 12]);
      bodyRot = 8;
      eyeScaleY = 0.6;
      mouthPath = 'M38,62 Q50,55 62,62';
      break;
    case 'coffee':
      bodyY = 4;
      armL = -20;
      armR = 50;
      break;
    case 'celebrate':
      armL = -55;
      armR = 55;
      bodyY = -interpolate(bounce, [0, 1], [0, 15]);
      break;
    case 'thumbs_up':
      armR = 60;
      armL = -30;
      break;
    case 'eyebrow':
      eyeScaleY = 0.7;
      bodyRot = -5;
      break;
    case 'arms_crossed':
      armL = 10;
      armR = -10;
      bodyRot = 5;
      break;
    case 'point':
      armR = 70;
      armL = -25;
      break;
    case 'explain':
      armL = -50;
      armR = 40;
      break;
    case 'chaos':
      bodyRot = wobble * 4;
      armL = -60 + wobble * 5;
      armR = 60 - wobble * 5;
      break;
    case 'troll':
      bodyRot = Math.sin(frame * 0.5) * 10;
      mouthPath = 'M35,55 Q50,72 65,55';
      break;
    default:
      break;
  }

  if (role === 'gremlin') {
    const chaosSpring = spring({frame, fps, config: SPRING_SNAP, durationInFrames: 8});
    bodyRot += chaosSpring * 15;
  }

  return (
    <svg
      width={size}
      height={Math.round(size * 1.14)}
      viewBox="0 0 100 120"
      style={{overflow: 'visible'}}
    >
      {/* shadow */}
      <ellipse cx="50" cy="112" rx="30" ry="6" fill="rgba(0,0,0,0.35)" />
      <g transform={`translate(0, ${bodyY}) rotate(${bodyRot}, 50, 70)`}>
        {/* legs */}
        <rect x="38" y="82" width="10" height="22" rx="4" fill={colors.accent} />
        <rect x="52" y="82" width="10" height="22" rx="4" fill={colors.accent} />
        {/* body */}
        <ellipse cx="50" cy="68" rx="28" ry="26" fill={colors.body} stroke="#000" strokeWidth="2.5" />
        {/* arms */}
        <line x1="28" y1="62" x2={28 + armL * 0.3} y2={62 + armL * 0.15} stroke={colors.body} strokeWidth="8" strokeLinecap="round" />
        <line x1="72" y1="62" x2={72 + armR * 0.3} y2={62 + armR * 0.15} stroke={colors.body} strokeWidth="8" strokeLinecap="round" />
        {/* head */}
        <circle cx="50" cy="38" r="22" fill={colors.body} stroke="#000" strokeWidth="2.5" />
        {/* eyes */}
        <ellipse cx="42" cy="36" rx="5" ry={5 * eyeScaleY} fill={colors.eye} stroke="#000" strokeWidth="1.5" />
        <ellipse cx="58" cy="36" rx="5" ry={5 * eyeScaleY} fill={colors.eye} stroke="#000" strokeWidth="1.5" />
        {pose === 'eyebrow' && (
          <line x1="36" y1="28" x2="48" y2="30" stroke="#000" strokeWidth="2.5" strokeLinecap="round" />
        )}
        {/* mouth */}
        <path d={mouthPath} fill="none" stroke="#000" strokeWidth="2.5" strokeLinecap="round" />
        {/* role accessories */}
        {role === 'expert' && (
          <>
            <rect x="34" y="30" width="32" height="10" rx="2" fill="none" stroke="#000" strokeWidth="2" />
            <line x1="50" y1="30" x2="50" y2="24" stroke="#000" strokeWidth="2" />
          </>
        )}
        {role === 'victim' && pose === 'coffee' && (
          <rect x="68" y="48" width="14" height="18" rx="3" fill="#6F4E37" stroke="#000" strokeWidth="1.5" />
        )}
        {role === 'gremlin' && (
          <polygon points="42,18 50,8 58,18" fill={colors.accent} stroke="#000" strokeWidth="1.5" />
        )}
        {role === 'hype' && pose === 'celebrate' && (
          <>
            <text x="18" y="30" fontSize="14">✨</text>
            <text x="72" y="25" fontSize="14">✨</text>
          </>
        )}
      </g>
    </svg>
  );
};
