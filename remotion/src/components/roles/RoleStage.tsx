import React from 'react';
import type {RoleMoment} from '../../types';
import {MangaLines} from '../fun/MangaLines';
import {RoleBase} from './RoleBase';
import {RoleBubble} from './RoleBubble';
import {RoleCharacter} from './RoleCharacter';

const ACCENTS: Record<string, string> = {
  victim: '#7B68A6',
  hype: '#E8A838',
  skeptic: '#5A6A7A',
  expert: '#00D4FF',
  gremlin: '#4CAF50',
};

type Props = {
  moment: RoleMoment;
};

export const RoleStage: React.FC<Props> = ({moment}) => {
  const duration = moment.end_frame - moment.start_frame;
  const side = moment.side ?? 'left';

  return (
    <>
      {moment.role === 'gremlin' && moment.mood === 'chaos' && (
        <MangaLines durationFrames={duration} />
      )}
      <RoleBase
        durationFrames={duration}
        side={side}
        isCallback={moment.is_callback}
      >
        <RoleBubble
          text={moment.line}
          side={side}
          accent={ACCENTS[moment.role] ?? '#C9923A'}
        />
        <RoleCharacter role={moment.role} pose={moment.pose} />
      </RoleBase>
    </>
  );
};
