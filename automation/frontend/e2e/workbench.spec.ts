import { test, expect } from '@playwright/test';
import { spawn, type ChildProcess } from 'node:child_process';
import { resolve } from 'node:path';
import { readFile } from 'node:fs/promises';
const root = resolve('../..');
async function server(scale = false): Promise<{ process: ChildProcess; url: string }> {
  const process = spawn(resolve(root, 'services/qdrant/runtime/python.exe'), [resolve(root, 'automation/tests/serve_workbench_test.py'), ...(scale ? ['--scale'] : [])], { cwd: root, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  return new Promise((ok, fail) => {
    let output = ''; const timer = setTimeout(() => { process.kill(); fail(Error('测试服务启动超时')); }, 30000);
    process.stdout!.on('data', chunk => { output += chunk; for (const line of output.split('\n')) { try { const value = JSON.parse(line); if (value.url) { clearTimeout(timer); ok({ process, url: value.url }); return; } } catch {} } });
    process.stderr!.on('data', c => { output += c; });
    process.on('exit', code => { clearTimeout(timer); fail(Error(`服务退出 ${code}: ${output}`)); });
  });
}
test('完整导航、关系、证据、候选和摘要', async ({ page }) => {
  const app = await server(); const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  try {
    await page.goto(app.url); await expect(page.getByRole('heading', { name: '把材料连接到问题' })).toBeVisible();
    await page.screenshot({path: resolve(root, 'tmp/workbench-home.png'), fullPage:true});
    await page.getByRole('link', { name: '打开材料关系 →' }).click();
    await expect(page.getByRole('heading', { name: '从问题出发，看见联系' })).toBeVisible();
    await expect(page.getByRole('img', { name: '材料关系图' })).toBeVisible();
    await page.getByLabel('查找中心材料').fill('CLM-SYNTHETIC');
    await page.getByRole('button', { name: /结论 合成计算偏移/ }).click();
    await page.getByRole('button', { name: '以此为中心', exact: true }).click();
    await page.getByRole('button', { name: '加入分析选择' }).click();
    await page.getByLabel('候选标题').fill('检查共同温度来源'); await page.getByLabel('候选解释').fill('测试中的关联建议，未复核');
    await page.getByRole('button', { name: '保存候选', exact: true }).click();
    await expect(page.getByRole('heading', { name: '检查共同温度来源' })).toBeVisible();
    await page.getByRole('button', { name: '主题聚合', exact: true }).click();
    await expect(page.getByRole('button', {name:'折叠所有分组'})).toBeVisible();
    await page.getByRole('button', {name:'全范围结构聚类', exact:true}).click();
    await expect(page.getByText(/Louvain; resolution=1/)).toBeVisible();
    await page.screenshot({path: resolve(root, 'tmp/workbench-groups.png'), fullPage:true});
    await page.getByRole('button', { name: '证据链', exact: true }).click();
    const downloaded = page.waitForEvent('download'); await page.getByRole('button', { name: '导出 JSON', exact: true }).click(); expect((await downloaded).suggestedFilename()).toBe('material-relations.json');
    await page.locator('nav a[href="#/evidence"]').click();
    await page.getByLabel('搜索证据').fill('CLM-SYNTHETIC'); await page.getByRole('button', { name: /结论 合成计算偏移/ }).click();
    await page.getByRole('button', { name: '预览来源', exact: true }).first().click(); await expect(page.getByRole('dialog')).toContainText('temperature_C,offset_ms');
    await page.getByRole('button', { name: '关闭', exact: true }).click();
    await page.screenshot({ path: resolve(root, 'tmp/workbench-evidence.png'), fullPage: true });
    expect(errors).toEqual([]);
  } finally { app.process.kill(); }
});
test('勾选联动图与导出，分类结合搜索且保留跨分类勾选', async ({page, request}) => {
  const app = await server();
  try {
    await page.goto(app.url + '#/relations');
    await expect(page.getByRole('img', {name:'材料关系图'})).toBeVisible();
    const catalog = await (await request.get(app.url + 'api/v1/catalog')).json();
    const expected = (ids: string[]) => {
      const selected = new Set(ids);
      for (const edge of catalog.edges) {
        if (ids.includes(edge.source)) selected.add(edge.target);
        if (ids.includes(edge.target)) selected.add(edge.source);
      }
      return [...selected].sort();
    };
    async function assertExport(ids: string[]) {
      const visible = expected(ids);
      await expect(page.locator('.graph-main')).toContainText(`显示 ${visible.length} 个节点`);
      const pending = page.waitForEvent('download');
      await page.getByRole('button', {name:'导出 JSON', exact:true}).click();
      const file = await (await pending).path();
      const value = JSON.parse(await readFile(file!, 'utf8'));
      expect(value.graph.nodes.map((n:{id:string}) => n.id).sort()).toEqual(visible);
      expect(value.graph.selection.checked.sort()).toEqual([...ids].sort());
    }
    await page.getByRole('checkbox', {name:'分类：结论', exact:true}).check();
    await page.getByLabel('查找中心材料').fill('合成');
    expect(await page.locator('.material-row .eyebrow').allTextContents()).toEqual(['结论']);
    await page.getByLabel('选择 合成计算偏移为 1.4 ms', {exact:true}).check();
    await assertExport(['CLM-SYNTHETIC']);
    await page.getByRole('checkbox', {name:'分类：研究', exact:true}).check();
    const shownKinds = new Set(await page.locator('.material-row .eyebrow').allTextContents());
    expect(shownKinds).toEqual(new Set(['结论', '研究']));
    await page.getByRole('checkbox', {name:'分类：结论', exact:true}).uncheck();
    await expect(page.getByLabel('选择 合成计算偏移为 1.4 ms', {exact:true})).toHaveCount(0);
    await page.locator('[data-material-id="RES-SYNTHETIC"] input[type="checkbox"]').check();
    await assertExport(['CLM-SYNTHETIC', 'RES-SYNTHETIC']);
    await page.getByRole('checkbox', {name:'分类：研究', exact:true}).uncheck();
    expect(new Set(await page.locator('.material-row .eyebrow').allTextContents()).size).toBeGreaterThan(2);
    await page.getByRole('checkbox', {name:'分类：结论', exact:true}).check();
    await expect(page.getByLabel('选择 合成计算偏移为 1.4 ms', {exact:true})).toBeChecked();
    await page.getByLabel('选择 合成计算偏移为 1.4 ms', {exact:true}).uncheck();
    await assertExport(['RES-SYNTHETIC']);
    await page.getByRole('button', {name:'清空勾选', exact:true}).click();
    await expect(page.locator('.graph-main')).toContainText(`显示 ${catalog.nodes.length} 个节点`);
  } finally { app.process.kill(); }
});

test('一万节点十万关系下局部图和轻量状态响应', async ({ page, request }) => {
  const app = await server(true);
  try {
    await page.goto(app.url + '#/relations'); await expect(page.getByRole('img', { name: '材料关系图' })).toBeVisible();
    await page.getByLabel('查找中心材料').fill('合成材料 0');
    await page.locator('[data-material-id="N0"] button').click();
    const start = Date.now(); await page.getByRole('button', { name: '以此为中心', exact: true }).click();
    await expect(page.locator('.graph-main')).toContainText('显示 21 个节点');
    await page.getByRole('button', {name:'适应画面', exact:true}).click();
    const elapsed = Date.now() - start; expect(elapsed).toBeLessThan(3000);
    await page.getByRole('button', {name:'全范围结构聚类', exact:true}).click();
    const t = Date.now(); const response = await request.get(app.url + 'api/v1/capabilities'); expect(response.ok()).toBeTruthy(); const apiMs = Date.now() - t; expect(apiMs).toBeLessThan(500);
    console.log(JSON.stringify({scaleNodes:10000, scaleEdges:100000, localInteractionMs:elapsed, statusMs:apiMs}));
    await page.screenshot({ path: resolve(root, 'tmp/workbench-scale.png'), fullPage: true });
  } finally { app.process.kill(); }
});
