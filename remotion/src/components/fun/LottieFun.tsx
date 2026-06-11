import React from 'react';
import {Lottie, LottieAnimationData} from '@remotion/lottie';
import {continueRender, delayRender, staticFile} from 'remotion';
import {useOverlayScale} from '../../OverlayScaleContext';
import {OVERLAY_BASE, overlaySize} from '../../layout';
import {FunBase} from './FunBase';

type Props = {
  lottieFile: string;
  durationFrames: number;
  side?: 'left' | 'right' | 'center';
  width?: number;
  height?: number;
};

export const LottieFun: React.FC<Props> = ({
  lottieFile,
  durationFrames,
  side = 'center',
  width,
  height,
}) => {
  const scale = useOverlayScale();
  const w = width ?? overlaySize(OVERLAY_BASE.lottieFun, scale);
  const h = height ?? overlaySize(OVERLAY_BASE.lottieFun, scale);
  const [data, setData] = React.useState<LottieAnimationData | null>(null);
  const [handle] = React.useState(() => delayRender(`fun-lottie-${lottieFile}`));

  React.useEffect(() => {
    fetch(staticFile(lottieFile))
      .then((r) => (r.ok ? r.json() : null))
      .then((json) => setData(json))
      .catch(() => setData(null))
      .finally(() => continueRender(handle));
  }, [lottieFile, handle]);

  if (!data) return null;

  return (
    <FunBase durationFrames={durationFrames} side={side} zone="corner">
      <Lottie animationData={data} style={{width: w, height: h}} />
    </FunBase>
  );
};
