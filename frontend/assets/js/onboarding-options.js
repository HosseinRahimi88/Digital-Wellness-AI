/*
  Mirrors config/onboarding_options.py's GOAL_OPTIONS / PURPOSE_OPTIONS /
  SCHEDULE_OPTIONS label->value maps, so both the first-time Onboarding
  view (app.html) and the editable Profile page use the exact same
  option set instead of two hand-copied lists drifting apart.
*/
(function () {
  const GOAL_OPTIONS = {
    'Build a better pre-sleep routine': 'better_sleep',
    'Reduce late-night device use': 'reduce_night_use',
    'Improve focus and reduce interruptions': 'improve_focus',
    'Check my device less frequently': 'reduce_pickups',
    'Manage notifications more intentionally': 'manage_notifications',
    'Improve work, study, and leisure balance': 'improve_balance',
    'Create more screen-free activity time': 'increase_activity',
    'Maintain my current healthy habits': 'maintain_habits',
  };
  const PURPOSE_OPTIONS = {
    'Work or career': 'work_career', 'Education or study': 'education', 'Social connection': 'social_connection',
    'Entertainment': 'entertainment', 'News or information': 'news_information', 'Content creation': 'content_creation',
    'A mixture of purposes': 'mixed', 'Other': 'other',
  };
  const SCHEDULE_OPTIONS = {
    'Standard daytime schedule': 'standard_day', 'Early shift': 'early_shift', 'Late shift': 'late_shift',
    'Rotating shifts': 'rotating_shift', 'Student or flexible schedule': 'student_flexible', 'Irregular schedule': 'irregular', 'Other': 'other',
  };

  window.DWOnboardingOptions = { GOAL_OPTIONS, PURPOSE_OPTIONS, SCHEDULE_OPTIONS };
})();
