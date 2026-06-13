import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND, OVERLAY_LEGIBLE, SAFE, SPRING_DEFAULT} from '../../layout';
import {FONT_BODY} from '../../fonts';

type Props = {
  toastText: string;
  toastIcon?: string;
  side?: 'left' | 'right';
  durationFrames: number;
};

const IconSlack: React.FC = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <rect x="4" y="10" width="4" height="10" rx="1" fill="#E01E5A" />
    <rect x="10" y="4" width="10" height="4" rx="1" fill="#36C5F0" />
    <rect x="10" y="10" width="10" height="4" rx="1" fill="#2EB67D" />
    <rect x="4" y="4" width="4" height="4" rx="1" fill="#ECB22E" />
  </svg>
);

const IconEmail: React.FC = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <rect x="3" y="5" width="18" height="14" rx="2" stroke={BRAND.cyan} strokeWidth="1.5" />
    <path d="M3 7l9 6 9-6" stroke={BRAND.cyan} strokeWidth="1.5" />
  </svg>
);

const ToastIcon: React.FC<{name?: string}> = ({name}) => {
  if (name === 'email') return <IconEmail />;
  return <IconSlack />;
};

export const NotificationToast: React.FC<Props> = ({
  toastText,
  toastIcon = 'slack',
  side = 'right',
  durationFrames,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const slideIn = spring({
    frame,
    fps,
    config: {damping: 14, stiffness: 120},
    durationInFrames: 12,
  });
  const slideOutStart = Math.max(0, durationFrames - 8);
  const slideOut = interpolate(
    frame,
    [slideOutStart, durationFrames],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const translateY = interpolate(slideIn, [0, 1], [-80, 16]) - slideOut * 96;
  const opacity = interpolate(slideIn, [0, 1], [0, 1]) * (1 - slideOut);

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-start',
        alignItems: side === 'right' ? 'flex-end' : 'flex-start',
        paddingTop: SAFE.top,
        paddingRight: side === 'right' ? SAFE.sides : 0,
        paddingLeft: side === 'left' ? SAFE.sides : 0,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          width: 180,
          height: 56,
          borderRadius: 12,
          backgroundColor: OVERLAY_LEGIBLE.pillBg,
          border: OVERLAY_LEGIBLE.pillBorder,
          boxShadow: OVERLAY_LEGIBLE.boxShadow,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '0 14px',
          transform: `translateY(${translateY}px)`,
          opacity,
        }}
      >
        <ToastIcon name={toastIcon} />
        <span
          style={{
            color: BRAND.text,
            fontFamily: FONT_BODY,
            fontSize: 15,
            fontWeight: 600,
          }}
        >
          {toastText}
        </span>
      </div>
    </AbsoluteFill>
  );
};
