import type {GlobalFxMoment} from '../../types';

export const getActiveGlobalFx = (
  frame: number,
  moments: GlobalFxMoment[],
  type: GlobalFxMoment['type'],
): GlobalFxMoment | null => {
  for (const m of moments) {
    if (m.type !== type) continue;
    if (frame >= m.start_frame && frame < m.start_frame + m.duration_frames) {
      return m;
    }
  }
  return null;
};

export const getActiveVhsSegment = (
  frame: number,
  moments: GlobalFxMoment[],
): GlobalFxMoment | null => {
  for (const m of moments) {
    if (m.type !== 'vhs_filter') continue;
    const end = m.end_frame ?? m.start_frame + m.duration_frames;
    if (frame >= m.start_frame && frame < end) {
      return m;
    }
  }
  return null;
};

export const getFreezeStampAtFrame = (
  frame: number,
  moments: GlobalFxMoment[],
): GlobalFxMoment | null => getActiveGlobalFx(frame, moments, 'freeze_stamp');
