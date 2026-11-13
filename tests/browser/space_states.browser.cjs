// Browser regression for space/index.html fail-closed states. Not run in CI (needs Playwright + Chrome).
// usage: PW=<path-to-playwright> node tests/browser/space_states.browser.cjs http://127.0.0.1:7860
const { chromium } = require(process.env.PW || 'playwright');
const base = process.argv[2] || 'http://127.0.0.1:4211';
const R = []; const check = (n, ok, d = '') => R.push({ n, ok, d });
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined, args: ['--no-sandbox'] });
  { const p = await b.newPage(); await p.goto(base + '/', { waitUntil: 'networkidle' });
    const s = p.locator('#sliders input[type=range]').first(); await s.focus(); const v0 = await s.inputValue();
    for (let i = 0; i < 3; i++) await p.keyboard.press('ArrowLeft');
    const still = await p.evaluate(() => !!document.activeElement && document.activeElement.matches('#sliders input[type=range]') && document.activeElement.dataset.i === '0');
    const v1 = await p.evaluate(() => document.activeElement && document.activeElement.value);
    check('slider keeps keyboard focus after 3 ArrowLeft', still);
    check('slider value moved 3 steps', still && Math.abs(+v0 - +v1 - 0.03) < 1e-9, `v0=${v0} v1=${v1}`);
    await p.close(); }
  for (const mode of ['500-html', 'abort', 'json-empty']) {
    const p = await b.newPage(); const errs = []; p.on('pageerror', e => errs.push(String(e)));
    const h = r => mode === 'abort' ? r.abort() : mode === '500-html' ? r.fulfill({ status: 500, contentType: 'text/html', body: '<!DOCTYPE html>x' }) : r.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    await p.route('**/api/**', h); await p.route('**/healthz', h);
    await p.goto(base + '/', { waitUntil: 'networkidle' }); await p.waitForTimeout(400);
    await p.click('#run-bench'); await p.waitForTimeout(300);
    const t = id => p.locator('#' + id).innerText();
    const green = await t('green'), anat = await t('anatomy'), lam = await t('lam'), inf = await t('infer');
    check(`[${mode}] greenlight not GREEN-LIGHT`, !/GREEN-LIGHT/.test(green), green);
    check(`[${mode}] anatomy not LIVE`, !/\bLIVE\b/.test(anat), anat);
    check(`[${mode}] lambda not fabricated 0.0000`, !/0\.0000/.test(lam), lam);
    check(`[${mode}] bench not "0/0 HOLD"`, !/HOLD/.test(inf), inf);
    check(`[${mode}] visible UNAVAILABLE`, /UNAVAILABLE/.test(green) && /UNAVAILABLE/.test(anat), green + ' | ' + anat);
    check(`[${mode}] no unhandled rejections`, errs.length === 0, errs[0] || '');
    await p.close(); }
  { const p = await b.newPage(); await p.goto(base + '/', { waitUntil: 'networkidle' });
    const btn = p.locator('#paint'); const before = await btn.getAttribute('aria-pressed'); await btn.click(); await p.waitForTimeout(300);
    check('toggle aria-pressed false → true', before === 'false' && (await btn.getAttribute('aria-pressed')) === 'true', String(before));
    check('7 result lines are live regions', (await p.locator('[role=status][aria-live=polite]').count()) >= 7);
    await p.close(); }
  { const p = await b.newPage(); let n = 0;
    await p.route('**/api/lambda', async r => { const k = ++n; const body = JSON.parse(r.request().postData() || '{}');
      if (k === 2) await new Promise(res => setTimeout(res, 800));
      r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ lambda: body.axes[0], decision: 'REQ' + k, blocked: false }) }); });
    await p.goto(base + '/', { waitUntil: 'networkidle' });
    const s = p.locator('#sliders input[type=range]').first(); await s.focus();
    await p.keyboard.press('ArrowLeft'); await p.waitForTimeout(50); await p.keyboard.press('ArrowLeft'); await p.waitForTimeout(1200);
    const lam = await p.locator('#lam').innerText(); check('latest request wins', /REQ3/.test(lam), lam); await p.close(); }
  await b.close();
  let f = 0; for (const r of R) { console.log((r.ok ? 'PASS ' : 'FAIL ') + r.n + (r.ok ? '' : ' :: ' + r.d)); if (!r.ok) f++; }
  console.log(`${R.length - f}/${R.length} passed`); process.exit(f ? 1 : 0);
})();
