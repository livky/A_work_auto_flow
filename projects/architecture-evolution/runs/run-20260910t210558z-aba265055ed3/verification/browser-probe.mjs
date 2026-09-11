import { chromium } from "../../automation/frontend/node_modules/playwright-core/index.mjs";
import { readFile, writeFile } from "node:fs/promises";
const base = JSON.parse((await readFile('.local/material-query-v2/server.log','utf8')).trim().split(/\r?\n/)[0]).url;
const browser = await chromium.launch({channel:'msedge',headless:true});
const page = await browser.newPage({viewport:{width:1600,height:1100}});
page.setDefaultTimeout(60000);
const responses=[];
page.on('response',async r=>{if(r.url().includes('materials'))try{responses.push({url:r.url().split('/api/')[1],body:await r.json()});}catch{}});
try {
 await page.goto(base+'#/materials');
 await page.getByRole('button',{name:'清空类型',exact:true}).click();
 await page.getByLabel('类型：Research 研究',{exact:true}).check();
 await page.getByLabel('查找归属对象',{exact:true}).fill('浮点');
 await page.getByRole('button',{name:/浮点求和.*归属对象/}).click();
 await page.getByLabel('问题',{exact:true}).fill('浮点');
 await page.getByRole('button',{name:'开始查询',exact:true}).click();
 await page.waitForFunction(()=>Array.from(document.querySelectorAll('.material-search button')).some(n=>n.textContent.trim()==='开始查询'&&!n.disabled),null,{timeout:60000});
 const output=page.getByRole('complementary',{name:'查询返回结果'});
 const observations=[];
 let actionNumber=0;
 await page.getByRole('button',{name:'全选候选',exact:true}).click();
 for (const name of ['组装所选材料（2）','组装所选材料（2）','返回完整文稿','展开研究经过','展开技术内容','深化所选材料']) {
   const action=page.getByRole('button',{name,exact:true});
   await action.click();
   await page.waitForFunction(()=>Array.from(document.querySelectorAll('.material-search button')).some(n=>n.textContent.trim()==='开始查询'&&!n.disabled),null,{timeout:60000});
   observations.push({action:name,output:await output.innerText()});
   await page.screenshot({path:`.local/material-query-v2/action-${++actionNumber}.png`,fullPage:false});
   if(name==='返回完整文稿') {
     const docImages=await output.locator('img').count();
     observations.at(-1).images=docImages;
     observations.at(-1).document_count=await output.locator('.packet-documents > article').count();
     if(docImages) { await output.locator('img').first().scrollIntoViewIfNeeded(); await page.screenshot({path:'.local/material-query-v2/document-figure.png',fullPage:false}); }
   }
 }
 await writeFile('.local/material-query-v2/browser-actions.json',JSON.stringify(observations,null,2));
 await writeFile('.local/material-query-v2/browser-probe-text.txt',await page.locator('body').innerText());
 await page.screenshot({path:'.local/material-query-v2/probe.png',fullPage:true});
} catch(e) { console.error(e); await writeFile('.local/material-query-v2/browser-probe-text.txt',await page.locator('body').innerText()); }
finally {await writeFile('.local/material-query-v2/browser-probe-responses.json',JSON.stringify(responses,null,2));await browser.close();}
