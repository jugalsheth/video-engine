import React, {useMemo} from 'react';
import {Audio, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {BrollMoment, FunMoment, RoleMoment, Shot, StepBeat, Transcript} from '../types';

type MusicConfig = {
  file?: string;
  volume_speaking?: number;
  volume_idle?: number;
};

type Props = {
  shots: Shot[];
  transcript: Transcript;
  brollMoments?: BrollMoment[];
  funMoments?: FunMoment[];
  roleMoments?: RoleMoment[];
  stepBeats?: StepBeat[];
  crustStartFrame?: number;
  captionStyle?: 'viral' | 'classic';
  music?: MusicConfig;
  energyWords?: string[];
};

const musicFile = (file?: string) =>
  staticFile(file ? `music/${file}` : 'music/background.mp3');

const DuckingMusic: React.FC<{transcript: Transcript; music?: MusicConfig}> = ({
  transcript,
  music,
}) => {
  const frame = useCurrentFrame();
  const isSpeaking = transcript.words.some(
    (w) => frame >= w.start_frame && frame <= w.end_frame + 2,
  );
  const volSpeaking = music?.volume_speaking ?? 0.03;
  const volIdle = music?.volume_idle ?? 0.07;
  return (
    <Audio
      src={musicFile(music?.file)}
      volume={isSpeaking ? volSpeaking : volIdle}
      loop
    />
  );
};

export const AudioLayer: React.FC<Props> = ({
  shots,
  transcript,
  brollMoments = [],
  funMoments = [],
  roleMoments = [],
  stepBeats = [],
  crustStartFrame,
  captionStyle = 'viral',
  music,
  energyWords = [],
}) => {
  const {fps} = useVideoConfig();

  const statShots = shots.filter((s) => s.type === 'STAT_CALLOUT');
  const stepShots = shots.filter((s) => s.type === 'STEP_REVEAL');
  const punchBeats: StepBeat[] =
    stepBeats.length > 0
      ? stepBeats
      : stepShots.map((s) => ({
          step: (s.params?.step_number as number) ?? 1,
          frame: s.start_frame,
        }));

  const highlightTicks = useMemo(() => {
    if (captionStyle !== 'viral') return [];
    const energy = new Set([
      'right', 'unless', 'listen', "that's", 'wait', 'but', 'now', 'truth',
      'secret', 'wild', 'finally', 'wrong',
      ...energyWords.map((w) => w.toLowerCase().replace(/[^a-z']/g, '')),
    ]);
    const frames: number[] = [];
    let last = -45;
    for (const w of transcript.words) {
      const token = w.word.toLowerCase().replace(/[^a-z']/g, '');
      if (!energy.has(token)) continue;
      if (w.start_frame < last + 45) continue;
      frames.push(w.start_frame);
      last = w.start_frame;
    }
    return frames;
  }, [transcript.words, captionStyle, energyWords]);

  return (
    <>
      <DuckingMusic transcript={transcript} music={music} />
      <Sequence from={0} durationInFrames={20}>
        <Audio src={staticFile('sfx/impact.wav')} volume={0.48} />
      </Sequence>
      {crustStartFrame != null && crustStartFrame > 30 && (
        <Sequence from={crustStartFrame} durationInFrames={22}>
          <Audio src={staticFile('sfx/impact.wav')} volume={0.55} />
        </Sequence>
      )}
      {statShots.map((s) => (
        <Sequence key={`pop-${s.start_frame}`} from={s.start_frame} durationInFrames={fps}>
          <Audio src={staticFile('sfx/pop.wav')} volume={0.38} />
        </Sequence>
      ))}
      {punchBeats.map((beat) => (
        <Sequence
          key={`step-punch-${beat.frame}-${beat.step}`}
          from={beat.frame}
          durationInFrames={18}
        >
          <Audio src={staticFile('sfx/impact.wav')} volume={0.42} />
        </Sequence>
      ))}
      {punchBeats.map((beat) => (
        <Sequence
          key={`step-swoosh-${beat.frame}-${beat.step}`}
          from={beat.frame + 2}
          durationInFrames={14}
        >
          <Audio src={staticFile('sfx/swoosh.wav')} volume={0.28} />
        </Sequence>
      ))}
      {highlightTicks.map((f) => (
        <Sequence key={`cap-tick-${f}`} from={f} durationInFrames={4}>
          <Audio src={staticFile('sfx/tick.wav')} volume={0.1} />
        </Sequence>
      ))}
      {brollMoments.map((m) => (
        <Sequence
          key={`swoosh-${m.start_frame}`}
          from={m.start_frame}
          durationInFrames={Math.min(30, fps)}
        >
          <Audio src={staticFile('sfx/swoosh.wav')} volume={0.22} />
        </Sequence>
      ))}
      {funMoments.map((m) => {
        const sfx =
          m.type === 'confetti' || m.type === 'mind_blown' || m.type === 'comic_sfx'
            ? 'sfx/pop.wav'
            : m.type === 'money_rain' || m.type === 'fire_spark'
              ? 'sfx/swoosh.wav'
              : 'sfx/tick.wav';
        return (
          <Sequence
            key={`fun-sfx-${m.start_frame}-${m.type}`}
            from={m.start_frame}
            durationInFrames={Math.min(20, fps)}
          >
            <Audio src={staticFile(sfx)} volume={0.28} />
          </Sequence>
        );
      })}
      {roleMoments.map((m) => (
        <Sequence
          key={`role-sfx-${m.start_frame}-${m.role}`}
          from={m.start_frame}
          durationInFrames={Math.min(18, fps)}
        >
          <Audio
            src={staticFile(
              m.role === 'hype' || m.role === 'gremlin'
                ? 'sfx/pop.wav'
                : 'sfx/tick.wav',
            )}
            volume={0.3}
          />
        </Sequence>
      ))}
    </>
  );
};
