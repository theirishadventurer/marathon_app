import { Pressable, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useAuth } from '@/auth/AuthContext';

export function SettingsScreen() {
  const { logout } = useAuth();
  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <View className="flex-1 px-6 pt-4">
        <Text className="text-ink text-2xl font-bold mb-6">Settings</Text>

        <Text className="text-ink-dim text-xs uppercase mb-2">Account</Text>
        <View className="bg-bg-card rounded-lg p-4 mb-6">
          <Text className="text-ink-dim">Garmin reauth, sync status, athlete info — wired in B12</Text>
        </View>

        <Pressable
          onPress={() => {
            void logout();
          }}
          className="bg-bg-card border border-line rounded-lg py-3 items-center"
        >
          <Text className="text-accent-danger font-semibold">Sign out</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}
