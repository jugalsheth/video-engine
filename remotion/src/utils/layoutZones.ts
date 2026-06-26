import type {BrollMoment} from '../types';
import {CAPTION_ZONE, BROLL_ZONE_TOP} from '../layout';
import {STRIP_HEIGHT_RATIO, isCompositedMoment} from './brollLayouts';

export type LayoutMode =
  | 'default'
  | 'composited_strip'
  | 'greenscreen'
  | 'legacy_broll_card'
  | 'step_chapter';

export type CaptionPlacement = {
  paddingTopPercent: number;
  mode: LayoutMode;
};

const DEFAULT_CAPTION_TOP = 75;
const COMPOSITED_CAPTION_TOP = 52;
const LEGACY_BROLL_CAPTION_TOP = 55;
const STEP_CAPTION_SHIFT = 12;

export const detectLayoutMode = (
  frame: number,
  brollMoments: BrollMoment[],
): LayoutMode => {
  const active = brollMoments.find(
    (m) => frame >= m.start_frame && frame < m.end_frame,
  );
  if (!active) return 'default';
  if (isCompositedMoment(active)) return 'composited_strip';
  if (active.layout === 'greenscreen') return 'greenscreen';
  if (active.image_file || active.clip_file) return 'legacy_broll_card';
  return 'default';
};

export const captionPlacement = (
  frame: number,
  brollMoments: BrollMoment[],
  basePosition: number,
  inStepChapter: boolean,
): CaptionPlacement => {
  const mode = detectLayoutMode(frame, brollMoments);
  let paddingTopPercent = basePosition;

  switch (mode) {
    case 'composited_strip':
    case 'greenscreen':
      paddingTopPercent = Math.min(basePosition, COMPOSITED_CAPTION_TOP);
      break;
    case 'legacy_broll_card':
      paddingTopPercent = Math.min(basePosition, LEGACY_BROLL_CAPTION_TOP);
      break;
    default:
      paddingTopPercent = basePosition;
  }

  if (inStepChapter) {
    paddingTopPercent = Math.min(
      paddingTopPercent + STEP_CAPTION_SHIFT,
      CAPTION_ZONE * 100 + 8,
    );
  }

  return {paddingTopPercent, mode};
};

export const brollPanelTopPercent = (): number =>
  (1 - STRIP_HEIGHT_RATIO) * 100;

export const legacyBrollTopPercent = (): number => BROLL_ZONE_TOP * 100;
