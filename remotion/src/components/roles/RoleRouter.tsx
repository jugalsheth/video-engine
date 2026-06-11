import React from 'react';
import type {RoleMoment} from '../../types';
import {RoleStage} from './RoleStage';

type Props = {
  moment: RoleMoment;
};

export const RoleRouter: React.FC<Props> = ({moment}) => {
  return <RoleStage moment={moment} />;
};
