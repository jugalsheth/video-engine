import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT, OVERLAY_LEGIBLE, SAFE, SPRING_SNAP} from '../../layout';

export type ChatMessage = {
  sender: string;
  text: string;
};

export type ChatProps = {
  platform?: 'imessage' | 'slack';
  messages: ChatMessage[];
};

export const ChatThread: React.FC<ChatProps> = ({platform = 'imessage', messages}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const isSlack = platform === 'slack';
  const bg = isSlack ? '#1a1d21' : '#000';
  const bubbleMe = isSlack ? '#1264a3' : '#0b84ff';
  const bubbleThem = isSlack ? '#222529' : '#3a3a3c';

  return (
    <div
      style={{
        paddingLeft: SAFE.sides,
        paddingRight: SAFE.sides,
        paddingTop: SAFE.top + 80,
      }}
    >
      <div
        style={{
          backgroundColor: bg,
          borderRadius: 20,
          padding: 24,
          border: OVERLAY_LEGIBLE.pillBorder,
          boxShadow: OVERLAY_LEGIBLE.boxShadow,
          minHeight: 320,
        }}
      >
        {messages.map((msg, i) => {
          const isMe = msg.sender in {me: 1, self: 1, you: 1} || msg.sender === 'me';
          const delay = i * 6;
          const enter = spring({
            frame: Math.max(0, frame - delay),
            fps,
            config: SPRING_SNAP,
            durationInFrames: 12,
          });
          const y = interpolate(enter, [0, 1], [16, 0]);
          const opacity = interpolate(frame - delay, [0, 8], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          });

          return (
            <div
              key={`${i}-${msg.text.slice(0, 12)}`}
              style={{
                display: 'flex',
                justifyContent: isMe ? 'flex-end' : 'flex-start',
                marginBottom: 14,
                opacity,
                transform: `translateY(${y}px)`,
              }}
            >
              <div
                style={{
                  maxWidth: '78%',
                  backgroundColor: isMe ? bubbleMe : bubbleThem,
                  color: '#fff',
                  padding: '12px 16px',
                  borderRadius: isMe ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                  fontSize: FONT.body - 2,
                  lineHeight: 1.35,
                }}
              >
                {msg.text}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
