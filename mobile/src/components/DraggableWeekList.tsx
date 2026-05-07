import * as Haptics from 'expo-haptics';
import { useRef } from 'react';
import { Text, View, type LayoutChangeEvent } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, {
  runOnJS,
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';

import type { PlannedWorkoutOut, WeekOut } from '@/api/types';
import { WorkoutCard } from '@/components/WorkoutCard';
import { dayName, fromIso, toIso } from '@/lib/dates';
import { colors, fonts } from '@/theme/tokens';

interface DayFrame {
  date: string;
  pageY: number;
  height: number;
}

interface Props {
  week: WeekOut;
  onWorkoutPress: (w: PlannedWorkoutOut) => void;
  onMoveRequest: (w: PlannedWorkoutOut, newDate: string) => void;
  disabled?: boolean;
}

function impact(kind: 'light' | 'medium' | 'selection') {
  if (kind === 'selection') {
    void Haptics.selectionAsync();
    return;
  }
  void Haptics.impactAsync(
    kind === 'light' ? Haptics.ImpactFeedbackStyle.Light : Haptics.ImpactFeedbackStyle.Medium,
  );
}

interface DraggableProps {
  workout: PlannedWorkoutOut;
  dayFrames: { value: DayFrame[] };
  hoveredDate: { value: string | null };
  onPress: () => void;
  onMove: (newDate: string) => void;
  disabled: boolean;
}

function DraggableWorkout({
  workout,
  dayFrames,
  hoveredDate,
  onPress,
  onMove,
  disabled,
}: DraggableProps) {
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const scale = useSharedValue(1);
  const elevation = useSharedValue(0);

  const handleHover = (date: string | null) => {
    if (date !== null && date !== workout.scheduled_date) impact('selection');
  };

  const handleDrop = (date: string | null) => {
    if (date !== null && date !== workout.scheduled_date) {
      impact('medium');
      onMove(date);
    }
  };

  const pan = Gesture.Pan()
    .enabled(!disabled && workout.status !== 'done')
    .activateAfterLongPress(300)
    .onStart(() => {
      'worklet';
      scale.value = withSpring(1.05, { damping: 12, stiffness: 220 });
      elevation.value = 10;
      runOnJS(impact)('light');
    })
    .onUpdate((e) => {
      'worklet';
      translateX.value = e.translationX;
      translateY.value = e.translationY;
      let newHover: string | null = null;
      for (const f of dayFrames.value) {
        if (e.absoluteY >= f.pageY && e.absoluteY < f.pageY + f.height) {
          newHover = f.date;
          break;
        }
      }
      if (newHover !== hoveredDate.value) {
        hoveredDate.value = newHover;
        runOnJS(handleHover)(newHover);
      }
    })
    .onEnd((e) => {
      'worklet';
      let dropDate: string | null = null;
      for (const f of dayFrames.value) {
        if (e.absoluteY >= f.pageY && e.absoluteY < f.pageY + f.height) {
          dropDate = f.date;
          break;
        }
      }
      hoveredDate.value = null;
      translateX.value = withSpring(0, { damping: 18, stiffness: 220 });
      translateY.value = withSpring(0, { damping: 18, stiffness: 220 });
      scale.value = withSpring(1);
      elevation.value = 0;
      runOnJS(handleDrop)(dropDate);
    });

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: translateX.value },
      { translateY: translateY.value },
      { scale: scale.value },
    ],
    zIndex: elevation.value > 0 ? 50 : 0,
    elevation: elevation.value,
    shadowColor: '#000',
    shadowOpacity: elevation.value > 0 ? 0.4 : 0,
    shadowRadius: elevation.value > 0 ? 12 : 0,
    shadowOffset: { width: 0, height: elevation.value > 0 ? 8 : 0 },
  }));

  return (
    <GestureDetector gesture={pan}>
      <Animated.View style={animatedStyle}>
        <WorkoutCard workout={workout} onPress={onPress} />
      </Animated.View>
    </GestureDetector>
  );
}

interface DropZoneProps {
  date: string;
  hoveredDate: { value: string | null };
  children: React.ReactNode;
  onLayoutMeasure: () => void;
  measureRef: (el: View | null) => void;
}

function DropZone({ date, hoveredDate, children, onLayoutMeasure, measureRef }: DropZoneProps) {
  const animatedStyle = useAnimatedStyle(() => ({
    backgroundColor:
      hoveredDate.value === date ? `${colors.accentRun}1A` : 'transparent',
    borderRadius: 12,
  }));
  const handleLayout = (_: LayoutChangeEvent) => {
    onLayoutMeasure();
  };
  return (
    <Animated.View ref={measureRef} onLayout={handleLayout} style={animatedStyle}>
      {children}
    </Animated.View>
  );
}

export function DraggableWeekList({
  week,
  onWorkoutPress,
  onMoveRequest,
  disabled = false,
}: Props) {
  const dayFrames = useSharedValue<DayFrame[]>([]);
  const hoveredDate = useSharedValue<string | null>(null);
  const refs = useRef<Record<string, View | null>>({});

  const measureDay = (date: string) => {
    const node = refs.current[date];
    if (node === null || node === undefined) return;
    node.measureInWindow((_x, y, _w, h) => {
      const others = dayFrames.value.filter((f) => f.date !== date);
      dayFrames.value = [...others, { date, pageY: y, height: h }];
    });
  };

  return (
    <View>
      {week.days.map((day) => {
        const date = fromIso(day.date);
        const isToday = day.date === toIso(new Date());
        return (
          <View key={day.date} className="mb-4">
            <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8, paddingHorizontal: 4 }}>
              {isToday && (
                <Text style={{ color: colors.accentRun, fontFamily: fonts.pixel, fontSize: 10, marginRight: 6 }}>▸</Text>
              )}
              <Text style={{
                color: isToday ? colors.accentRun : colors.ink,
                fontFamily: fonts.monoBold, fontSize: 14,
              }}>
                {dayName(date, 'long')}
              </Text>
              <Text style={{ color: colors.inkDim, fontFamily: fonts.mono, fontSize: 12, marginLeft: 8 }}>
                {date.getMonth() + 1}/{date.getDate()}
              </Text>
            </View>

            <DropZone
              date={day.date}
              hoveredDate={hoveredDate}
              measureRef={(el) => { refs.current[day.date] = el; }}
              onLayoutMeasure={() => { measureDay(day.date); }}
            >
              {day.workouts.length === 0 ? (
                <View style={{
                  backgroundColor: colors.bgPanelAlt,
                  borderWidth: 1, borderColor: colors.line, borderRadius: 6, padding: 14, alignItems: 'center',
                }}>
                  <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.inkMute }}>Rest day</Text>
                </View>
              ) : (
                day.workouts.map((w) => (
                  <DraggableWorkout
                    key={w.id}
                    workout={w}
                    dayFrames={dayFrames}
                    hoveredDate={hoveredDate}
                    onPress={() => { onWorkoutPress(w); }}
                    onMove={(newDate) => { onMoveRequest(w, newDate); }}
                    disabled={disabled}
                  />
                ))
              )}
            </DropZone>
          </View>
        );
      })}
    </View>
  );
}
