import React, {useMemo} from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {SourceVoice} from './components/SourceVoice';
import {AudioLayer} from './components/AudioLayer';
import {BrollRouter} from './components/broll/BrollRouter';
import {CompositedBrollLayer} from './components/broll/CompositedBrollLayer';
import {CaptionLayer} from './components/CaptionLayer';
import {StatCallout} from './components/StatCallout';
import {CustomVisual} from './components/CustomVisual';
import {StepChecklist} from './components/StepChecklist';
import {StepNumberFlash} from './components/StepNumberFlash';
import {TitleCard} from './components/TitleCard';
import {CountPromiseCard} from './components/CountPromiseCard';
import {WordHighlight} from './components/WordHighlight';
import {CrustFlash} from './components/CrustFlash';
import {StepPunch} from './components/StepPunch';
import {ZoomHook} from './components/ZoomHook';
import {FunRouter} from './components/fun/FunRouter';
import {LogoPop} from './components/logos/LogoPop';
import {RoleRouter} from './components/roles/RoleRouter';
import {PostFX} from './components/PostFX';
import {Watermark} from './components/Watermark';
import {MainVideo} from './components/MainVideo';
import {GlitchBurst} from './components/globalFx/GlitchBurst';
import {VHSFilter} from './components/globalFx/VHSFilter';
import {ScreenShake} from './components/globalFx/ScreenShake';
import {FreezeStampOverlay} from './components/globalFx/FreezeStampOverlay';
import {GlobalFxRouter} from './components/globalFx/GlobalFxRouter';
import {SocialRouter} from './components/social/SocialRouter';
import {SplitWipe} from './components/globalFx/SplitWipe';
import {VideoFreezeWrap} from './components/globalFx/VideoFreezeWrap';
import {OverlayScaleContext} from './OverlayScaleContext';
import {
  filterBrollMoments,
  filterFunMoments,
  filterGlobalFxMoments,
  filterLogoMoments,
  filterRoleMoments,
  filterSocialMoments,
} from './utils/conflictScheduler';
import {isCompositedMoment} from './utils/brollLayouts';
import type {Shot, Transcript, VideoProps} from './types';

