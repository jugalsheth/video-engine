import React from 'react';
import {ChecklistAnimation} from './ChecklistAnimation';
import {DataFlowDiagram} from './DataFlowDiagram';
import {GrowthChart} from './GrowthChart';
import {NeuralNetwork} from './NeuralNetwork';
import {PhoneMockup} from './PhoneMockup';
import {SalaryChart} from './SalaryChart';
import {GreenscreenBroll} from './GreenscreenBroll';
import {StockVideoBroll} from './StockVideoBroll';
import {TerminalWindow} from './TerminalWindow';
import type {BrollMoment} from '../../types';

const MAP: Record<string, React.FC<{durationFrames: number}>> = {
  salary: SalaryChart,
  linkedin: PhoneMockup,
  checklist: ChecklistAnimation,
  data_flow: DataFlowDiagram,
  terminal: TerminalWindow,
  neural_network: NeuralNetwork,
  growth_chart: GrowthChart,
};

const SvgFallback: React.FC<{moment: BrollMoment}> = ({moment}) => {
  const Component = MAP[moment.type] ?? DataFlowDiagram;
  const duration = moment.end_frame - moment.start_frame;
  return <Component durationFrames={duration} />;
};

export const BrollRouter: React.FC<{moment: BrollMoment}> = ({moment}) => {
  if (moment.layout === 'greenscreen') {
    return <GreenscreenBroll moment={moment} />;
  }
  if (moment.clip_file) {
    return <StockVideoBroll moment={moment} />;
  }
  return <SvgFallback moment={moment} />;
};
