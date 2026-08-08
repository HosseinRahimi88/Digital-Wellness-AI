/* Profile page controller: view/edit the account's onboarding
   preferences (goal, purpose, schedule) via PUT /auth/me/onboarding.
   Shares its option lists with the initial onboarding flow via
   onboarding-options.js so the two never drift apart. */
document.addEventListener('DOMContentLoaded', async () => {
  const account = await window.DWShell.init('profile');
  if (!account) return;

  const canvas = document.getElementById('bgCanvas');
  if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

  const initials = (account.display_name || account.email || '?').trim().slice(0, 2).toUpperCase();
  document.getElementById('avatarCircle').textContent = initials;

  const { GOAL_OPTIONS, PURPOSE_OPTIONS, SCHEDULE_OPTIONS } = window.DWOnboardingOptions;
  const selected = { goal: account.primary_goal, purpose: account.main_use_purpose, schedule: account.schedule_type };

  function buildOptionList(container, options, stateKey) {
    container.innerHTML = '';
    Object.entries(options).forEach(([label, value]) => {
      const el = document.createElement('div');
      el.className = 'onboard-option' + (selected[stateKey] === value ? ' selected' : '');
      el.textContent = label;
      el.addEventListener('click', () => {
        Array.from(container.children).forEach((c) => c.classList.remove('selected'));
        el.classList.add('selected');
        selected[stateKey] = value;
      });
      container.appendChild(el);
    });
  }

  buildOptionList(document.getElementById('goalOptions'), GOAL_OPTIONS, 'goal');
  buildOptionList(document.getElementById('purposeOptions'), PURPOSE_OPTIONS, 'purpose');
  buildOptionList(document.getElementById('scheduleOptions'), SCHEDULE_OPTIONS, 'schedule');

  document.getElementById('saveProfileBtn').addEventListener('click', async () => {
    try {
      await window.DWApi.saveOnboarding({
        primary_goal: selected.goal || 'maintain_habits',
        main_use_purpose: selected.purpose || 'mixed',
        schedule_type: selected.schedule || 'standard_day',
        usual_sleep_time: account.usual_sleep_time || '23:00',
        usual_wake_time: account.usual_wake_time || '07:00',
        preferred_effort: account.preferred_effort || 'moderate',
        work_screen_required: account.work_screen_required || false,
      });
      window.DWToast.success(window.DWI18n.t('toast_saved'));
      window.DWMascot.react('saved');
    } catch (e) {
      window.DWToast.error(e.message);
    }
  });
});
