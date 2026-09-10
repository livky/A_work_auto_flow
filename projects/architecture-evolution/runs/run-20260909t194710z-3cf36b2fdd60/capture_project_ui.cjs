/* Actual Project UI inspection. This uses the real server and byte-identical
 * canonical records; it neither intercepts responses nor writes business data.
 * Usage: node capture_project_ui.cjs BASE_URL NEW_OUTPUT_DIRECTORY
 * Failure preserves screenshots, response captures, and an explicit error. */
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(path.resolve(__dirname, '../../../../automation/frontend/node_modules/playwright'));
async function main() {
  const [base, output] = process.argv.slice(2);
  if (!base || !output) throw new Error('BASE_URL and NEW_OUTPUT_DIRECTORY are required');
  fs.mkdirSync(output, { recursive: false });
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const receipt = { started_at: new Date().toISOString(), errors: [], captures: [], documents: [] };
  const pending = [];
  page.on('pageerror', e => receipt.errors.push(String(e)));
  page.on('response', response => {
    if (response.url().includes('/api/v1/memory/') && response.request().method() === 'POST') {
      const n = pending.length;
      pending.push(response.text().then(body => {
        fs.writeFileSync(path.join(output, `response-${n}.json`), body);
        receipt.documents.push({ operation: response.url().split('/api/v1/memory/')[1], status: response.status(), file: `response-${n}.json` });
      }));
    }
  });
  async function capture(name) {
    await page.screenshot({ path: path.join(output, name + '.png') });
    fs.writeFileSync(path.join(output, name + '.txt'), await page.locator('body').innerText());
    receipt.captures.push({ name, overflow: await page.evaluate(() => document.documentElement.scrollWidth > innerWidth),
      formula_count: await page.locator('.katex-display').count(), section_count: await page.locator('.research-paper > section').count() });
  }
  try {
    await page.goto(base.replace(/\/$/, '') + '/#/memory');
    await page.getByLabel('记忆归属对象').selectOption('PRJ-ARCHITECTURE-EVOLUTION');
    await page.getByRole('button', { name: '研究经过', exact: true }).click();
    await page.getByRole('button', { name: '读取研究经过', exact: true }).click();
    await page.locator('.research-paper').waitFor();
    await capture('process-desktop');
    const navigation = page.getByRole('navigation', { name: '研究文稿目录' });
    await navigation.getByRole('link', { name: '表示查询运行实现：契约、范围和累计资源', exact: true }).click();
    const section = page.locator('.research-paper > section').filter({ has: page.getByRole('heading', { name: /表示查询运行实现：契约、范围和累计资源/ }) });
    await section.locator('.katex-display').first().scrollIntoViewIfNeeded();
    await capture('process-formula');
    receipt.selected_section_text = await section.innerText();
    await page.getByLabel('文稿类型').selectOption('research_report');
    await page.getByRole('button', { name: '读取研究经过', exact: true }).click();
    await page.getByRole('heading', { name: '表示查询：当前实现与核心简报', exact: true }).waitFor();
    await page.locator('.research-paper').scrollIntoViewIfNeeded();
    await capture('brief-desktop');
    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator('.research-paper > section').first().scrollIntoViewIfNeeded();
    await capture('brief-mobile');
    receipt.status = 'completed';
  } catch (error) {
    receipt.status = 'failed'; receipt.failure = String(error);
    await page.screenshot({ path: path.join(output, 'failure.png') }).catch(() => {});
    process.exitCode = 1;
  } finally {
    await Promise.allSettled(pending);
    receipt.ended_at = new Date().toISOString();
    fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify(receipt, null, 2));
    await browser.close();
  }
}
main().catch(e => { console.error(e); process.exitCode = 1; });
