import React from 'react';
import type {FunMoment} from '../../types';
import {ComicSFX} from './ComicSFX';
import {DoodleArrow} from './DoodleArrow';
import {EmojiPop} from './EmojiPop';
import {LottieFun} from './LottieFun';
import {MangaLines} from './MangaLines';
import {QuestionBounce} from './QuestionBounce';
import {RedXSlam} from './RedXSlam';
import {SpeechBubble} from './SpeechBubble';

type Props = {
  moment: FunMoment;
};

export const FunRouter: React.FC<Props> = ({moment}) => {
  const duration = moment.end_frame - moment.start_frame;
  const side = moment.side ?? 'right';
  const mood = moment.mood ?? 'medium';

  switch (moment.type) {
    case 'comic_sfx':
      return (
        <ComicSFX
          text={moment.text ?? 'BOOM!'}
          durationFrames={duration}
          side={side}
          mood={mood}
        />
      );
    case 'emoji_pop':
      return (
        <EmojiPop
          emoji={moment.emoji ?? '✨'}
          durationFrames={duration}
          side={side}
          mood={mood}
        />
      );
    case 'doodle_arrow':
      return <DoodleArrow durationFrames={duration} side={side} />;
    case 'speech_bubble':
      return (
        <SpeechBubble
          text={moment.text ?? moment.keyword.toUpperCase()}
          durationFrames={duration}
          side={side}
        />
      );
    case 'red_x':
      return <RedXSlam durationFrames={duration} side={side} />;
    case 'question_bounce':
      return <QuestionBounce durationFrames={duration} side={side} />;
    case 'manga_lines':
      return <MangaLines durationFrames={duration} />;
    case 'confetti':
    case 'money_rain':
    case 'fire_spark':
    case 'mind_blown':
      return (
        <LottieFun
          lottieFile={moment.lottie_file ?? `lottie/fun/${moment.type}.json`}
          durationFrames={duration}
          side={side}
          width={undefined}
          height={undefined}
        />
      );
    default:
      return (
        <EmojiPop emoji="✨" durationFrames={duration} side={side} mood={mood} />
      );
  }
};
