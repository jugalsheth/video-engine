import React from 'react';
import {
  AbsoluteFill,
  OffthreadVideo,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {ChecklistAnimation} from './ChecklistAnimation';
import {DataFlowDiagram} from './DataFlowDiagram';
import {GrowthChart} from './GrowthChart';
import {NeuralNetwork} from './NeuralNetwork';
import {PhoneMockup} from './PhoneMockup';
import {SalaryChart} from './SalaryChart';
import {TerminalWindow} from './TerminalWindow';
import {MEDIA_CONTAIN_CENTER, SPRING_DEFAULT} from '../../layout';
import type {BrollMoment} from '../../types';

const SVG_MAP: Record<string, React.FC<{durationFrames: number}>> = {
  salary: SalaryChart,
  linkedin: PhoneMockup,
  checklist: ChecklistAnimation,
  data_flow: DataFlowDiagram,
  terminal: TerminalWindow,
  neural_network: NeuralNetwork,
  growth_chart: GrowthChart,
};

type Props = {
  moment: BrollMoment;
};

export const GreenscreenBroll: React.FC<Props> = ({moment}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const duration = moment.end_frame - moment.start_frame;

  const fadeIn = spring({frame, fps, config: SPRING_DEFAULT, durationInFrames: 10});
  const fadeOut = spring({
    frame: Math.max(0, frame - (duration - 10)),
    fps,
    config: SPRING_DEFAULT,
    durationInFrames: 10,
  });
  const opacity = frame < duration - 10 ? fadeIn : 1 - fadeOut;

  const SvgComponent = SVG_MAP[moment.type] ?? DataFlowDiagram;

  return (
    <AbsoluteFill style={{opacity, pointerEvents: 'none'}}>
      <AbsoluteFill
        style={{
          height: '62%',
          overflow: 'hidden',
          backgroundColor: '#0C0B09',
          borderBottom: '3px solid rgba(0,212,255,0.35)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        {moment.clip_file ? (
          <OffthreadVideo
            src={staticFile(moment.clip_file)}
            style={MEDIA_CONTAIN_CENTER}
            muted
          />
        ) : (
          <AbsoluteFill
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              padding: 24,
            }}
          >
            <SvgComponent durationFrames={duration} />
          </AbsoluteFill>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
