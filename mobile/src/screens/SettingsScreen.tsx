import BottomSheet from '@gorhom/bottom-sheet';
import { useRef, useState } from 'react';
import { ActivityIndicator, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { isAxiosError } from 'axios';

import { useGarminReauth, useGarminStatus, useRequestSync } from '@/api/hooks/useGarmin';
import { usePlanCurrent } from '@/api/hooks/usePlan';
import { useAuth } from '@/auth/AuthContext';
import { BrandBanner } from '@/components/BrandBanner';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { RetroButton } from '@/components/retro/RetroButton';
import { SectionHeader } from '@/components/SectionHeader';
import { StartDateSheet } from '@/components/StartDateSheet';
import { toIso } from '@/lib/dates';
import { colors, fonts } from '@/theme/tokens';

// FUTURE: thread athlete email from /athletes/me or a user-aware AuthContext.
// For now, the BrandBanner subhead is a placeholder — the spec called for an
// email that the auth layer doesn't expose yet.
const SETTINGS_SUBHEAD = 'ATHLETE — runner@marathon.dev';

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

  const inputStyle = {
    fontFamily: fonts.body,
    fontSize: 18,
    color: colors.ink,
    paddingHorizontal: 10,
    paddingVertical: 6,
  } as const;

  return (
    <RetroBorder background={colors.bgPanelAlt} style={{ marginTop: 12 }}>
      <View style={{ padding: 14 }}>
        <Text style={{
          fontFamily: fonts.pixel, fontSize: 8, color: colors.inkDim, letterSpacing: 1, marginBottom: 8,
        }}>
          RECONNECT GARMIN
        </Text>
        <View style={{ marginBottom: 8 }}>
          <RetroBorder background={colors.bg}>
            <TextInput
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
              placeholder="garmin email"
              placeholderTextColor={colors.inkMute}
              style={inputStyle}
            />
          </RetroBorder>
        </View>
        <View style={{ marginBottom: 12 }}>
          <RetroBorder background={colors.bg}>
            <TextInput
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              placeholder="garmin password"
              placeholderTextColor={colors.inkMute}
              style={inputStyle}
            />
          </RetroBorder>
        </View>
        {error !== null && (
          <Text style={{
            fontFamily: fonts.mono, fontSize: 12, color: colors.accentDanger, marginBottom: 8,
          }}>
            {error}
          </Text>
        )}
        <RetroButton
          tone="primary"
          label={reauth.isPending ? 'Connecting…' : 'Connect'}
          onPress={() => { void submit(); }}
          disabled={reauth.isPending || email.length === 0 || password.length === 0}
        />
      </View>
    </RetroBorder>
  );
}

