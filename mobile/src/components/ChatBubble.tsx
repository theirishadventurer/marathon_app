import { View } from 'react-native';
import Markdown from 'react-native-markdown-display';

import { colors, fonts } from '@/theme/tokens';

interface Props {
  role: 'user' | 'assistant';
  contentMd: string;
}

export function ChatBubble({ role, contentMd }: Props) {
  const isUser = role === 'user';
  return (
    <View
      style={{
        alignSelf: isUser ? 'flex-end' : 'flex-start',
        maxWidth: '85%',
        marginVertical: 4,
        marginHorizontal: 12,
        padding: 12,
        backgroundColor: isUser ? colors.bgPanel : colors.bg,
        borderWidth: 2,
        borderColor: isUser ? colors.accentRun : colors.line,
      }}
    >
      <Markdown
        style={{
          body: { color: colors.ink, fontFamily: fonts.body, fontSize: 16, lineHeight: 22 },
          strong: { fontFamily: fonts.monoBold, color: colors.ink },
          link: { color: colors.accentRun },
          code_inline: { fontFamily: fonts.mono, color: colors.accentRun },
        }}
      >
        {contentMd}
      </Markdown>
    </View>
  );
}
