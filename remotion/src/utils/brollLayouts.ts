import type {BrollMoment} from '../types';

export const COMPOSITED_LAYOUTS = [
  'presenter_on_bg',
  'presenter_cutout',
  'immersive_flash',
] as const;

export type CompositedLayout = (typeof COMPOSITED_LAYOUTS)[number];

export const isCompositedLayout = (layout?: string): layout is CompositedLayout =>
  COMPOSITED_LAYOUTS.includes(layout as CompositedLayout);

export const isCompositedMoment = (moment: BrollMoment): boolean =>
  isCompositedLayout(moment.layout) ||
  Boolean(moment.image_file && moment.layout !== 'pip' && moment.layout !== 'greenscreen');

export const STRIP_HEIGHT_RATIO = 0.38;
