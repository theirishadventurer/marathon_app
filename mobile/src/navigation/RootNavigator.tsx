import { createBottomTabNavigator, type BottomTabBarButtonProps } from '@react-navigation/bottom-tabs';
import { DarkTheme, NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Pressable, Text, View } from 'react-native';

import { ChatPlaceholderScreen } from '@/screens/ChatPlaceholderScreen';
import { ProgramScreen } from '@/screens/ProgramScreen';
import { SettingsScreen } from '@/screens/SettingsScreen';
import { TodayScreen } from '@/screens/TodayScreen';
import { WeekScreen } from '@/screens/WeekScreen';
import { WorkoutDetailScreen } from '@/screens/WorkoutDetailScreen';
import { colors, radius } from '@/theme/tokens';
import type { RootStackParamList, TabParamList } from './types';

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tabs = createBottomTabNavigator<TabParamList>();

const navTheme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: colors.bg,
    card: colors.bgElev,
    border: colors.line,
    primary: colors.accentRun,
    text: colors.ink,
  },
};

const tabIcon = (label: string) => ({ color }: { color: string }) =>
  <Text style={{ color, fontSize: 14, fontFamily: 'PressStart2P', textAlign: 'center' }}>{label}</Text>;

/**
 * Custom tab button: paints a filled phosphor-green rounded pill behind
 * the icon+label when focused. Inactive tabs render with no background.
 * Replaces react-navigation's default flat active-tint highlight.
 *
 * NOTE: react-navigation v7 passes `aria-selected` (not `accessibilityState`)
 * to the button factory — see BottomTabItem.js line 141. Reading
 * `accessibilityState?.selected` here would silently always evaluate to
 * false and the pill would never render.
 *
 * Spec: docs/superpowers/specs/2026-05-07-feat-staycation-ux-overhaul-design.md §5.5.
 */
function PillTabBarButton({
  children,
  onPress,
  onLongPress,
  testID,
  'aria-label': ariaLabel,
  'aria-selected': ariaSelected,
}: BottomTabBarButtonProps) {
  const focused = ariaSelected === true;
  return (
    <Pressable
      onPress={onPress}
      onLongPress={onLongPress}
      aria-label={ariaLabel}
      aria-selected={ariaSelected}
      testID={testID}
      style={{ flex: 1, alignItems: 'center', justifyContent: 'center', paddingVertical: 6 }}
    >
      <View style={{
        backgroundColor: focused ? colors.accentRun : 'transparent',
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: radius.lg,
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2,
      }}>
        {children}
      </View>
    </Pressable>
  );
}

function MainTabs() {
  return (
    <Tabs.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.bg,        // ink on green pill
        tabBarInactiveTintColor: colors.inkDim,
        tabBarButton: (props) => <PillTabBarButton {...props} />,
        tabBarStyle: {
          backgroundColor: colors.bgPanel,
          borderTopWidth: 1,
          borderTopColor: colors.line,
          height: 64,
          paddingBottom: 6,
          paddingTop: 6,
        },
        tabBarLabelStyle: {
          fontFamily: 'PressStart2P',
          fontSize: 8,
          letterSpacing: 1,
        },
      }}
    >
      <Tabs.Screen name="Today" component={TodayScreen} options={{ tabBarIcon: tabIcon('▣') }} />
      <Tabs.Screen name="Week" component={WeekScreen} options={{ tabBarIcon: tabIcon('▦') }} />
      <Tabs.Screen name="Program" component={ProgramScreen} options={{ tabBarIcon: tabIcon('▤') }} />
      <Tabs.Screen name="Chat" component={ChatPlaceholderScreen} options={{ tabBarIcon: tabIcon('◇') }} />
      <Tabs.Screen name="Settings" component={SettingsScreen} options={{ tabBarIcon: tabIcon('⚙') }} />
    </Tabs.Navigator>
  );
}

export function RootNavigator() {
  return (
    <NavigationContainer theme={navTheme}>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        <Stack.Screen name="Tabs" component={MainTabs} />
        <Stack.Screen
          name="WorkoutDetail"
          component={WorkoutDetailScreen}
          options={{ presentation: 'modal', animation: 'slide_from_bottom' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
