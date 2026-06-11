import React from 'react';
import {Lottie, LottieAnimationData} from '@remotion/lottie';
import {continueRender, delayRender, staticFile} from 'remotion';

type Props = {
  file?: string;
  fallbackFiles?: string[];
  width?: number;
  height?: number;
  style?: React.CSSProperties;
};

export const LottieAccent: React.FC<Props> = ({
  file = 'lottie/chart_growth.json',
  fallbackFiles = [],
  width = 48,
  height = 48,
  style,
}) => {
  const [data, setData] = React.useState<LottieAnimationData | null>(null);
  const [handle] = React.useState(() => delayRender(`lottie-${file}`));

  React.useEffect(() => {
    const paths = [file, ...fallbackFiles];
    const tryFetch = async (idx: number): Promise<LottieAnimationData | null> => {
      if (idx >= paths.length) return null;
      const r = await fetch(staticFile(paths[idx]));
      if (!r.ok) return tryFetch(idx + 1);
      const json = await r.json();
      if (!json || typeof json !== 'object') return tryFetch(idx + 1);
      return json as LottieAnimationData;
    };
    tryFetch(0)
      .then((json) => setData(json))
      .catch(() => setData(null))
      .finally(() => continueRender(handle));
  }, [file, fallbackFiles, handle]);

  if (!data) return null;

  return (
    <div style={{position: 'absolute', top: -8, right: -8, opacity: 0.85, ...style}}>
      <Lottie animationData={data} style={{width, height}} />
    </div>
  );
};
