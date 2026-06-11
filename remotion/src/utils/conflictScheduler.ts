import type {BrollMoment, FunMoment, LogoMoment, RoleMoment, Shot, StepBeat} from '../types';

// BROLL_OVERLAY in shot_list is metadata only — real clips come from broll_moments.json
const BLOCKING_TYPES = new Set(['TITLE_CARD']);
const TITLE_BUFFER_FRAMES = 12;
const STEP_WINDOW_BUFFER = 60;

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
    end: b.frame + buffer + 75,
    step: b.step,
  }));
};

const overlapsStepWindow = (
  start: number,
  end: number,
  stepWindows: Array<{start: number; end: number}>,
): boolean => stepWindows.some((w) => overlaps(start, end, w.start, w.end));

export const filterBrollMoments = (
  shots: Shot[],
  brollMoments: BrollMoment[],
  stepBeats: StepBeat[] = [],
): BrollMoment[] => {
  const blocking = shots
    .filter((s) => BLOCKING_TYPES.has(s.type))
    .map((s) => ({
      start: s.start_frame,
      end:
        s.type === 'TITLE_CARD'
          ? s.end_frame + TITLE_BUFFER_FRAMES
          : s.end_frame,
      type: s.type,
    }));

  const stepWindows = getStepWindows(shots, stepBeats);
  const accepted: BrollMoment[] = [];
  const stepPairedCount = new Map<number, number>();

  for (const moment of brollMoments) {
    const blocked = blocking.some((b) =>
      overlaps(moment.start_frame, moment.end_frame, b.start, b.end),
    );
    if (blocked) continue;

    const brollOverlap = accepted.some((b) =>
      overlaps(moment.start_frame, moment.end_frame, b.start_frame, b.end_frame),
    );
    if (brollOverlap) continue;

    if (moment.step_paired != null) {
      const count = stepPairedCount.get(moment.step_paired) ?? 0;
      if (count >= 1) continue;
      stepPairedCount.set(moment.step_paired, count + 1);
      accepted.push(moment);
      continue;
    }

    const inStepWindow = stepWindows.find((w) =>
      overlaps(moment.start_frame, moment.end_frame, w.start, w.end),
    );
    if (inStepWindow) {
      const count = stepPairedCount.get(inStepWindow.step) ?? 0;
      if (count >= 1) continue;
      stepPairedCount.set(inStepWindow.step, count + 1);
    }

    accepted.push(moment);
  }

  return accepted;
};

const FUN_BLOCKING_TYPES = new Set(['TITLE_CARD']);

export const filterFunMoments = (
  shots: Shot[],
  funMoments: FunMoment[],
  stepBeats: StepBeat[] = [],
): FunMoment[] => {
  const blocking = shots
    .filter((s) => FUN_BLOCKING_TYPES.has(s.type))
    .map((s) => ({
      start: s.start_frame,
      end:
        s.type === 'TITLE_CARD'
          ? s.end_frame + TITLE_BUFFER_FRAMES
          : s.end_frame,
    }));

  const stepWindows = getStepWindows(shots, stepBeats);
  const accepted: FunMoment[] = [];

  for (const moment of funMoments) {
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

export const filterRoleMoments = (
  shots: Shot[],
  roleMoments: RoleMoment[],
  stepBeats: StepBeat[] = [],
): RoleMoment[] => {
  const blocking = shots
    .filter((s) => FUN_BLOCKING_TYPES.has(s.type))
    .map((s) => ({
      start: s.start_frame,
      end:
        s.type === 'TITLE_CARD'
          ? s.end_frame + TITLE_BUFFER_FRAMES
          : s.end_frame,
    }));

  const stepWindows = getStepWindows(shots, stepBeats);
  const accepted: RoleMoment[] = [];

  for (const moment of roleMoments) {
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

export const filterLogoMoments = (
  shots: Shot[],
  logoMoments: LogoMoment[],
): LogoMoment[] => {
  const blocking = shots
    .filter((s) => FUN_BLOCKING_TYPES.has(s.type))
    .map((s) => ({
      start: s.start_frame,
      end:
        s.type === 'TITLE_CARD'
          ? s.end_frame + TITLE_BUFFER_FRAMES
          : s.end_frame,
    }));

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
