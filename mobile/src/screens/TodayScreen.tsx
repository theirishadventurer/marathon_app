import { Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export function TodayScreen() {
  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <View className="flex-1 items-center justify-center">
        <Text className="text-ink text-xl font-semibold">Today</Text>
        <Text className="text-ink-dim mt-2">Wired in B5</Text>
      </View>
    </SafeAreaView>
  );
}
