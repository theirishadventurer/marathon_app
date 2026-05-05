import { Pressable, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { RootStackParamList } from '@/navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'WorkoutDetail'>;

export function WorkoutDetailScreen({ route, navigation }: Props) {
  const { workoutId } = route.params;
  return (
    <SafeAreaView className="flex-1 bg-bg">
      <View className="flex-1 px-6 pt-4">
        <Pressable onPress={() => { navigation.goBack(); }} className="mb-4">
          <Text className="text-accent-run">‹ Back</Text>
        </Pressable>
        <Text className="text-ink text-2xl font-bold mb-2">Workout Detail</Text>
        <Text className="text-ink-dim text-xs">id: {workoutId}</Text>
        <Text className="text-ink-dim mt-6">Wired in B11</Text>
      </View>
    </SafeAreaView>
  );
}
