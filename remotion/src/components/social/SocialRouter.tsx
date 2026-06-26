import React from 'react';
import {AbsoluteFill} from 'remotion';
import {staticFile} from 'remotion';
import {FakeTweet} from './FakeTweet';
import {NewsHeadline} from './NewsHeadline';
import {ChatThread} from './ChatThread';
import {ReactionCutaway} from './ReactionCutaway';
import type {SocialMoment} from '../../types';

const avatarSrc = (file?: string) => (file ? staticFile(file) : undefined);

export const SocialRouter: React.FC<{moment: SocialMoment}> = ({moment}) => {
  const props = moment.props ?? {};

  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {moment.type === 'tweet' && (
        <FakeTweet
          handle={String(props.handle ?? '@creator')}
          display_name={String(props.display_name ?? 'Creator')}
          text={String(props.text ?? '')}
          verified={Boolean(props.verified)}
          avatar_file={avatarSrc(props.avatar_file as string | undefined)}
        />
      )}
      {moment.type === 'headline' && (
        <NewsHeadline
          source={String(props.source ?? 'BREAKING')}
          headline={String(props.headline ?? '')}
          subheadline={props.subheadline ? String(props.subheadline) : undefined}
        />
      )}
      {moment.type === 'chat' && (
        <ChatThread
          platform={(props.platform as 'imessage' | 'slack') ?? 'imessage'}
          messages={(props.messages as Array<{sender: string; text: string}>) ?? []}
        />
      )}
      {moment.type === 'reaction' && (
        <ReactionCutaway
          emoji={String(props.emoji ?? '🤯')}
          label={props.label ? String(props.label) : undefined}
          image_file={props.image_file as string | undefined}
        />
      )}
    </AbsoluteFill>
  );
};
