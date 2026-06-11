import React from 'react';

/** Global multiplier for roles, B-roll, Lottie, stickers, comic SFX. Studio slider: graphicsScale */
export const OverlayScaleContext = React.createContext(1.65);

export const useOverlayScale = (): number => React.useContext(OverlayScaleContext);
