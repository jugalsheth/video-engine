import rules from './conflict_rules.json';

export const TITLE_BUFFER_FRAMES = rules.title_buffer_frames as number;
export const STEP_WINDOW_BUFFER = rules.step_window_buffer_frames as number;
export const STEP_BEAT_FALLBACK_DURATION = rules.step_beat_fallback_duration_frames as number;
export const COMPOSITED_LAYOUTS = new Set(rules.composited_layouts as string[]);
export const HOOK_FRAME_LIMIT = rules.hook_frame_limit as number;
export const BROLL_RATE_LIMIT_FRAMES = rules.broll_rate_limit_frames as number;
export const BROLL_STAGGER_FRAMES = rules.broll_stagger_frames as number;

const blocking = rules.blocking_shot_types as Record<string, string[]>;

export const blockingTypes = (momentType: keyof typeof blocking | string): Set<string> =>
  new Set(blocking[momentType] ?? blocking.broll ?? ['TITLE_CARD', 'CUSTOM_VISUAL']);

export const STEP_WINDOW_MOMENT_TYPES = new Set(
  (rules.step_window_moment_types as string[]) ?? ['broll', 'fun', 'role', 'social'],
);

export const BROLL_OVERLAP_DEDUP = Boolean(rules.broll_overlap_dedup);
export const BROLL_MAX_PER_STEP = (rules.broll_max_per_step as number) ?? 1;
export const TOAST_BLOCKS_PIP_BROLL_ONLY = Boolean(rules.toast_blocks_pip_broll_only);
