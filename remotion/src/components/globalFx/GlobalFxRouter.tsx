import React from 'react';
import type {GlobalFxMoment} from '../../types';
import {NotificationToast} from './NotificationToast';

type Props = {
  moment: GlobalFxMoment;
};

export const GlobalFxRouter: React.FC<Props> = ({moment}) => {
  const duration = moment.duration_frames;

  switch (moment.type) {
    case 'notification_toast':
      return (
        <NotificationToast
          toastText={moment.toast_text ?? '12 new'}
          toastIcon={moment.toast_icon}
          side={moment.side ?? 'right'}
          durationFrames={duration}
        />
      );
    default:
      return null;
  }
};
