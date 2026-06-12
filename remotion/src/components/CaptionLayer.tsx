import React, {useMemo} from 'react';
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {BRAND, CAPTION_VIRAL, FONT, SAFE, SPRING_DEFAULT, SPRING_SNAP} from '../layout';
import {FONT_BODY} from '../fonts';
import type {StepBeat, Transcript, WordTimestamp} from '../types';

const ENERGY_WORDS = ['right', 'unless', 'listen', "that's", 'wait', 'but', 'now'];
const MAX_WORDS_CLASSIC = 5;
const MAX_WORDS_VIRAL = CAPTION_VIRAL.maxWords;

type Props = {
  transcript: Transcript;
  captionVerticalPosition?: number;
  captionStyle?: 'viral' | 'classic';
  closerStartFrame?: number;
  openLoopPayoffFrame?: number;
  openLoopPlantFrame?: number;
  wordHighlightFrames?: Set<number>;
  stepBeats?: StepBeat[];
  energyWords?: string[];
};

const STEP_CHAPTER_WINDOW = 45;
const STEP_CAPTION_SHIFT = 16;

const getVisibleWords = (
  words: WordTimestamp[],
  frame: number,
  maxWords: number,
): WordTimestamp[] => {
  const activeIndex = words.findIndex(
    (w) => frame >= w.start_frame && frame <= w.end_frame,
  );
  if (activeIndex === -1) {
    const past = words.filter((w) => w.end_frame < frame);
    const idx = past.length > 0 ? past.length - 1 : 0;
    const start = Math.max(0, idx - Math.floor(maxWords / 2));
    return words.slice(start, start + maxWords);
  }
  const start = Math.max(0, activeIndex - Math.floor(maxWords / 2));
  return words.slice(start, start + maxWords);
};

const isEnergyWord = (word: string, extra: string[] = []) => {
  const n = word.toLowerCase().replace(/[^a-z']/g, '');
  const merged = [...ENERGY_WORDS, ...extra.map((e) => e.toLowerCase())];
  return merged.some((e) => n.includes(e.replace(/[^a-z']/g, '')));
};

export const CaptionLayer: React.FC<Props> = ({
  transcript,
  captionVerticalPosition = 75,
  captionStyle = 'viral',
  closerStartFrame,
  openLoopPayoffFrame,
  openLoopPlantFrame,
  wordHighlightFrames,
  stepBeats = [],
  energyWords = [],
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const inStepChapter = stepBeats.some(
    (b) => frame >= b.frame - STEP_CHAPTER_WINDOW && frame <= b.frame + STEP_CHAPTER_WINDOW,
  );
  const effectiveCaptionPosition = inStepChapter
    ? captionVerticalPosition + STEP_CAPTION_SHIFT
    : captionVerticalPosition;
  const words = transcript.words;
  const isViral = captionStyle === 'viral';
  const maxWords = isViral ? MAX_WORDS_VIRAL : MAX_WORDS_CLASSIC;
  const visible = useMemo(
    () => getVisibleWords(words, frame, maxWords),
    [words, frame, maxWords],
  );
  const activeIndex = words.findIndex(
    (w) => frame >= w.start_frame && frame <= w.end_frame,
  );

  let fontSize = isViral ? CAPTION_VIRAL.fontSize : FONT.caption;
  if (closerStartFrame && frame >= closerStartFrame) {
    const p = spring({
      frame: frame - closerStartFrame,
      fps,
      config: SPRING_DEFAULT,
      durationInFrames: 30,
    });
    fontSize = interpolate(p, [0, 1], [fontSize, 44]);
  }

  const payoffGlow =
    openLoopPayoffFrame &&
    frame >= openLoopPayoffFrame &&
    frame <= openLoopPayoffFrame + 30
      ? spring({
          frame: frame - openLoopPayoffFrame,
          fps,
          config: SPRING_DEFAULT,
          durationInFrames: 30,
        })
      : 0;

  const plantTease =
    openLoopPlantFrame &&
    frame >= openLoopPlantFrame &&
    frame <= openLoopPlantFrame + 45
      ? spring({
          frame: frame - openLoopPlantFrame,
          fps,
          config: SPRING_DEFAULT,
          durationInFrames: 20,
        })
      : 0;

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-start',
        alignItems: 'center',
        paddingTop: `${effectiveCaptionPosition}%`,
        paddingLeft: SAFE.sides,
        paddingRight: SAFE.sides,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          backgroundColor: isViral ? CAPTION_VIRAL.pillBg : BRAND.bgCaption,
          padding: isViral ? '12px 20px' : '16px 24px',
          borderRadius: isViral ? 12 : 0,
          maxWidth: '100%',
          boxShadow:
            payoffGlow > 0
              ? `0 0 ${interpolate(payoffGlow, [0, 0.5, 1], [0, 12, 0])}px rgba(0,212,255,0.6)`
              : plantTease > 0
                ? `0 0 ${interpolate(plantTease, [0, 0.5, 1], [0, 8, 4])}px rgba(255,184,0,0.5)`
                : undefined,
          border:
            plantTease > 0.3
              ? `1px solid rgba(255,184,0,${interpolate(plantTease, [0.3, 1], [0.2, 0.6])})`
              : undefined,
        }}
      >
        <p
          style={{
            margin: 0,
            fontFamily: FONT_BODY,
            fontSize,
            fontWeight: isViral ? 900 : 600,
            textAlign: 'center',
            lineHeight: 1.2,
            textTransform: isViral ? 'uppercase' : 'none',
          }}
        >
          {visible.map((w, i) => {
            const globalIdx = words.indexOf(w);
            const isActive = globalIdx === activeIndex;
            const energy =
              isEnergyWord(w.word, energyWords) ||
              (wordHighlightFrames?.has(w.start_frame) ?? false);
            const localFrame = frame - w.start_frame;

            let flash = 1;
            if (energy && isActive && localFrame >= 0 && localFrame <= 3) {
              flash = interpolate(localFrame, [0, 1, 2, 3], [0, 1, 1, 0], {
                extrapolateRight: 'clamp',
              });
            }

            const scaleBoost = isViral ? CAPTION_VIRAL.activeScale - 1 : 0.08;
            const wordScale = isActive
              ? spring({
                  frame: frame - w.start_frame,
                  fps,
                  config: SPRING_SNAP,
                  durationInFrames: 4,
                }) *
                  scaleBoost +
                1
              : 1;

            const activeColor = isViral ? CAPTION_VIRAL.highlight : BRAND.cyan;

            return (
              <span
                key={`${w.start_frame}-${i}`}
                style={{
                  color: isActive ? activeColor : BRAND.text,
                  opacity: isActive ? 1 : isViral ? 0.85 : 0.7,
                  marginRight: isViral ? 12 : 8,
                  display: 'inline-block',
                  transform: `scale(${wordScale})`,
                  textShadow: isViral
                    ? CAPTION_VIRAL.textShadow
                    : energy && flash > 0.5
                      ? `0 0 8px ${BRAND.cyan}`
                      : undefined,
                }}
              >
                {w.word}
              </span>
            );
          })}
        </p>
      </div>
    </AbsoluteFill>
  );
};
