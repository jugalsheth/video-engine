import React, {createContext, useContext} from 'react';

type ZoomScaleContextValue = {
  scale: number;
};

export const ZoomScaleContext = createContext<ZoomScaleContextValue>({
  scale: 1,
});

export const useZoomScale = (): number => useContext(ZoomScaleContext).scale;

export const ZoomScaleProvider: React.FC<{
  scale: number;
  children: React.ReactNode;
}> = ({scale, children}) => (
  <ZoomScaleContext.Provider value={{scale}}>{children}</ZoomScaleContext.Provider>
);
