import { Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export function WeekScreen() {
  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <View className="flex-1 items-center justify-center">
        <Text className="text-ink text-xl font-semibold">Week</Text>
        <Text className="text-ink-dim mt-2">Wired in B8</Text>
      </View>
    </SafeAreaView>
  );
}
