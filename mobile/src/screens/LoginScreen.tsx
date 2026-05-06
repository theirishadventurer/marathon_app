import { useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { isAxiosError } from 'axios';

import { useAuth } from '@/auth/AuthContext';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { RetroButton } from '@/components/retro/RetroButton';
import { colors } from '@/theme/tokens';

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
      if (isAxiosError(e) && e.response?.status === 401) setError('INVALID LOGIN');
      else if (isAxiosError(e) && e.code === 'ECONNABORTED') setError('SERVER UNREACHABLE');
      else setError('LOGIN FAILED');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={{ flex: 1, paddingHorizontal: 24, justifyContent: 'center' }}>
          <Text style={{
            fontFamily: 'PressStart2P', fontSize: 24, color: colors.accentHi,
            marginBottom: 6, textAlign: 'center',
          }}>
            MARATHON
          </Text>
          <Text style={{
            fontFamily: 'VT323', fontSize: 18, color: colors.inkDim,
            marginBottom: 36, textAlign: 'center',
          }}>
            ▸ PRESS START
          </Text>

          <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, marginBottom: 6 }}>
            EMAIL
          </Text>
          <RetroBorder background={colors.bgPanelAlt} style={{ marginBottom: 14 }}>
            <TextInput
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
              textContentType="emailAddress"
              placeholder="you@example.com"
              placeholderTextColor={colors.inkMute}
              style={{ fontFamily: 'VT323', fontSize: 18, color: colors.ink, padding: 10 }}
            />
          </RetroBorder>

          <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, marginBottom: 6 }}>
            PASSWORD
          </Text>
          <RetroBorder background={colors.bgPanelAlt} style={{ marginBottom: 14 }}>
            <TextInput
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              textContentType="password"
              placeholder="••••••••"
              placeholderTextColor={colors.inkMute}
              style={{ fontFamily: 'VT323', fontSize: 18, color: colors.ink, padding: 10 }}
            />
          </RetroBorder>

          {error !== null && (
            <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.accentDanger, marginBottom: 12 }}>
              ! {error}
            </Text>
          )}

          {submitting ? (
            <View style={{ alignItems: 'center', paddingVertical: 12 }}>
              <ActivityIndicator color={colors.accentRun} />
            </View>
          ) : (
            <RetroButton
              label="Sign in"
              onPress={() => { void onSubmit(); }}
              disabled={email.length === 0 || password.length === 0}
              tone="primary"
            />
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
