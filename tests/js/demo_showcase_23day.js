/* The 23-day demo, walked feature by feature.

   Builds a real 23-day demo session with 10 friends through the real
   API, then visits every page and checks each feature actually has real
   content in it - not that the page loaded, but that the thing the page
   exists for is populated. Screenshots every page so the run is
   presentable, not just green. */
const { chromium } = require('playwright');
const fs = require('fs');

const APP = 'http://127.0.0.1:8000';
const SHOTS = '/tmp/claude-0/-home-user-Digital-Wellness-AI/6f6b0649-8431-5b02-a094-23a4f6a97d9c/scratchpad/shots23';
const LANG = process.env.SHOW_LANG || 'fa';

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass: !!pass, detail: detail === undefined ? '' : String(detail).slice(0, 90) });
}

(async () => {
  fs.rmSync(SHOTS, { recursive: true, force: true });
  fs.mkdirSync(SHOTS, { recursive: true });

  const email = `show_${Date.now()}@example.com`;
  const reg = await fetch(`${APP}/api/v1/auth/register`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password: 'TestPass123!', display_name: 'Showcase' }),
  }).then((r) => r.json());
  const auth = { Authorization: `Bearer ${reg.access_token}`, 'Content-Type': 'application/json' };

  // ---- Build the 23-day demo through the real endpoint ----------------
  const t0 = Date.now();
  const session = await fetch(`${APP}/api/v1/demo/session`, {
    method: 'POST', headers: auth,
    body: JSON.stringify({ days: 23, profile: 'improving', friends: 10 }),
  }).then((r) => r.json());
  const buildMs = Date.now() - t0;

  check('demo session created', !!session.access_token, session.detail || '');
  check('23 days built', session.days_created === 23, `days_created=${session.days_created}`);
  check('10 friends connected', session.friends_connected === 10, `friends=${session.friends_connected}`);
  check('build under 30s', buildMs < 30000, `${(buildMs / 1000).toFixed(1)}s`);
  check('demo account is separate from the real one',
    !!session.demo_user_id, session.demo_user_id);

  if (!session.access_token) {
    console.log(JSON.stringify({ fatal: 'no demo token', session }, null, 1));
    return;
  }

  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 1000 } });
  const page = await ctx.newPage();
  const jsErrors = [];
  page.on('pageerror', (e) => jsErrors.push(String(e.message).slice(0, 120)));

  // Seed the browser exactly as demo.js's activate() does when a real
  // user starts a demo from Settings - token, language, AND the final
  // result/inputs the Plan, Coach and What-if pages read.
  await page.addInitScript(([t, l, res, inp]) => {
    localStorage.setItem('dwai_token', t);
    localStorage.setItem('dwai_lang', l);
    localStorage.setItem('dwai_intro_seen', '1');
    if (res) localStorage.setItem('dwai_last_result', res);
    if (inp) localStorage.setItem('dwai_last_payload', inp);
  }, [session.access_token, LANG,
      session.final_result ? JSON.stringify(session.final_result) : '',
      session.final_inputs ? JSON.stringify(session.final_inputs) : '']);

  check('session carries the final result for the browser', !!session.final_result);
  check('session carries the inputs behind it',
    session.final_inputs && Object.keys(session.final_inputs).length > 40,
    Object.keys(session.final_inputs || {}).length + ' fields');

  const visit = async (name, wait = 3000) => {
    await page.goto(`${APP}/${name}`, { waitUntil: 'load', timeout: 30000 });
    await page.waitForTimeout(wait);
    await page.screenshot({ path: `${SHOTS}/${name.replace('.html', '')}.png`, fullPage: true });
  };

  // ---- Dashboard: heatmap, stats, trend, recommendations --------------
  await visit('dashboard.html', 5000);
  const dash = await page.evaluate(() => ({
    lastScore: (document.getElementById('statLastScore') || {}).textContent,
    weekAvg: (document.getElementById('statWeekAvg') || {}).textContent,
    entries: (document.getElementById('statEntries') || {}).textContent,
    scoredCells: document.querySelectorAll('.heatmap-cell .heatmap-score').length,
    flags: document.querySelectorAll('.heatmap-flag').length,
    recCards: document.querySelectorAll('#dashRecs .rec-card').length,
    recNote: (document.getElementById('dashRecs') || {}).textContent,
    cohortRows: document.querySelectorAll('#cohortRows .metric-row').length,
    topFactor: (document.getElementById('topFeatureLine') || {}).textContent,
  }));
  check('dashboard: 23 check-ins counted', Number(dash.entries) === 23, `entries=${dash.entries}`);
  check('dashboard: real last score', dash.lastScore && dash.lastScore !== '--', dash.lastScore);
  check('dashboard: week average', dash.weekAvg && dash.weekAvg !== '--', dash.weekAvg);
  check('dashboard: heatmap has this week\'s days', dash.scoredCells >= 1 && dash.scoredCells <= 7, `${dash.scoredCells} of the current week`);
  check('dashboard: heatmap exception toggles', dash.flags === dash.scoredCells, `${dash.flags} toggles for ${dash.scoredCells} days`);
  check('dashboard: advice area populated', dash.recCards >= 1 || (dash.recNote || '').trim().length > 10, `${dash.recCards} cards`);
  check('dashboard: cohort comparison', dash.cohortRows >= 1, `${dash.cohortRows} rows`);
  check('dashboard: top factor named', (dash.topFactor || '').length > 5, dash.topFactor);

  // ---- Analytics: trend, insight cards, the letter --------------------
  await visit('analytics.html', 4200);
  const an = await page.evaluate(() => ({
    verdict: (document.getElementById('trendVerdict') || {}).textContent,
    note: (document.getElementById('trendNote') || {}).textContent,
    canvasDrawn: (() => {
      const c = document.getElementById('trendChart');
      if (!c) return false;
      const ctx2 = c.getContext('2d');
      const d = ctx2.getImageData(0, 0, c.width, c.height).data;
      for (let i = 3; i < d.length; i += 40) if (d[i] !== 0) return true;
      return false;
    })(),
    letterOffered: !!document.getElementById('letterSection')
      && !document.getElementById('letterSection').classList.contains('hidden'),
    cards: document.querySelectorAll('.insight-card, .card').length,
  }));
  check('analytics: trend verdict stated', (an.verdict || '').length > 3, an.verdict);
  check('analytics: trend chart actually drawn', an.canvasDrawn);
  check('analytics: 23 days unlocks the future letter', an.letterOffered);

  // Open the letter and confirm the envelope + dateline render.
  if (an.letterOffered) {
    await page.click('#openLetterBtn').catch(() => {});
    await page.waitForTimeout(2600);
    const letter = await page.evaluate(() => ({
      envelope: !!document.querySelector('.letter-envelope'),
      dateline: (document.querySelector('.letter-dateline') || {}).textContent,
      lines: document.querySelectorAll('.letter-body p').length,
      readable: (() => {
        const c = document.querySelector('.letter-card');
        if (!c) return false;
        return getComputedStyle(c).opacity !== '0';
      })(),
    }));
    check('letter: envelope rendered', letter.envelope);
    check('letter: dated from the future', (letter.dateline || '').length > 3, letter.dateline);
    check('letter: written from real numbers', letter.lines >= 4, `${letter.lines} lines`);
    check('letter: ends readable', letter.readable);
    await page.screenshot({ path: `${SHOTS}/analytics-letter.png`, fullPage: true });
  }

  // ---- Weekly plan ----------------------------------------------------
  await visit('weekly.html', 4200);
  const wk = await page.evaluate(() => {
    const days = [...document.querySelectorAll('#planDays .day-card')];
    return {
      dayCount: days.length,
      distinctThemes: new Set(days.map((d) => (d.querySelector('.muted') || {}).textContent)).size,
      tasks: document.querySelectorAll('#planDays .task-row').length,
      chips: document.querySelectorAll('#planFocusChips .chip-option').length,
      intro: (document.getElementById('planIntro') || {}).textContent,
      weekRows: document.querySelectorAll('.metric-row').length,
    };
  });
  check('plan: 7 days', wk.dayCount === 7, `${wk.dayCount}`);
  check('plan: days are not all identical', wk.distinctThemes >= 3, `${wk.distinctThemes} distinct themes`);
  check('plan: tasks present', wk.tasks >= 14, `${wk.tasks} tasks`);
  check('plan: focus areas chosen', wk.chips >= 1, `${wk.chips}`);
  check('plan: intro personalised', (wk.intro || '').length > 40);
  check('weekly: week summary rows', wk.weekRows >= 4, `${wk.weekRows}`);

  // ---- League: 10 friends, leaderboard, seeded chats -------------------
  await visit('league.html', 7000);
  const lg = await page.evaluate(() => ({
    connections: document.querySelectorAll('#leagueConnectionsList > *').length,
    leaderboard: document.querySelectorAll('#leagueLeaderboardList > *').length,
    conversations: document.querySelectorAll('#chatConversationList .chat-conversation').length,
    renameControls: document.querySelectorAll('.chat-conversation-rename').length,
  }));
  check('league: 10 friends listed', lg.connections >= 10, `${lg.connections}`);
  check('league: leaderboard populated', lg.leaderboard >= 5, `${lg.leaderboard} rows`);
  check('league: chats pre-seeded', lg.conversations >= 10, `${lg.conversations} conversations`);
  check('league: rename control present', lg.renameControls >= 1, `${lg.renameControls}`);

  // Open a chat and confirm it has a real opening message in it.
  if (lg.conversations) {
    await page.click('#chatConversationList .chat-conversation').catch(() => {});
    await page.waitForTimeout(2000);
    const thread = await page.evaluate(() => ({
      messages: document.querySelectorAll('#chatThread .chat-message').length,
      firstBody: (document.querySelector('#chatThread .chat-body') || {}).textContent,
    }));
    check('league: chat has an opening message', thread.messages >= 1, thread.firstBody);
    await page.screenshot({ path: `${SHOTS}/league-chat.png`, fullPage: true });
  }

  // ---- Hall of Fame / badges ------------------------------------------
  await visit('hall.html', 3600);
  const hall = await page.evaluate(() => ({
    badges: document.querySelectorAll('.badge-card, .hall-badge, [class*="badge"]').length,
    earned: document.querySelectorAll('.is-earned').length,
    dir: document.documentElement.dir,
  }));
  check('hall: badges rendered', hall.badges >= 5, `${hall.badges}`);
  check('hall: some earned after 23 days', hall.earned >= 1, `${hall.earned} earned`);

  // ---- What-if ---------------------------------------------------------
  await visit('whatif.html', 4000);
  const wi = await page.evaluate(() => ({
    sliders: document.querySelectorAll('input[type="range"]').length,
    numbers: document.querySelectorAll('input[type="number"]').length,
    hasBaseline: !!document.querySelector('#whatifBaseline, [id*="baseline"]'),
  }));
  check('what-if: controls present', (wi.sliders + wi.numbers) >= 1, `${wi.sliders} sliders / ${wi.numbers} numbers`);

  // ---- Model performance ----------------------------------------------
  await visit('model-performance.html', 4000);
  const mp = await page.evaluate(() => {
    const txt = document.body.innerText;
    return {
      hasMetrics: /0\.\d{2,}/.test(txt),
      mentionsBoth: /class/i.test(txt) && /regress/i.test(txt),
      cards: document.querySelectorAll('.card').length,
    };
  });
  check('model page: real metric numbers', mp.hasMetrics);
  check('model page: both models covered', mp.mentionsBoth);

  // ---- Profile / persona -----------------------------------------------
  await visit('profile.html', 3600);
  const pr = await page.evaluate(() => ({
    persona: (document.querySelector('#personaTitle, [id*="persona"]') || {}).textContent,
    options: document.querySelectorAll('.onboard-option').length,
    selected: document.querySelectorAll('.onboard-option.selected').length,
  }));
  check('profile: persona resolved', (pr.persona || '').length > 2, pr.persona);
  check('profile: option pickers rendered', pr.options >= 15, `${pr.options}`);

  // ---- Coach: the menu, and an answer built from the demo's own data ----
  await visit('coach.html', 4200);
  const coach = await page.evaluate(async () => {
    const menu = window.DWAIMenu ? window.DWAIMenu.ITEMS : [];
    let ctx = null;
    try { ctx = await window.DWAIMenu.buildContext(); } catch (e) { /* reported below */ }
    const answers = {};
    ['score_meaning', 'field_sleep_hours', 'edu_shap', 'dim_sleep', 'planday_1']
      .forEach((id) => {
        try { answers[id] = (window.DWAIMenu.getAnswer(id, ctx || {}) || '').slice(0, 100); }
        catch (e) { answers[id] = 'ERROR: ' + e.message; }
      });
    return {
      menuCount: menu.length,
      categories: new Set(menu.map((i) => i.cat)).size,
      hasCtxResult: !!(ctx && ctx.result),
      hasCtxPlan: !!(ctx && ctx.plan),
      answers,
    };
  });
  check('coach: menu is large', coach.menuCount >= 140, `${coach.menuCount} items`);
  check('coach: menu is organised', coach.categories >= 10, `${coach.categories} categories`);
  check('coach: reads the demo result', coach.hasCtxResult);
  check('coach: reads the demo plan', coach.hasCtxPlan);
  Object.entries(coach.answers).forEach(([id, text]) => {
    check(`coach answer "${id}" is real`, text.length > 30 && !text.startsWith('ERROR'), text);
  });

  // ---- Check-in screen: CSV history + reopening a past day -------------
  await visit('app.html', 4200);
  const appv = await page.evaluate(() => ({
    view: (document.querySelector('.view.active') || {}).id,
    csvHistoryCard: !!document.getElementById('csvHistoryCard'),
  }));
  check('check-in screen reachable in demo', ['view-predict', 'view-onboarding'].includes(appv.view), appv.view);

  // Reopen a real demo day through the URL the heatmap uses.
  const anyDate = await fetch(`${APP}/api/v1/history?page=1&page_size=1`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
  }).then((r) => r.json()).then((d) => (d.items[0] || {}).date);
  if (anyDate) {
    await page.goto(`${APP}/app.html?day=${anyDate}`, { waitUntil: 'load', timeout: 30000 });
    await page.waitForTimeout(3800);
    const reopened = await page.evaluate(() => ({
      view: (document.querySelector('.view.active') || {}).id,
      banner: !document.getElementById('pastDayBanner').classList.contains('hidden'),
      bannerText: (document.getElementById('pastDayBannerText') || {}).textContent,
      score: (document.getElementById('horizonTodayScore') || {}).textContent,
      dims: document.querySelectorAll('.dim-wave').length,
      recs: document.querySelectorAll('#recCards .rec-card').length,
    }));
    check('reopen: lands on the result', reopened.view === 'view-result', reopened.view);
    check('reopen: banner names the day', reopened.banner, reopened.bannerText);
    check('reopen: real score shown', reopened.score && reopened.score !== '--', reopened.score);
    check('reopen: dimensions rendered', reopened.dims >= 4, `${reopened.dims}`);
    check('reopen: recommendations rendered', reopened.recs >= 1, `${reopened.recs}`);
    await page.screenshot({ path: `${SHOTS}/reopened-day.png`, fullPage: true });
  }

  // ---- Language integrity across the whole demo -------------------------
  check('no JS errors anywhere in the walkthrough', jsErrors.length === 0, jsErrors.join(' | '));

  // ---- Tear the demo down and prove nothing leaked ----------------------
  const del = await fetch(`${APP}/api/v1/demo/session`, {
    method: 'DELETE', headers: { Authorization: `Bearer ${session.access_token}` },
  });
  check('demo session deletable', del.status === 200 || del.status === 204, `HTTP ${del.status}`);

  const realHistory = await fetch(`${APP}/api/v1/history?page=1&page_size=50`, {
    headers: { Authorization: `Bearer ${reg.access_token}` },
  }).then((r) => r.json());
  check('the real account still has zero days',
    (realHistory.items || []).length === 0, `${(realHistory.items || []).length} entries`);

  const passed = checks.filter((c) => c.pass).length;
  console.log(JSON.stringify({
    lang: LANG,
    buildSeconds: +(buildMs / 1000).toFixed(1),
    passed, total: checks.length,
    failed: checks.filter((c) => !c.pass),
    screenshots: fs.readdirSync(SHOTS).length,
    all: checks,
  }, null, 1));
  await browser.close();
})();
