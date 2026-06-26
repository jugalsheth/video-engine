import type {BrollMoment, FunMoment, GlobalFxMoment, LogoMoment, RoleMoment, Shot, SocialMoment, StepBeat} from '../types';
import {
  BROLL_MAX_PER_STEP,
  BROLL_OVERLAP_DEDUP,
  STEP_BEAT_FALLBACK_DURATION,
  STEP_WINDOW_BUFFER,
  TITLE_BUFFER_FRAMES,
  TOAST_BLOCKS_PIP_BROLL_ONLY,
  blockingTypes,
} from '../config/conflictRules';
import {isCompositedLayout} from '../utils/brollLayouts';

const overlaps = (aStart: number, aEnd: number, bStart: number, bEnd: number) =>
  aStart < bEnd && aEnd > bStart;

export const getStepWindows = (
  shots: Shot[],
  stepBeats: StepBeat[] = [],
  buffer = STEP_WINDOW_BUFFER,
): Array<{start: number; end: number; step: number}> => {
  const fromShots = shots
    .filter((s) => s.type === 'STEP_REVEAL')
    .map((s) => ({
      start: s.start_frame - buffer,
      end: s.end_frame + buffer,
      step: (s.params.step_number as number) ?? 0,
    }));

  if (fromShots.length > 0) return fromShots;

  return stepBeats.map((b) => ({
    start: b.frame - buffer,
    end: b.frame + buffer + STEP_BEAT_FALLBACK_DURATION,
    step: b.step,
  }));
};

const overlapsStepWindow = (
  start: number,
  end: number,
  stepWindows: Array<{start: number; end: number}>,
): boolean => stepWindows.some((w) => overlaps(start, end, w.start, w.end));

const shotBlockingRanges = (shots: Shot[], momentType: string) =>
  shots
    .filter((s) => blockingTypes(momentType).has(s.type))
    .map((s) => ({
      start: s.start_frame,
      end:
        s.type === 'TITLE_CARD'
          ? s.end_frame + TITLE_BUFFER_FRAMES
          : s.end_frame,
      type: s.type,
    }));

export const filterBrollMoments = (
  shots: Shot[],
  brollMoments: BrollMoment[],
  stepBeats: StepBeat[] = [],
): BrollMoment[] => {
  const blocking = shotBlockingRanges(shots, 'broll');
  const stepWindows = getStepWindows(shots, stepBeats);
  const accepted: BrollMoment[] = [];
  const stepPairedCount = new Map<number, number>();

  for (const moment of brollMoments) {
    const blocked = blocking.some((b) =>
      overlaps(moment.start_frame, moment.end_frame, b.start, b.end),
    );
    if (blocked) continue;

    if (BROLL_OVERLAP_DEDUP) {
      const brollOverlap = accepted.some((b) =>
        overlaps(moment.start_frame, moment.end_frame, b.start_frame, b.end_frame),
      );
      if (brollOverlap) continue;
    }

    if (moment.step_paired != null) {
      const count = stepPairedCount.get(moment.step_paired) ?? 0;
      if (count >= BROLL_MAX_PER_STEP) continue;
      stepPairedCount.set(moment.step_paired, count + 1);
      accepted.push(moment);
      continue;
    }

    const inStepWindow = stepWindows.find((w) =>
      overlaps(moment.start_frame, moment.end_frame, w.start, w.end),
    );
    if (inStepWindow) {
      const count = stepPairedCount.get(inStepWindow.step) ?? 0;
      if (count >= BROLL_MAX_PER_STEP) continue;
      stepPairedCount.set(inStepWindow.step, count + 1);
    }

    accepted.push(moment);
  }

  return accepted;
};

