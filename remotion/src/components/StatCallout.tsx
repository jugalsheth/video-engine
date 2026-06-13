import React from 'react';
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {BRAND, FONT, OVERLAY_LEGIBLE, SAFE, SPRING_DEFAULT, SPRING_SNAP} from '../layout';
import {FONT_BODY, FONT_HEADLINE} from '../fonts';
import {LottieAccent} from './LottieAccent';

type Props = {
  number: string | number;
  label: string;
  side?: 'left' | 'right';
  tickerEnabled?: boolean;
};

const parseNumber = (value: string | number): number => {
  if (typeof value === 'number') return value;
  const cleaned = value.replace(/[^0-9.]/g, '');
  return cleaned ? parseFloat(cleaned) : 0;
};

const ParticleBurst: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const particles = Array.from({length: 20}, (_, i) => {
    const angle = (i / 20) * Math.PI * 2;
    const p = spring({frame, fps, config: SPRING_DEFAULT, durationInFrames: 25});
    const dist = interpolate(p, [0, 1], [0, 40 + (i % 5) * 8]);
    const opacity = interpolate(frame, [0, 25], [1, 0], {extrapolateRight: 'clamp'});
    return {
      x: Math.cos(angle) * dist,
      y: Math.sin(angle) * dist,
      opacity,
      size: 4 + (i % 3) * 2,
    };
  });

  return (
    <>
      {particles.map((pt, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            width: pt.size,
            height: pt.size,
            borderRadius: '50%',
            backgroundColor: BRAND.cyan,
            opacity: pt.opacity,
            transform: `translate(${pt.x}px, ${pt.y}px)`,
          }}
        />
      ))}
    </>
  );
};

export const StatCallout: React.FC<Props> = ({
  number,
  label,
  side = 'right',
  tickerEnabled = true,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const target = parseNumber(number);
  const suffix = typeof number === 'string' ? number.replace(/[0-9.]/g, '') : '';

  const entrance = spring({frame, fps, config: SPRING_SNAP, durationInFrames: 7});
  const slideX = interpolate(entrance, [0, 1], [side === 'right' ? 120 : -120, 0]);
  const shake =
    frame <= 8
      ? Math.sin(frame * 2.5) * interpolate(frame, [0, 8], [14, 0], {extrapolateRight: 'clamp'})
      : 0;
  const popScale = 0.5 + entrance * 0.5;
  const flash = frame <= 2 ? interpolate(frame, [0, 1, 2], [0, 0.5, 0], {extrapolateRight: 'clamp'}) : 0;

  let display: number;
  if (tickerEnabled) {
    const progress = interpolate(frame, [0, 20], [0, target], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    });
    display = Math.round(progress);
  } else {
    display = target;
  }

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
      {flash > 0 && (
        <AbsoluteFill
          style={{
            backgroundColor: '#fff',
            opacity: flash * 0.35,
            mixBlendMode: 'overlay',
            pointerEvents: 'none',
          }}
        />
      )}
      <div
        style={{
          position: 'relative',
          transform: `translateX(${slideX + shake}px) scale(${popScale})`,
          backgroundColor: OVERLAY_LEGIBLE.pillBg,
          border: OVERLAY_LEGIBLE.pillBorder,
          boxShadow: OVERLAY_LEGIBLE.boxShadow,
          padding: '20px 28px',
          borderRadius: 8,
          textAlign: side === 'right' ? 'right' : 'left',
          maxWidth: 320,
        }}
      >
        <ParticleBurst />
        <LottieAccent
          file="lottie/fun/sparkle_burst.json"
          fallbackFiles={[
            'lottie/fun/datapulse.json',
            'lottie/data_pulse.json',
            'lottie/chart_growth.json',
          ]}
          width={72}
          height={72}
        />
        <div
          style={{
            color: BRAND.amber,
            fontFamily: FONT_HEADLINE,
            fontSize: FONT.stat + 8,
            fontWeight: 400,
            lineHeight: 1,
          }}
        >
          {display}
          {suffix}
        </div>
        <div
          style={{
            color: BRAND.text,
            fontFamily: FONT_BODY,
            fontSize: FONT.body - 4,
            fontWeight: 600,
            marginTop: 8,
            textShadow: OVERLAY_LEGIBLE.textShadow,
          }}
        >
          {label}
        </div>
      </div>
    </AbsoluteFill>
  );
};