export function SettingsScreen() {
  const { logout } = useAuth();
  const status = useGarminStatus();
  const plan = usePlanCurrent();
  const sync = useRequestSync();
  const [showReauth, setShowReauth] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const startDateSheetRef = useRef<BottomSheet>(null);
  const today = toIso(new Date());
  const openStartDate = () => startDateSheetRef.current?.snapToIndex(0);
  const closeStartDate = () => startDateSheetRef.current?.close();

  const onSync = async () => {
    setSyncMsg(null);
    try {
      await sync.mutateAsync();
      setSyncMsg('Sync requested — your laptop agent will pick it up shortly.');
    } catch (e) {
      setSyncMsg(
        isAxiosError(e) ? (e.response?.data?.detail ?? 'Request failed.') : 'Request failed.',
      );
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top']}>
      <ScrollView contentContainerStyle={{ paddingBottom: 40 }}>
        <BrandBanner subhead={SETTINGS_SUBHEAD} />
        <View style={{ paddingHorizontal: 20, paddingTop: 4 }}>
          <SectionHeader label="Plan" />
        <RetroBorder style={{ marginBottom: 24 }}>
          <View style={{ padding: 14 }}>
            {plan.data === undefined ? (
              <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.inkDim }}>—</Text>
            ) : (
              <View>
                <Text style={{ fontFamily: fonts.monoBold, fontSize: 16, color: colors.ink }}>
                  {plan.data.plan_name}
                </Text>
                {plan.data.active_cycle !== null && (
                  <Text style={{ fontFamily: fonts.mono, fontSize: 14, color: colors.inkDim, marginTop: 6 }}>
                    Cycle: {plan.data.active_cycle.name} → {plan.data.active_cycle.race_name}
                  </Text>
                )}
                {plan.data.cycle_progress !== null && (
                  <Text style={{ fontFamily: fonts.mono, fontSize: 14, color: colors.inkDim, marginTop: 4 }}>
                    Week {plan.data.cycle_progress.week} of {plan.data.cycle_progress.total_weeks} · {plan.data.cycle_progress.days_to_race} days to race
                  </Text>
                )}
                <View style={{ marginTop: 14 }}>
                  <RetroButton label="Reset start date" onPress={openStartDate} />
                </View>
              </View>
            )}
          </View>
        </RetroBorder>

        <SectionHeader label="Garmin" />
        <RetroBorder>
          <View style={{ padding: 14 }}>
            {status.isLoading ? (
              <ActivityIndicator color={colors.accentRun} />
            ) : status.data === undefined ? (
              <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.inkDim }}>—</Text>
            ) : (
              <View>
                {status.data.needs_reauth && (
                  <View style={{
                    borderWidth: 2, borderColor: colors.accentDanger, padding: 12, marginBottom: 12,
                  }}>
                    <Text style={{
                      fontFamily: fonts.pixel, fontSize: 8, color: colors.accentDanger, letterSpacing: 1,
                    }}>
                      ! REAUTH REQUIRED
                    </Text>
                    <Text style={{
                      fontFamily: fonts.mono, fontSize: 13, color: colors.inkDim, marginTop: 6,
                    }}>
                      Garmin is asking us to log in again.
                    </Text>
                  </View>
                )}
                <Text style={{
                  fontFamily: fonts.pixel, fontSize: 8, color: colors.inkDim, letterSpacing: 1,
                }}>
                  LAST SYNC
                </Text>
                <Text style={{ fontFamily: fonts.monoBold, fontSize: 18, color: colors.ink, marginTop: 4 }}>
                  {timeAgo(status.data.last_sync)}
                </Text>
                {status.data.last_error !== null && (
                  <View style={{ marginTop: 12 }}>
                    <Text style={{
                      fontFamily: fonts.pixel, fontSize: 8, color: colors.inkDim, letterSpacing: 1,
                    }}>
                      LAST ERROR
                    </Text>
                    <Text style={{
                      fontFamily: fonts.mono, fontSize: 13, color: colors.accentDanger, marginTop: 4,
                    }}>
                      {status.data.last_error}
                    </Text>
                  </View>
                )}
                <View style={{ flexDirection: 'row', marginTop: 16, gap: 8 }}>
                  <View style={{ flex: 1 }}>
                    <RetroButton
                      tone="default"
                      label={sync.isPending ? 'Requesting…' : 'Sync now'}
                      onPress={() => { void onSync(); }}
                      disabled={sync.isPending}
                    />
                  </View>
                  <View style={{ flex: 1 }}>
                    <RetroButton
                      tone="default"
                      label={showReauth ? 'Close' : 'Reconnect'}
                      onPress={() => { setShowReauth((s) => !s); }}
                    />
                  </View>
                </View>
                {syncMsg !== null && (
                  <Text style={{
                    fontFamily: fonts.mono, fontSize: 12, color: colors.inkDim, marginTop: 12,
                  }}>
                    {syncMsg}
                  </Text>
                )}
              </View>
            )}
          </View>
        </RetroBorder>

        {showReauth && <GarminReauth onDone={() => { setShowReauth(false); }} />}

          <View style={{ marginTop: 40 }}>
            <RetroButton
              tone="danger"
              label="Sign out"
              onPress={() => { void logout(); }}
            />
          </View>
        </View>
      </ScrollView>
      <StartDateSheet
        ref={startDateSheetRef}
        defaultDate={today}
        onClose={closeStartDate}
      />
    </SafeAreaView>
  );
}
