export const FRAME = { width: 1080, height: 1920, fps: 30 };

export const SAFE = { top: 150, bottom: 170, sides: 60 };

export const GRAPHICS_ZONE_TOP = 0.35;
export const CAPTION_ZONE = 0.52;
export const BROLL_ZONE_TOP = 0.3;

export const BRAND = {
  bg: 'rgba(12,11,9,0.88)',
  bgCaption: 'rgba(12,11,9,0.75)',
  cyan: '#00D4FF',
  amber: '#C9923A',
  text: '#F5F0E8',
};

export const SPRING_DEFAULT = { damping: 200, stiffness: 100 };
export const SPRING_STEP = { damping: 150, stiffness: 100 };
export const SPRING_SNAP = { damping: 12, stiffness: 400, mass: 0.5 };
export const SPRING_CAPCUT = { damping: 14, stiffness: 420, mass: 0.55 };

export const FONT = {
  headline: 56,
  body: 36,
  label: 28,
  caption: 38,
  stat: 72,
  step: 34,
};

export const CAPTION_VIRAL = {
  maxWords: 2,
  fontSize: 52,
  activeScale: 1.28,
  highlight: '#C9923A',
  textShadow: '0 3px 0 #000, 0 0 12px rgba(0,0,0,0.9), 2px 2px 4px rgba(0,0,0,0.8)',
  pillBg: 'rgba(12,11,9,0.65)',
};

/** Readable on bright or dark footage — dark plate + heavy shadow */
export const OVERLAY_LEGIBLE = {
  pillBg: 'rgba(8, 8, 12, 0.92)',
  pillBorder: '1.5px solid rgba(0, 212, 255, 0.4)',
  textShadow:
    '0 2px 0 #000, 0 0 14px rgba(0,0,0,0.95), 0 0 3px rgba(0,0,0,1), 1px 1px 0 #000',
  boxShadow: '0 8px 28px rgba(0,0,0,0.65)',
};

/** Base pixel sizes before graphicsScale (default 1.65 = immersive CapCut-scale) */
export const OVERLAY_BASE = {
  roleCharacter: 240,
  roleBubbleFont: 30,
  roleBubbleMaxWidth: 340,
  brollHeight: 720,
  brollWidthPct: 98,
  lottieFun: 360,
  lottieStat: 88,
  comicSfxFont: 108,
  comicSfxFontChaos: 128,
  emojiSize: 112,
  emojiSizeChaos: 140,
  sticker: 420,
};

export const overlaySize = (base: number, scale: number): number =>
  Math.round(base * scale);

/** Full-bleed cover — default A-roll */
export const MEDIA_COVER_CENTER = {
  width: '100%',
  height: '100%',
  objectFit: 'cover' as const,
  objectPosition: 'center center',
};

/** Greenscreen stock — fit entire clip, letterbox on dark panel */
export const MEDIA_CONTAIN_CENTER = {
  width: '100%',
  height: '100%',
  objectFit: 'contain' as const,
  objectPosition: 'center center',
};

/** A-roll focal point when top greenscreen panel is active (face in lower strip) */
export const AROLL_GREENSCREEN_POSITION = 'center 28%';
