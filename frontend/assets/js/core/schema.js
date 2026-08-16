/*
  Client-side mirror of the wizard's structure. Field bounds/choices are
  always fetched live from GET /schema/features (the backend's own
  single source of truth - core/feature_schema.py) so this file never
  hardcodes a min/max/choice list that could drift from the real model
  contract. What lives here is presentation-only: step grouping, widget
  type, and sensible starting defaults (mirrors utils/form_generator.py).
*/
(function () {
  const STEPS = [
    {
      key: 'demographics', titleKey: 'step_demographics',
      fields: [
        'age', 'gender', 'occupation_group', 'region_group', 'education_group',
        'device_category', 'primary_platform', 'purpose_group',
        'is_content_creator', 'uses_screen_time_limits',
      ],
    },
    { key: 'time', titleKey: 'step_time', fields: ['day_of_week'] },
    {
      key: 'screen', titleKey: 'step_screen',
      fields: ['social_min', 'gaming_min', 'work_study_min', 'video_min', 'other_min', 'night_screen_min', 'pre_sleep_screen_min'],
    },
    {
      key: 'device', titleKey: 'step_device',
      fields: ['notifications_per_day', 'pickups_per_day', 'app_opens_per_day', 'sessions_per_day', 'first_check_after_waking_min'],
    },
    { key: 'sleep', titleKey: 'step_sleep', fields: ['sleep_hours', 'sleep_quality_1_10'] },
    {
      key: 'mental', titleKey: 'step_mental',
      fields: [
        'stress_0_10', 'mental_fatigue_0_10', 'anxiety_0_27', 'low_mood_0_27', 'happiness_0_10',
        'loneliness_1_10', 'self_esteem_1_10', 'fomo_1_10', 'social_comparison_1_10', 'life_satisfaction_1_10',
      ],
    },
    {
      key: 'focus', titleKey: 'step_focus',
      fields: ['focus_0_100', 'productivity_0_100', 'physical_activity_min_per_day', 'caffeine_cups_per_day'],
    },
  ];

  // Fields whose value is fully computed from other inputs - shown
  // read-only in the "auto-calculated" panel, never as editable inputs.
  const DERIVED_FIELDS = new Set([
    'total_screen_min', 'social_ratio', 'gaming_ratio', 'work_study_ratio', 'other_ratio',
    'night_ratio', 'pre_sleep_ratio', 'notification_density', 'pickup_density', 'app_open_density',
    'screen_ewma_baseline', 'screen_vs_baseline_pct', 'fragmentation_index_0_100', 'digital_dependence_0_100',
  ]);

  // Collected only to feed derive_features() - not real model inputs
  // (see core/feature_schema.py's module docstring) so they are not
  // part of FEATURE_SCHEMA and won't come back from GET /schema/features.
  const HELPER_ONLY_FIELDS = {
    sessions_per_day: { label: 'Usage Sessions / Day', dtype: 'int', minimum: 0, maximum: 200, default: 12 },
    first_check_after_waking_min: { label: 'Minutes Until First Phone Check After Waking', dtype: 'float', minimum: 0, maximum: 300, default: 45 },
  };

  const SLIDER_FIELDS = new Set([
    'sleep_hours', 'sleep_quality_1_10', 'stress_0_10', 'mental_fatigue_0_10', 'fomo_1_10',
    'happiness_0_10', 'loneliness_1_10', 'self_esteem_1_10', 'social_comparison_1_10', 'life_satisfaction_1_10',
    'focus_0_100', 'productivity_0_100',
  ]);

  const DEFAULTS = {
    age: 22, gender: 'Male', occupation_group: 'Student', region_group: 'Middle East',
    education_group: 'Bachelor', device_category: 'Tablet', primary_platform: 'RedNote',
    purpose_group: 'Work/Career', is_content_creator: false, uses_screen_time_limits: true,
    day_of_week: 'Tuesday',
    social_min: 45, gaming_min: 0, work_study_min: 120, video_min: 30, other_min: 15,
    night_screen_min: 0, pre_sleep_screen_min: 10,
    notifications_per_day: 30, pickups_per_day: 20, app_opens_per_day: 25,
    sessions_per_day: 12, first_check_after_waking_min: 45,
    sleep_hours: 8, sleep_quality_1_10: 8.5,
    stress_0_10: 2, mental_fatigue_0_10: 2, anxiety_0_27: 2, low_mood_0_27: 1, fomo_1_10: 2,
    happiness_0_10: 8.5, loneliness_1_10: 2, self_esteem_1_10: 8, social_comparison_1_10: 2, life_satisfaction_1_10: 8.5,
    focus_0_100: 85, productivity_0_100: 85, physical_activity_min_per_day: 60, caffeine_cups_per_day: 1,
  };

  function computeTotalScreenMin(d) {
    const total = (Number(d.social_min) || 0) + (Number(d.gaming_min) || 0) +
      (Number(d.work_study_min) || 0) + (Number(d.video_min) || 0) + (Number(d.other_min) || 0);
    return Math.max(total, 1.0);
  }

  function round(n, dp) { const f = Math.pow(10, dp); return Math.round(n * f) / f; }

  function deriveFeatures(input) {
    const data = Object.assign({}, input);
    data.total_screen_min = computeTotalScreenMin(data);
    const tot = data.total_screen_min;
    const screenHours = tot > 0 ? tot / 60.0 : 1.0;

    data.social_ratio = round((Number(data.social_min) || 0) / tot, 4);
    data.gaming_ratio = round((Number(data.gaming_min) || 0) / tot, 4);
    data.work_study_ratio = round((Number(data.work_study_min) || 0) / tot, 4);
    data.other_ratio = round((Number(data.other_min) || 0) / tot, 4);
    data.night_ratio = round((Number(data.night_screen_min) || 0) / tot, 4);
    data.pre_sleep_ratio = round((Number(data.pre_sleep_screen_min) || 0) / tot, 4);

    data.notification_density = round((Number(data.notifications_per_day) || 0) / screenHours, 2);
    data.pickup_density = round((Number(data.pickups_per_day) || 0) / screenHours, 2);
    data.app_open_density = round((Number(data.app_opens_per_day) || 0) / screenHours, 2);

    if (input.screen_ewma_baseline === undefined || input.screen_ewma_baseline === null) {
      data.screen_ewma_baseline = tot;
    }
    const popBaseline = 240.0;
    const rawPct = ((tot - popBaseline) / popBaseline) * 100.0;
    data.screen_vs_baseline_pct = round(Math.max(-100, Math.min(300, rawPct)), 2);

    const fragScore = (Number(data.pickups_per_day) || 0) * 0.4 + (Number(data.sessions_per_day) || 0) * 0.6;
    data.fragmentation_index_0_100 = round(Math.min(100, Math.max(0, fragScore)), 2);

    const recreationMin = (Number(data.social_min) || 0) + (Number(data.gaming_min) || 0) + (Number(data.video_min) || 0);
    const nightPenalty = (Number(data.night_screen_min) || 0) * 1.5;
    const wakingPenalty = Math.max(0, 60 - (Number(data.first_check_after_waking_min) || 0)) * 0.8;
    const depScore = (recreationMin / 6.0) + (nightPenalty / 3.0) + wakingPenalty;
    data.digital_dependence_0_100 = round(Math.min(100, Math.max(0, depScore)), 2);

    return data;
  }

  // Separate from deriveFeatures() on purpose: utils/feature_derivation.py's
  // derive_features() never touches day_index/is_weekend - that stamping is
  // utils/form_generator.py's own logic (day_index hardcoded to 1, is_weekend
  // inferred from the day-of-week picker), applied only for a fresh manual
  // submission. Demo profiles (config/demo_profiles.py) get their own
  // day_index/is_weekend straight from FEATURE_SCHEMA and must NOT be
  // re-stamped, or a loaded demo fixture would silently drift from the
  // exact values the backend itself generated.
  function applyCalendarDefaults(data) {
    const out = Object.assign({}, data);
    out.day_index = 1;
    out.is_weekend = ['Saturday', 'Sunday'].includes(out.day_of_week) ? 1 : 0;
    return out;
  }

  /* The "which day is it" step only makes sense when this check-in is a
     hypothetical entry the user has explicitly excluded from weekly
     analysis (the "don't record this" checkbox) - a real, recorded
     check-in should never ask the user something the app already knows
     (today's real weekday), so that step is dropped from the normal
     flow entirely and the real weekday is stamped in automatically at
     submission time instead (see app.js's submitPrediction). */
  function stepsFor(isHypothetical) {
    return isHypothetical ? STEPS : STEPS.filter((s) => s.key !== 'time');
  }

  function todaysWeekday() {
    return new Date().toLocaleDateString('en-US', { weekday: 'long' });
  }

  window.DWSchema = {
    STEPS, stepsFor, todaysWeekday, DERIVED_FIELDS, HELPER_ONLY_FIELDS, SLIDER_FIELDS, DEFAULTS,
    deriveFeatures, applyCalendarDefaults, computeTotalScreenMin,
  };
})();
