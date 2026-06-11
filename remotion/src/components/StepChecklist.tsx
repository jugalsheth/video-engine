import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {BRAND, OVERLAY_LEGIBLE, SAFE, SPRING_STEP} from '../layout';
import {FONT_BODY, FONT_HEADLINE} from '../fonts';
import type {StepBeat} from '../types';

type Props = {
  beats: StepBeat[];
  endFrame: number;
};

const ROW_HEIGHT = 78;
const STEP_FONT = 48;

export const StepChecklist: React.FC<Props> = ({beats, endFrame}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  if (beats.length === 0) return null;

  const sorted = [...beats].sort((a, b) => a.step - b.step);
  const firstFrame = sorted[0].frame;
  const globalFrame = frame + firstFrame;

  const visibleBeats = sorted.filter((b) => globalFrame >= b.frame);
  if (visibleBeats.length === 0 || globalFrame > endFrame) return null;

  const activeBeat = [...visibleBeats].reverse().find((b) => globalFrame >= b.frame);
  const activeStep = activeBeat?.step ?? 1;
  const totalSteps = sorted.length;

  const lineHeight =
    visibleBeats.length > 0
      ? 60 + (visibleBeats.length - 1) * ROW_HEIGHT
      : 0;

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-start',
        alignItems: 'flex-start',
        paddingTop: SAFE.top + 80,
        paddingLeft: SAFE.sides,
        pointerEvents: 'none',
        zIndex: 20,
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: SAFE.top + 24,
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <div
          style={{
            backgroundColor: OVERLAY_LEGIBLE.pillBg,
            border: OVERLAY_LEGIBLE.pillBorder,
            borderRadius: 8,
            padding: '6px 16px',
            fontFamily: FONT_BODY,
            fontSize: 22,
            fontWeight: 800,
            color: BRAND.cyan,
            letterSpacing: 1,
            textShadow: OVERLAY_LEGIBLE.textShadow,
          }}
        >
          {activeStep}/{totalSteps}
        </div>
      </div>

      <div
        style={{
          position: 'absolute',
          left: SAFE.sides + 23,
          top: SAFE.top + 60,
          width: 2,
          height: lineHeight,
          backgroundColor: BRAND.cyan,
          opacity: 0.85,
          boxShadow: '0 0 8px rgba(0,212,255,0.45)',
        }}
      />

      {sorted.map((beat) => {
        if (globalFrame < beat.frame) return null;

        const localFrame = globalFrame - beat.frame;
        const slide = spring({
          frame: localFrame,
          fps,
          config: SPRING_STEP,
          durationInFrames: 14,
        });
        const translateX = interpolate(slide, [0, 1], [-100, 0]);
        const opacity = interpolate(slide, [0, 1], [0, 1]);
        const isActive = beat.step === activeStep;
        const isPast = beat.step < activeStep;

        return (
          <div
            key={beat.step}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              opacity: opacity * (isActive ? 1 : isPast ? 0.7 : 1),
              transform: `translateX(${translateX}px)`,
              marginTop: (beat.step - 1) * ROW_HEIGHT,
              maxWidth: 920,
            }}
          >
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: '50%',
                backgroundColor: BRAND.amber,
                color: '#0a0a0e',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontFamily: FONT_HEADLINE,
                fontSize: 28,
                fontWeight: 900,
                flexShrink: 0,
                boxShadow: isActive
                  ? `0 0 16px rgba(201,146,58,0.6), ${OVERLAY_LEGIBLE.boxShadow}`
                  : OVERLAY_LEGIBLE.boxShadow,
                border: isActive
                  ? '2px solid rgba(201,146,58,0.9)'
                  : OVERLAY_LEGIBLE.pillBorder,
              }}
            >
              {beat.step}
            </div>
            <div
              style={{
                backgroundColor: OVERLAY_LEGIBLE.pillBg,
                borderLeft: isActive
                  ? `4px solid ${BRAND.amber}`
                  : OVERLAY_LEGIBLE.pillBorder,
                borderTop: isActive ? 'none' : OVERLAY_LEGIBLE.pillBorder,
                borderRight: isActive ? 'none' : OVERLAY_LEGIBLE.pillBorder,
                borderBottom: isActive ? 'none' : OVERLAY_LEGIBLE.pillBorder,
                borderRadius: isActive ? '0 8px 8px 0' : 8,
                padding: '12px 18px',
                boxShadow: OVERLAY_LEGIBLE.boxShadow,
                backdropFilter: 'blur(6px)',
                WebkitBackdropFilter: 'blur(6px)',
                flex: 1,
              }}
            >
              <p
                style={{
                  margin: 0,
                  color: BRAND.text,
                  fontFamily: FONT_HEADLINE,
                  fontSize: STEP_FONT,
                  fontWeight: 800,
                  lineHeight: 1.15,
                  letterSpacing: 0.4,
                  textTransform: 'uppercase',
                  textShadow: OVERLAY_LEGIBLE.textShadow,
                }}
              >
                {beat.label ?? `STEP ${beat.step}`}
              </p>
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
