import { chromium, firefox, webkit } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const base = 'http://127.0.0.1:8002';
const viewports = [
  { name: 'desktop', width: 1920, height: 1080 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 375, height: 667 }
];

const checks = [
  {
    page: '/use/macro-analysis.html',
    selector: 'select[id*="year"], select',
    choose: '2020',
    keyboardChoose: '2015'
  },
  {
    page: '/use/meso-analysis.html',
    selector: 'select',
    choose: 'efficiency'
  },
  {
    page: '/use/prediction.html',
    selector: 'select',
    choose: 'combined'
  }
];

const engines = [
  { name: 'chromium', launcher: chromium },
  { name: 'firefox', launcher: firefox },
  { name: 'webkit', launcher: webkit }
];

const output = [];
let failed = false;

for (const engine of engines) {
  const browser = await engine.launch({ headless: true });
  for (const vp of viewports) {
    const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
    const page = await context.newPage();
    for (const c of checks) {
      const item = { browser: engine.name, viewport: vp.name, page: c.page };
      try {
        await page.goto(base + c.page, { waitUntil: 'networkidle', timeout: 45000 });
        const select = page.locator(c.selector).first();
        await select.waitFor({ state: 'visible', timeout: 15000 });
        const before = await select.inputValue();
        await select.selectOption(c.choose);
        const afterMouse = await select.inputValue();
        item.before = before;
        item.afterMouse = afterMouse;
        item.mouseChanged = before !== afterMouse;

        if (c.keyboardChoose) {
          await select.focus();
          const optionValues = await select.locator('option').evaluateAll((nodes) => nodes.map((n) => n.value));
          const targetIndex = optionValues.indexOf(c.keyboardChoose);
          const currentIndex = optionValues.indexOf(afterMouse);
          if (targetIndex >= 0 && currentIndex >= 0) {
            const move = (targetIndex - currentIndex + optionValues.length) % optionValues.length;
            for (let i = 0; i < move; i += 1) {
              await page.keyboard.press('ArrowDown');
            }
            await page.keyboard.press('Enter');
            const afterKeyboard = await select.inputValue();
            item.afterKeyboard = afterKeyboard;
            item.keyboardChanged = afterKeyboard === c.keyboardChoose;
          } else {
            item.afterKeyboard = afterMouse;
            item.keyboardChanged = false;
          }
        } else {
          item.keyboardChanged = true;
        }

        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
        item.overflowX = overflow;
        item.ok = item.mouseChanged && item.keyboardChanged && overflow === 0;
      } catch (e) {
        item.error = String(e);
        item.ok = false;
      }
      if (!item.ok) failed = true;
      output.push(item);
    }
    await context.close();
  }
  await browser.close();
}

const reportDir = path.resolve('reports/ui');
fs.mkdirSync(reportDir, { recursive: true });
const reportPath = path.resolve(reportDir, 'dropdown-compat-report.json');
fs.writeFileSync(reportPath, JSON.stringify(output, null, 2), 'utf-8');

if (failed) {
  process.exit(1);
}
