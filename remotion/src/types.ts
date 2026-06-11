export type WordTimestamp = {
  word: string;
  start: number;
  end: number;
  start_frame: number;
  end_frame: number;
};

export type Transcript = {
  full_text: string;
  words: WordTimestamp[];
  duration_seconds: number;
  total_frames: number;
  fps: number;
};

export type Shot = {
  type: string;
  start_frame: number;
  end_frame: number;
  params: Record<string, unknown>;
};

export type ShotList = {
  video_title: string;
  territory: string;
  total_frames: number;
  fps: number;
  caption_for_posting: string;
  hashtags: string[];
  shots: Shot[];
  script_metadata?: {
    title_overlay?: string;
    subtitle_overlay?: string;
    open_loop_plant?: string;
    open_loop_payoff?: string;
    hook_type?: string;
    script_number?: number;
    count_promise?: string;
    brand?: {
      handle?: string;
      headlineFont?: string;
      bodyFont?: string;
      stepNumberColor?: string;
      watermarkOpacity?: number;
    };
    music?: {
      key?: string;
      file?: string;
      volume_speaking?: number;
      volume_idle?: number;
    };
  };
};

export type BrollMoment = {
  type: string;
  start_frame: number;
  end_frame: number;
  keyword: string;
  word: string;
  clip_file?: string;
  source?: string;
  search_query?: string;
  layout?: 'pip' | 'greenscreen';
  side?: 'left' | 'right';
  step_paired?: number;
};

export type BrollData = {
  moments: BrollMoment[];
  skipped: Array<BrollMoment & { reason?: string }>;
  summary: { detected: number; skipped: number; types: string[] };
};

export type FunMoment = {
  type: string;
  start_frame: number;
  end_frame: number;
  keyword: string;
  mood?: 'medium' | 'chaos';
  side?: 'left' | 'right' | 'center';
  text?: string;
  emoji?: string;
  lottie_file?: string;
};

export type FunData = {
  mood: 'medium' | 'chaos';
  moments: FunMoment[];
  skipped: Array<FunMoment & { reason?: string }>;
  summary: { detected: number; skipped: number; mood: string; types: string[] };
};

export type RoleMoment = {
  role: string;
  pose: string;
  line: string;
  start_frame: number;
  end_frame: number;
  keyword: string;
  mood?: 'medium' | 'chaos';
  side?: 'left' | 'right';
  is_callback?: boolean;
};

export type RoleData = {
  mood: 'medium' | 'chaos';
  moments: RoleMoment[];
  skipped: Array<RoleMoment & { reason?: string }>;
  summary: { detected: number; skipped: number; mood: string; roles: string[] };
};

export type LogoMoment = {
  type: 'logo_pop';
  brand: string;
  logo_file: string;
  label?: string;
  start_frame: number;
  end_frame: number;
  keyword: string;
  side?: 'left' | 'right';
};

export type LogoData = {
  moments: LogoMoment[];
  skipped: Array<LogoMoment & { reason?: string }>;
  summary: { detected: number; skipped: number; brands: string[] };
};

export type StepBeat = {
  step: number;
  frame: number;
  label?: string;
  source?: string;
};

export type StepBeatData = {
  beats: StepBeat[];
  summary?: {
    count: number;
    steps: number[];
    source?: string;
  };
};

export type VideoBeats = {
  hook_start: number;
  hook_end: number;
  crust_start: number;
  pause_frames: number;
  setup_zoom: number;
  crust_zoom_peak: number;
  crust_settle: number;
  summary?: {
    hook_seconds: number;
    crust_seconds: number;
    pause_ms: number;
  };
};

export type VideoProps = {
  titleVerticalPosition: number;
  captionVerticalPosition: number;
  captionStyle: 'viral' | 'classic';
  zoomIntensity: number;
  graphicsScale: number;
  statCalloutSide: 'left' | 'right';
  transcript: Transcript;
  shotList: ShotList;
  brollMoments: BrollData;
  funMoments: FunData;
  roleMoments: RoleData;
  logoMoments: LogoData;
  stepBeats: StepBeatData;
  videoBeats: VideoBeats;
};
