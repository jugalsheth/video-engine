import React from 'react';
import {Composition, staticFile} from 'remotion';
import {z} from 'zod';
import {VideoComposition} from './VideoComposition';
import type {BrollData, FunData, LogoData, RoleData, ShotList, StepBeatData, Transcript, VideoBeats, VideoProps} from './types';

export const videoSchema = z.object({
  titleVerticalPosition: z.number().default(15),
  captionVerticalPosition: z.number().default(52),
  captionStyle: z.enum(['viral', 'classic']).default('viral'),
  zoomIntensity: z.number().default(1.18),
  graphicsScale: z.number().min(0.8).max(2.2).default(1.65),
  statCalloutSide: z.enum(['left', 'right']).default('right'),
});

const emptyTranscript: Transcript = {
  full_text: '',
  words: [],
  duration_seconds: 0,
  total_frames: 300,
  fps: 30,
};

const emptyShotList: ShotList = {
  video_title: 'Preview',
  territory: '',
  total_frames: 300,
  fps: 30,
  caption_for_posting: '',
  hashtags: [],
  shots: [],
};

const emptyBroll: BrollData = {
  moments: [],
  skipped: [],
  summary: {detected: 0, skipped: 0, types: []},
};

const emptyFun: FunData = {
  mood: 'medium',
  moments: [],
  skipped: [],
  summary: {detected: 0, skipped: 0, mood: 'medium', types: []},
};

const emptyRoles: RoleData = {
  mood: 'medium',
  moments: [],
  skipped: [],
  summary: {detected: 0, skipped: 0, mood: 'medium', roles: []},
};

const emptyLogos: LogoData = {
  moments: [],
  skipped: [],
  summary: {detected: 0, skipped: 0, brands: []},
};

const emptyStepBeats: StepBeatData = {
  beats: [],
  summary: {count: 0, steps: [], source: 'none'},
};

const defaultBeats: VideoBeats = {
  hook_start: 0,
  hook_end: 90,
  crust_start: 120,
  pause_frames: 8,
  setup_zoom: 1.05,
  crust_zoom_peak: 1.26,
  crust_settle: 1.1,
};

const defaultProps: VideoProps = {
  titleVerticalPosition: 15,
  captionVerticalPosition: 52,
  captionStyle: 'viral',
  zoomIntensity: 1.18,
  graphicsScale: 1.65,
  statCalloutSide: 'right',
  transcript: emptyTranscript,
  shotList: emptyShotList,
  brollMoments: emptyBroll,
  funMoments: emptyFun,
  roleMoments: emptyRoles,
  logoMoments: emptyLogos,
  stepBeats: emptyStepBeats,
  videoBeats: defaultBeats,
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="VideoComposition"
      component={VideoComposition}
      durationInFrames={300}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={defaultProps}
      schema={videoSchema}
      calculateMetadata={async ({props, abortSignal}) => {
        const [transcript, shotList, brollMoments, funMoments, roleMoments, logoMoments, stepBeats, videoBeats] =
          await Promise.all([
          fetch(staticFile('transcript.json'), {signal: abortSignal}).then((r) => r.json() as Promise<Transcript>),
          fetch(staticFile('shot_list.json'), {signal: abortSignal}).then((r) => r.json() as Promise<ShotList>),
          fetch(staticFile('broll_moments.json'), {signal: abortSignal}).then((r) => r.json() as Promise<BrollData>),
          fetch(staticFile('fun_moments.json'), {signal: abortSignal})
            .then((r) => (r.ok ? r.json() : emptyFun) as Promise<FunData>)
            .catch(() => emptyFun),
          fetch(staticFile('role_moments.json'), {signal: abortSignal})
            .then((r) => (r.ok ? r.json() : emptyRoles) as Promise<RoleData>)
            .catch(() => emptyRoles),
          fetch(staticFile('logo_moments.json'), {signal: abortSignal})
            .then((r) => (r.ok ? r.json() : emptyLogos) as Promise<LogoData>)
            .catch(() => emptyLogos),
          fetch(staticFile('step_beats.json'), {signal: abortSignal})
            .then((r) => (r.ok ? r.json() : emptyStepBeats) as Promise<StepBeatData>)
            .catch(() => emptyStepBeats),
          fetch(staticFile('video_beats.json'), {signal: abortSignal})
            .then((r) => (r.ok ? r.json() : defaultBeats) as Promise<VideoBeats>)
            .catch(() => defaultBeats),
        ]);

        return {
          durationInFrames: transcript.total_frames,
          fps: transcript.fps ?? 30,
          props: {
            ...props,
            transcript,
            shotList,
            brollMoments,
            funMoments,
            roleMoments,
            logoMoments,
            stepBeats,
            videoBeats,
          },
        };
      }}
    />
  );
};
