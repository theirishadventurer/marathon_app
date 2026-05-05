import './global.css';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StatusBar } from 'expo-status-bar';
import { ActivityIndicator, Text, View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AuthProvider, useAuth } from '@/auth/AuthContext';
import { LoginScreen } from '@/screens/LoginScreen';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

function PlaceholderHome() {
  const { logout } = useAuth();
  return (
    <View className="flex-1 items-center justify-center bg-bg">
      <Text className="text-ink text-lg font-semibold">Signed in</Text>
      <Text className="text-ink-dim mt-2">Tabs land in B4</Text>
      <Text
        onPress={() => {
          void logout();
        }}
        className="text-accent-danger mt-6"
      >
        Sign out
      </Text>
    </View>
  );
}

function Gate() {
  const { token, loading } = useAuth();
  if (loading) {
    return (
      <View className="flex-1 items-center justify-center bg-bg">
        <ActivityIndicator color="#34d399" />
      </View>
    );
  }
  return token === null ? <LoginScreen /> : <PlaceholderHome />;
}

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <Gate />
            <StatusBar style="light" />
          </AuthProvider>
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
