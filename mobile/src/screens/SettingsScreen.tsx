import { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { isAxiosError } from 'axios';

import { useGarminReauth, useGarminStatus, useManualSync } from '@/api/hooks/useGarmin';
import { usePlanCurrent } from '@/api/hooks/usePlan';
import { useAuth } from '@/auth/AuthContext';
import { colors } from '@/theme/tokens';

function timeAgo(iso: string | null): string {
  if (iso === null) return 'never';
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diffMin = Math.round((now - then) / 60_000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.round(diffHr / 24);
  return `${diffDay}d ago`;
}

function GarminReauth({ onDone }: { onDone: () => void }) {
  const reauth = useGarminReauth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setError(null);
    try {
      await reauth.mutateAsync({ email: email.trim(), password });
      setEmail('');
      setPassword('');
      onDone();
    } catch (e) {
      if (isAxiosError(e)) {
        setError(e.response?.data?.detail ?? 'Reauth failed.');
      } else {
        setError('Reauth failed.');
      }
    }
  };

  return (
    <View className="bg-bg-card rounded-xl p-4 border border-line mt-3">
      <Text className="text-ink-dim text-xs uppercase mb-3">Reconnect Garmin</Text>
      <TextInput
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="email-address"
        placeholder="garmin email"
        placeholderTextColor={colors.inkMute}
        className="bg-bg text-ink rounded-lg px-3 py-2 mb-2"
      />
      <TextInput
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        placeholder="garmin password"
        placeholderTextColor={colors.inkMute}
        className="bg-bg text-ink rounded-lg px-3 py-2 mb-3"
      />
      {error !== null && (
        <Text className="text-accent-danger text-sm mb-2">{error}</Text>
      )}
      <Pressable
        onPress={() => { void submit(); }}
        disabled={reauth.isPending || email.length === 0 || password.length === 0}
        className="bg-accent-run rounded-lg py-2 items-center disabled:opacity-50"
      >
        {reauth.isPending ? (
          <ActivityIndicator color={colors.bg} />
        ) : (
          <Text style={{ color: colors.bg, fontWeight: '600' }}>Connect</Text>
        )}
      </Pressable>
    </View>
  );
}

export function SettingsScreen() {
  const { logout } = useAuth();
  const status = useGarminStatus();
  const plan = usePlanCurrent();
  const sync = useManualSync();
  const [showReauth, setShowReauth] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);

  const onSync = async () => {
    setSyncMsg(null);
    try {
      const report = await sync.mutateAsync();
      setSyncMsg(
        `Synced ${report.synced_activities} activities, ${report.synced_metrics} metrics.${
          report.errors.length > 0 ? ` ${report.errors.length} error(s).` : ''
        }`,
      );
    } catch (e) {
      setSyncMsg(isAxiosError(e) ? (e.response?.data?.detail ?? 'Sync failed.') : 'Sync failed.');
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        <Text className="text-ink text-2xl font-bold mb-6">Settings</Text>

        <Text className="text-ink-dim text-xs uppercase mb-2">Plan</Text>
        <View className="bg-bg-card rounded-xl p-4 border border-line mb-6">
          {plan.data === undefined ? (
            <Text className="text-ink-dim">—</Text>
          ) : (
            <View>
              <Text className="text-ink text-base font-semibold">{plan.data.plan_name}</Text>
              {plan.data.active_cycle !== null && (
                <Text className="text-ink-dim text-sm mt-1">
                  Cycle: {plan.data.active_cycle.name} → {plan.data.active_cycle.race_name}
                </Text>
              )}
              {plan.data.cycle_progress !== null && (
                <Text className="text-ink-dim text-sm mt-1">
                  Week {plan.data.cycle_progress.week} of {plan.data.cycle_progress.total_weeks} · {plan.data.cycle_progress.days_to_race} days to race
                </Text>
              )}
            </View>
          )}
        </View>

        <Text className="text-ink-dim text-xs uppercase mb-2">Garmin</Text>
        <View className="bg-bg-card rounded-xl p-4 border border-line">
          {status.isLoading ? (
            <ActivityIndicator color={colors.accentRun} />
          ) : status.data === undefined ? (
            <Text className="text-ink-dim">—</Text>
          ) : (
            <View>
              {status.data.needs_reauth && (
                <View className="bg-bg rounded-lg p-3 border border-accent-danger mb-3">
                  <Text style={{ color: colors.accentDanger, fontWeight: '600' }}>
                    Reauth required
                  </Text>
                  <Text className="text-ink-dim text-xs mt-1">
                    Garmin is asking us to log in again.
                  </Text>
                </View>
              )}
              <Text className="text-ink-dim text-xs">Last sync</Text>
              <Text className="text-ink text-sm font-semibold">
                {timeAgo(status.data.last_sync)}
              </Text>
              {status.data.last_error !== null && (
                <View className="mt-3">
                  <Text className="text-ink-dim text-xs">Last error</Text>
                  <Text style={{ color: colors.accentDanger }} className="text-sm">
                    {status.data.last_error}
                  </Text>
                </View>
              )}
              <View className="flex-row mt-4 gap-x-3">
                <Pressable
                  onPress={() => { void onSync(); }}
                  disabled={sync.isPending}
                  className="flex-1 border border-line rounded-lg py-2 items-center disabled:opacity-50"
                >
                  {sync.isPending ? (
                    <ActivityIndicator color={colors.ink} />
                  ) : (
                    <Text className="text-ink font-semibold">Sync now</Text>
                  )}
                </Pressable>
                <Pressable
                  onPress={() => { setShowReauth((s) => !s); }}
                  className="flex-1 border border-line rounded-lg py-2 items-center"
                >
                  <Text className="text-ink font-semibold">
                    {showReauth ? 'Close' : 'Reconnect'}
                  </Text>
                </Pressable>
              </View>
              {syncMsg !== null && (
                <Text className="text-ink-dim text-xs mt-3">{syncMsg}</Text>
              )}
            </View>
          )}
        </View>

        {showReauth && <GarminReauth onDone={() => { setShowReauth(false); }} />}

        <View className="mt-10">
          <Pressable
            onPress={() => { void logout(); }}
            className="bg-bg-card border border-line rounded-lg py-3 items-center"
          >
            <Text style={{ color: colors.accentDanger, fontWeight: '600' }}>Sign out</Text>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
