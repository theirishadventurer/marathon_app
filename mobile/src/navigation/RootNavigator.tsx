import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { DarkTheme, NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Text } from 'react-native';

import { ChatPlaceholderScreen } from '@/screens/ChatPlaceholderScreen';
import { SettingsScreen } from '@/screens/SettingsScreen';
import { TodayScreen } from '@/screens/TodayScreen';
import { WeekScreen } from '@/screens/WeekScreen';
import { WorkoutDetailScreen } from '@/screens/WorkoutDetailScreen';
import { colors } from '@/theme/tokens';
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

function MainTabs() {
  return (
    <Tabs.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.accentRun,
        tabBarInactiveTintColor: colors.inkDim,
        tabBarStyle: {
          backgroundColor: colors.bgPanel,
          borderTopWidth: 2,
          borderTopColor: colors.line,
          height: 60,
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
