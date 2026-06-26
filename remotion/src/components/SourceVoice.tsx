import React from 'react';
import {Audio, staticFile} from 'remotion';

/**
 * Always-on voice bed from source.mp4.
 * All OffthreadVideo instances are muted — this is the sole speech audio track.
 */
export const SourceVoice: React.FC = () => (
  <Audio src={staticFile('source.mp4')} volume={1} />
);
