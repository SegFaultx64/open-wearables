/**
 * Map a Garmin/Apple/etc. workout type string to a Lucide icon component.
 * Replaces the emoji glyphs which render inconsistently across fonts/OSes.
 */
import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  Bike,
  Compass,
  Dumbbell,
  Flame,
  Footprints,
  Mountain,
  MountainSnow,
  PersonStanding,
  Snowflake,
  Sparkles,
  Trophy,
  Waves,
  Zap,
} from 'lucide-react';

const iconByPattern: Array<[RegExp, LucideIcon]> = [
  // Running / walking / hiking
  [/trail_running|trail|fell/i, Mountain],
  [/run|jog|treadmill/i, Footprints],
  [/walk/i, PersonStanding],
  [/hik/i, Compass],
  [/mountaineer|climb|boulder/i, Mountain],
  // Cycling
  [/cycl|bike|biking|mtb|gravel|spin/i, Bike],
  // Water
  [/swim|pool|open_water|kayak|paddle|surf|row/i, Waves],
  // Snow
  [/ski|snowboard|sled|alpine|nordic/i, MountainSnow],
  [/skat|hockey/i, Snowflake],
  // Strength / fitness
  [/strength|weight|gym|crossfit|powerlift/i, Dumbbell],
  [/cardio|hiit|aerobic|jumping/i, Flame],
  [/yoga|pilates|stretch|breathwork|meditat/i, Sparkles],
  [/golf|tennis|basketball|football|soccer|baseball|volleyball|game/i, Trophy],
  [/eboard|skateboard/i, Zap],
];

export function getWorkoutIcon(type: string | null | undefined): LucideIcon {
  const t = (type ?? '').toLowerCase();
  for (const [re, Icon] of iconByPattern) {
    if (re.test(t)) return Icon;
  }
  return Activity;
}