const filterWithStepWindows = <T extends {start_frame: number; end_frame: number}>(
  shots: Shot[],
  moments: T[],
  stepBeats: StepBeat[],
  momentType: string,
): T[] => {
  const blocking = shotBlockingRanges(shots, momentType);
  const stepWindows = getStepWindows(shots, stepBeats);
  const accepted: T[] = [];

  for (const moment of moments) {
    const blocked = blocking.some((b) =>
      overlaps(moment.start_frame, moment.end_frame, b.start, b.end),
    );
    if (blocked) continue;

    if (overlapsStepWindow(moment.start_frame, moment.end_frame, stepWindows)) {
      continue;
    }

    const overlap = accepted.some((a) =>
      overlaps(moment.start_frame, moment.end_frame, a.start_frame, a.end_frame),
    );
    if (overlap) continue;

    accepted.push(moment);
  }

  return accepted;
};

export const filterFunMoments = (
  shots: Shot[],
  funMoments: FunMoment[],
  stepBeats: StepBeat[] = [],
): FunMoment[] => filterWithStepWindows(shots, funMoments, stepBeats, 'fun');

export const filterRoleMoments = (
  shots: Shot[],
  roleMoments: RoleMoment[],
  stepBeats: StepBeat[] = [],
): RoleMoment[] => filterWithStepWindows(shots, roleMoments, stepBeats, 'role');

export const filterLogoMoments = (
  shots: Shot[],
  logoMoments: LogoMoment[],
): LogoMoment[] => {
  const blocking = shotBlockingRanges(shots, 'logo');
  const accepted: LogoMoment[] = [];

  for (const moment of logoMoments) {
    const blocked = blocking.some((b) =>
      overlaps(moment.start_frame, moment.end_frame, b.start, b.end),
    );
    if (blocked) continue;

    const overlap = accepted.some((a) =>
      overlaps(moment.start_frame, moment.end_frame, a.start_frame, a.end_frame),
    );
    if (overlap) continue;

    accepted.push(moment);
  }

  return accepted;
};

export const filterSocialMoments = (
  shots: Shot[],
  socialMoments: SocialMoment[],
  stepBeats: StepBeat[] = [],
): SocialMoment[] => filterWithStepWindows(shots, socialMoments, stepBeats, 'social');

const momentEnd = (m: GlobalFxMoment): number =>
  m.start_frame + m.duration_frames;

const overlapsBrollPip = (
  start: number,
  end: number,
  brollMoments: BrollMoment[],
): boolean =>
  brollMoments.some((b) => {
    if (TOAST_BLOCKS_PIP_BROLL_ONLY) {
      if (b.layout === 'greenscreen' || isCompositedLayout(b.layout)) return false;
    }
    return overlaps(start, end, b.start_frame, b.end_frame);
  });

const overlapsFunRegion = (
  start: number,
  end: number,
  funMoments: FunMoment[],
): boolean =>
  funMoments.some((f) => overlaps(start, end, f.start_frame, f.end_frame));

/** Filter global FX moments — freeze/glitch/shake allowed broadly; toast region-gated. */
export const filterGlobalFxMoments = (
  shots: Shot[],
  globalFxMoments: GlobalFxMoment[],
  brollMoments: BrollMoment[] = [],
  funMoments: FunMoment[] = [],
): GlobalFxMoment[] => {
  const glitchFrames = new Set(
    globalFxMoments.filter((m) => m.type === 'glitch_burst').map((m) => m.start_frame),
  );

  const accepted: GlobalFxMoment[] = [];

  for (const moment of globalFxMoments) {
    const end = momentEnd(moment);

    if (moment.type === 'vhs_filter') {
      const competes = [...glitchFrames].some((gf) =>
        overlaps(moment.start_frame, end, gf, gf + 8),
      );
      if (competes) continue;
    }

    if (moment.type === 'notification_toast') {
      if (overlapsBrollPip(moment.start_frame, end, brollMoments)) continue;
      if (overlapsFunRegion(moment.start_frame, end, funMoments)) continue;
    }

    if (moment.type === 'freeze_stamp') {
      accepted.push(moment);
      continue;
    }

    if (moment.type === 'glitch_burst' || moment.type === 'screen_shake') {
      accepted.push(moment);
      continue;
    }

    if (moment.type === 'vhs_filter' || moment.type === 'split_wipe') {
      accepted.push(moment);
      continue;
    }

    accepted.push(moment);
  }

  return accepted;
};
