/*
  Demo Mode trigger, available from the Settings modal on every page.
  One click -> the real narrative processing screen (~15s, same
  skippable/never-fake-ceiling contract as the prediction flow) ->
  services/demo_service.py builds 23 real-model-scored days plus one
  demo League friend -> the page reloads on the dashboard with
  everything populated. Never touches a real check-in the user already
  logged; it only ADDS synthetic days alongside them.
*/
(function () {
  const MIN_MS = 15000;

  async function run() {
    if (!window.DWApi || !window.DWApi.isAuthed()) return;
    const lang = (window.DWI18n && window.DWI18n.get()) || 'en';
    const confirmed = window.confirm(
      lang === 'fa'
        ? 'این کار ۲۳ روز داده‌ی نمایشی (با امتیازهای واقعی مدل) و یک دوست نمایشی در لیگ اضافه می‌کند. ادامه بدهم؟'
        : 'This adds 23 days of demo history (with real model scores) and one demo League friend. Continue?'
    );
    if (!confirmed) return;

    const modal = document.getElementById('settingsModal');
    if (modal) modal.classList.remove('show');

    let response;
    try {
      response = await window.DWProcessing.run(window.DWApi.demoPopulate(), { flow: 'demo', minMs: MIN_MS });
    } catch (e) {
      if (window.DWToast) window.DWToast.error(e.message);
      return;
    }

    // Populate the same localStorage keys a real check-in leaves behind,
    // so Coach/Result-dependent pages work immediately after reload.
    try {
      localStorage.setItem('dwai_last_result', JSON.stringify(response.final_result));
      localStorage.setItem('dwai_last_payload', JSON.stringify(response.final_user_data));
    } catch (e) {}

    if (window.DWToast) {
      window.DWToast.success(
        lang === 'fa'
          ? `${response.days_created} روز اضافه شد${response.friend_connected ? ' و یک دوست وصل شد' : ''}.`
          : `${response.days_created} days added${response.friend_connected ? ' and a friend connected' : ''}.`
      );
    }
    setTimeout(() => { location.href = 'dashboard.html'; }, 900);
  }

  window.DWDemo = { run };
})();
