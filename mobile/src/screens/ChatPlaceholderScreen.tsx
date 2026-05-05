import { Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export function ChatPlaceholderScreen() {
  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <View className="flex-1 items-center justify-center px-6">
        <Text className="text-ink text-xl font-semibold">Chat</Text>
        <Text className="text-ink-dim mt-2 text-center">
          Free-form coach chat lands in Session 3.
        </Text>
      </View>
    </SafeAreaView>
  );
}
