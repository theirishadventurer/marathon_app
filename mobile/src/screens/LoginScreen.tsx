import { useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { isAxiosError } from 'axios';

import { useAuth } from '@/auth/AuthContext';

export function LoginScreen() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await login({ email: email.trim(), password });
    } catch (e) {
      if (isAxiosError(e) && e.response?.status === 401) {
        setError('Invalid email or password');
      } else if (isAxiosError(e) && e.code === 'ECONNABORTED') {
        setError('Server not reachable — check API URL');
      } else {
        setError('Could not sign in. Try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View className="flex-1 px-6 justify-center">
          <Text className="text-ink text-3xl font-bold mb-1">marathon</Text>
          <Text className="text-ink-dim mb-10">sign in to your training plan</Text>

          <Text className="text-ink-dim text-xs uppercase mb-2">Email</Text>
          <TextInput
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            textContentType="emailAddress"
            placeholder="you@example.com"
            placeholderTextColor="#6b7280"
            className="bg-bg-card text-ink rounded-lg px-4 py-3 mb-4"
          />

          <Text className="text-ink-dim text-xs uppercase mb-2">Password</Text>
          <TextInput
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            textContentType="password"
            placeholder="••••••••"
            placeholderTextColor="#6b7280"
            className="bg-bg-card text-ink rounded-lg px-4 py-3 mb-4"
          />

          {error !== null && (
            <Text className="text-accent-danger mb-4">{error}</Text>
          )}

          <Pressable
            onPress={onSubmit}
            disabled={submitting || email.length === 0 || password.length === 0}
            className="bg-accent-run rounded-lg py-4 items-center disabled:opacity-50"
          >
            {submitting ? (
              <ActivityIndicator color="#0b0b0d" />
            ) : (
              <Text className="text-bg font-semibold">Sign in</Text>
            )}
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