const normalizeToken = (w: string) => w.toLowerCase().replace(/[^a-z0-9']/g, '');

const findPayoffFrame = (transcript: Transcript, payoffText?: string): number | undefined => {
  if (!payoffText) return undefined;

  const payoffWords = payoffText
    .toLowerCase()
    .split(/\s+/)
    .map(normalizeToken)
    .filter((w) => w.length > 2);

  if (payoffWords.length === 0) return undefined;

  const transcriptTokens = transcript.words.map((w) => normalizeToken(w.word));

  for (let i = 0; i <= transcriptTokens.length - payoffWords.length; i++) {
    let matches = 0;
    for (let j = 0; j < payoffWords.length; j++) {
      const t = transcriptTokens[i + j] ?? '';
      const p = payoffWords[j];
      if (t === p || t.includes(p) || p.includes(t)) matches++;
    }
    if (matches >= Math.ceil(payoffWords.length * 0.6)) {
      return transcript.words[i]?.start_frame;
    }
  }

  return undefined;
};

const ShotLayer: React.FC<{
  shot: Shot;
  props: VideoProps;
  closerStartFrame?: number;
  payoffFrame?: number;
  plantFrame?: number;
  wordHighlightFrames?: Set<number>;
  stepBeats?: VideoProps['stepBeats']['beats'];
  brollMoments?: VideoProps['brollMoments']['moments'];
}> = ({shot, props, closerStartFrame, payoffFrame, plantFrame, wordHighlightFrames, stepBeats = [], brollMoments = []}) => {
  const params = shot.params;
  switch (shot.type) {
    case 'TITLE_CARD':
      return (
        <TitleCard
          text={(params.text as string) ?? props.shotList.video_title}
          subtitle={(params.subtitle as string) ?? ''}
          titleVerticalPosition={props.titleVerticalPosition}
          phase={(params.phase as string) ?? 'hook'}
        />
      );
    case 'CAPTION_HIGHLIGHT':
      return (
        <CaptionLayer
          transcript={props.transcript}
          captionVerticalPosition={props.captionVerticalPosition}
          captionStyle={props.captionStyle}
          closerStartFrame={closerStartFrame}
          openLoopPayoffFrame={payoffFrame}
          openLoopPlantFrame={plantFrame}
          wordHighlightFrames={wordHighlightFrames}
          stepBeats={stepBeats}
          energyWords={props.energyWords}
          brollMoments={brollMoments}
        />
      );
    case 'STAT_CALLOUT':
      return (
        <StatCallout
          number={(params.number as string | number) ?? '0'}
          label={(params.label as string) ?? ''}
          side={(params.position as 'left' | 'right') ?? props.statCalloutSide}
          tickerEnabled={props.tickerEnabled ?? true}
        />
      );
    case 'CUSTOM_VISUAL':
      return (
        <CustomVisual
          description={(params.description as string) ?? ''}
          assetPath={(params.asset_path as string) ?? 'custom_assets/'}
          assetStatus={(params.asset_status as string) ?? 'needs_creation'}
          assetFilename={(params.asset_filename as string) ?? ''}
          layout={(params.layout as 'hero' | 'corner') ?? 'hero'}
        />
      );
    default:
      return null;
  }
};

export const VideoComposition: React.FC<VideoProps> = (props) => {
  const {
    transcript,
    shotList,
    brollMoments,
    funMoments,
    roleMoments,
    logoMoments,
    stepBeats,
    zoomIntensity,
    graphicsScale,
    videoBeats,
    globalFxMoments,
    socialMoments,
    glitchIntensity = 0.6,
    shakeIntensity = 2,
    freezeStampEnabled = false,
  } = props;
  const stepBeatList = stepBeats?.beats ?? [];
  const shots = shotList.shots ?? [];
  const totalFrames = transcript.total_frames;
  const rawGlobalFx = globalFxMoments?.moments ?? [];

  const hookShot = shots.find((s) => s.type === 'ZOOM_HOOK');
  const closerShot = shots.find((s) => s.type === 'ZOOM_CLOSER');
  const closerStartFrame = closerShot?.start_frame ?? totalFrames - 90;

  const hookIntensity =
    (hookShot?.params?.peak_scale as number) ?? zoomIntensity;

  const payoffFrame = findPayoffFrame(
    transcript,
    shotList.script_metadata?.open_loop_payoff,
  );

  const plantFrame = findPayoffFrame(
    transcript,
    shotList.script_metadata?.open_loop_plant,
  );

  const wordHighlightFrames = useMemo(() => {
    const frames = new Set<number>();
    for (const s of shots) {
      if (s.type === 'WORD_HIGHLIGHT') {
        frames.add(s.start_frame);
      }
    }
    return frames;
  }, [shots]);

  const acceptedBroll = useMemo(
    () => filterBrollMoments(shots, brollMoments.moments ?? [], stepBeatList),
    [shots, brollMoments, stepBeatList],
  );

  const legacyBroll = useMemo(
    () => acceptedBroll.filter((m) => !isCompositedMoment(m)),
    [acceptedBroll],
  );

  const acceptedFun = useMemo(
    () => filterFunMoments(shots, funMoments?.moments ?? [], stepBeatList),
    [shots, funMoments, stepBeatList],
  );

  const acceptedRoles = useMemo(
    () => filterRoleMoments(shots, roleMoments?.moments ?? [], stepBeatList),
    [shots, roleMoments, stepBeatList],
  );

  const acceptedLogos = useMemo(
    () => filterLogoMoments(shots, logoMoments?.moments ?? []),
    [shots, logoMoments],
  );

  const acceptedSocial = useMemo(
    () => filterSocialMoments(shots, socialMoments?.moments ?? [], stepBeatList),
    [shots, socialMoments, stepBeatList],
  );

  const acceptedGlobalFx = useMemo(() => {
    const filtered = filterGlobalFxMoments(
      shots,
      rawGlobalFx,
      acceptedBroll,
      acceptedFun,
    );
    if (freezeStampEnabled) {
      return filtered;
    }
    return filtered.filter((m) => m.type !== 'freeze_stamp');
  }, [shots, rawGlobalFx, acceptedBroll, acceptedFun, freezeStampEnabled]);

  const freezeMoments = useMemo(
    () => acceptedGlobalFx.filter((m) => m.type === 'freeze_stamp'),
    [acceptedGlobalFx],
  );

  const toastMoments = useMemo(
    () => acceptedGlobalFx.filter((m) => m.type === 'notification_toast'),
    [acceptedGlobalFx],
  );

  const splitWipeMoments = useMemo(
    () => acceptedGlobalFx.filter((m) => m.type === 'split_wipe'),
    [acceptedGlobalFx],
  );

  const stepChecklistEnd = payoffFrame ?? closerStartFrame;
  const stepChecklistStart = stepBeatList.length > 0
    ? Math.min(...stepBeatList.map((b) => b.frame))
    : 0;
  const stepChecklistDuration = Math.max(1, stepChecklistEnd - stepChecklistStart);
  const countPromise = shotList.script_metadata?.count_promise;
  const brand = shotList.script_metadata?.brand;
  const wordHighlightShots = shots.filter((s) => s.type === 'WORD_HIGHLIGHT');

  const videoContent = (
    <GlitchBurst moments={acceptedGlobalFx} defaultIntensity={glitchIntensity}>
      <VHSFilter moments={acceptedGlobalFx}>
        <MainVideo brollMoments={acceptedBroll} />
      </VHSFilter>
    </GlitchBurst>
  );

  return (
    <OverlayScaleContext.Provider value={graphicsScale}>
    <ScreenShake moments={acceptedGlobalFx} defaultIntensity={shakeIntensity}>
    <AbsoluteFill style={{backgroundColor: '#0C0B09'}}>
      <SourceVoice />
      <ZoomHook
        zoomIntensity={hookIntensity}
        closerStartFrame={closerStartFrame}
        totalFrames={totalFrames}
        videoBeats={videoBeats}
        stepBeats={stepBeatList}
        closerEndScale={(closerShot?.params?.end_scale as number) ?? hookIntensity}
      >
        {freezeStampEnabled ? (
          <VideoFreezeWrap moments={acceptedGlobalFx}>
            {videoContent}
          </VideoFreezeWrap>
        ) : (
          videoContent
        )}
        <CompositedBrollLayer moments={acceptedBroll} />
        <CrustFlash crustStartFrame={videoBeats?.crust_start ?? 120} />
      </ZoomHook>

      <PostFX stepBeats={stepBeatList} />

      {countPromise && (
        <Sequence from={0} durationInFrames={45} layout="none">
          <CountPromiseCard text={countPromise} />
        </Sequence>
      )}

      <StepPunch beats={stepBeatList} />
      <StepNumberFlash beats={stepBeatList} />

      {wordHighlightShots.map((shot, index) => {
        const duration = Math.max(1, shot.end_frame - shot.start_frame);
        return (
          <Sequence
            key={`word-highlight-${shot.start_frame}-${index}`}
            from={shot.start_frame}
            durationInFrames={duration}
            layout="none"
          >
            <WordHighlight word={(shot.params.word as string) ?? ''} />
          </Sequence>
        );
      })}

      {stepBeatList.length > 0 && (
        <Sequence
          from={stepChecklistStart}
          durationInFrames={stepChecklistDuration}
          layout="none"
        >
          <StepChecklist beats={stepBeatList} endFrame={stepChecklistEnd} />
        </Sequence>
      )}

      {shots.map((shot, index) => {
        if (['ZOOM_HOOK', 'ZOOM_CLOSER', 'WORD_HIGHLIGHT', 'BROLL_OVERLAY', 'STEP_REVEAL'].includes(shot.type)) {
          return null;
        }
        if (shot.type === 'CUSTOM_VISUAL' && shot.params?.asset_status !== 'ready') {
          return null;
        }
        const duration = Math.max(1, shot.end_frame - shot.start_frame);
        return (
          <Sequence
            key={`${shot.type}-${shot.start_frame}-${index}`}
            from={shot.start_frame}
            durationInFrames={duration}
            layout="none"
          >
            <ShotLayer
              shot={shot}
              props={props}
              closerStartFrame={closerStartFrame}
              payoffFrame={payoffFrame}
              plantFrame={plantFrame}
              wordHighlightFrames={wordHighlightFrames}
              stepBeats={stepBeatList}
              brollMoments={acceptedBroll}
            />
          </Sequence>
        );
      })}

      {legacyBroll.map((moment) => (
        <Sequence
          key={`broll-${moment.start_frame}-${moment.type}`}
          from={moment.start_frame}
          durationInFrames={moment.end_frame - moment.start_frame}
          layout="none"
        >
          <BrollRouter moment={moment} />
        </Sequence>
      ))}

      {acceptedFun.map((moment) => (
        <Sequence
          key={`fun-${moment.start_frame}-${moment.type}`}
          from={moment.start_frame}
          durationInFrames={moment.end_frame - moment.start_frame}
          layout="none"
        >
          <FunRouter moment={moment} />
        </Sequence>
      ))}

      {acceptedRoles.map((moment) => (
        <Sequence
          key={`role-${moment.start_frame}-${moment.role}`}
          from={moment.start_frame}
          durationInFrames={moment.end_frame - moment.start_frame}
          layout="none"
        >
          <RoleRouter moment={moment} />
        </Sequence>
      ))}

      {acceptedLogos.map((moment) => (
        <Sequence
          key={`logo-${moment.start_frame}-${moment.brand}`}
          from={moment.start_frame}
          durationInFrames={moment.end_frame - moment.start_frame}
          layout="none"
        >
          <LogoPop
            logoFile={moment.logo_file}
            label={moment.label}
            durationFrames={moment.end_frame - moment.start_frame}
            side={moment.side ?? 'right'}
          />
        </Sequence>
      ))}

      {acceptedSocial.map((moment) => (
        <Sequence
          key={`social-${moment.start_frame}-${moment.type}`}
          from={moment.start_frame}
          durationInFrames={moment.end_frame - moment.start_frame}
          layout="none"
        >
          <SocialRouter moment={moment} />
        </Sequence>
      ))}

      {freezeMoments.map((moment, index) => (
        <Sequence
          key={`freeze-stamp-${moment.start_frame}-${index}`}
          from={moment.start_frame}
          durationInFrames={moment.duration_frames}
          layout="none"
        >
          <FreezeStampOverlay
            stampText={moment.stamp_text ?? '0'}
            durationFrames={moment.duration_frames}
          />
        </Sequence>
      ))}

      {toastMoments.map((moment, index) => (
        <Sequence
          key={`toast-${moment.start_frame}-${index}`}
          from={moment.start_frame}
          durationInFrames={moment.duration_frames}
          layout="none"
        >
          <GlobalFxRouter moment={moment} />
        </Sequence>
      ))}

      {splitWipeMoments.map((moment, index) => (
        <Sequence
          key={`split-wipe-${moment.start_frame}-${index}`}
          from={moment.start_frame}
          durationInFrames={moment.duration_frames}
          layout="none"
        >
          <SplitWipe durationFrames={moment.duration_frames} />
        </Sequence>
      ))}

      <Watermark
        handle={brand?.handle ?? ''}
        opacity={brand?.watermarkOpacity ?? 0.45}
      />

      <AudioLayer
        shots={shots}
        transcript={transcript}
        brollMoments={acceptedBroll}
        funMoments={acceptedFun}
        roleMoments={acceptedRoles}
        stepBeats={stepBeatList}
        crustStartFrame={videoBeats?.crust_start}
        captionStyle={props.captionStyle}
        music={shotList.script_metadata?.music}
        energyWords={props.energyWords}
      />
    </AbsoluteFill>
    </ScreenShake>
    </OverlayScaleContext.Provider>
  );
};
