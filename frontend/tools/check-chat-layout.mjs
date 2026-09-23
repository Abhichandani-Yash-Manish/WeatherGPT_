import { chromium, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {writeFile} from 'node:fs/promises';
const out='../research/design/2026-09-23-chat-refinement'; const b=await chromium.launch();
const context=await b.newContext({viewport:{width:1440,height:900}, reducedMotion:'reduce'}); const p=await context.newPage();const report=[];
async function audit(state){console.log('Checking '+state); const a=await new AxeBuilder({page:p}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa','best-practice']).analyze();report.push({state,violations:a.violations.map(v=>({rule:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))}); await writeFile(out+'/layout-acceptance.json',JSON.stringify(report,null,2));}
await p.goto('http://127.0.0.1:8765/#/assistant');
await p.locator('.g-composer-context > button').click();await p.getByRole('searchbox',{name:'Place',exact:true}).fill('Nadiad');
await p.getByRole('option').filter({hasText:'Nadiād'}).first().click();
await p.locator('.w-now').waitFor();await p.locator('.g-language-trigger').waitFor();await p.locator('.w-greeting').click();
await p.screenshot({path:out+'/welcome-final-1440.png'});await audit('welcome');
await p.locator('.g-language-trigger').click();await p.screenshot({path:out+'/language-final.png'});await audit('language list');await p.keyboard.press('Escape');
await p.locator('.g-composer-context > button').click();await p.getByRole('searchbox',{name:'Place',exact:true}).fill('Pune');await p.getByRole('option').first().waitFor();await audit('place picker');await p.keyboard.press('Escape');await expect(p.getByRole('dialog')).not.toBeVisible();
for(const width of [768,360]){await p.setViewportSize({width,height:900});await p.screenshot({path:out+'/welcome-final-'+width+'.png'});report.push({state:'welcome '+width,overflow:await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth)});}
await p.setViewportSize({width:1440,height:900});await p.locator('button').filter({hasText:'Will it rain in Pune tomorrow?'}).first().click();await p.locator('.g-answer').first().waitFor();
await p.screenshot({path:out+'/answer-final-1440.png'});await audit('restored answer');
await p.locator('.g-evidence-entry summary').first().click();await expect(p.locator('.g-evidence-receipts').first()).toBeVisible();
report.push({state:'source receipt opens',passed:true});
await p.locator('.g-you').last().scrollIntoViewIfNeeded();
for(const width of [768,360]){await p.setViewportSize({width,height:900});await p.locator('.g-you').last().scrollIntoViewIfNeeded();await p.screenshot({path:out+'/answer-final-'+width+'.png'});report.push({state:'answer '+width,overflow:await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth)});}
await writeFile(out+'/layout-acceptance.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));await b.close();
if (report.some(r=>r.overflow || r.violations?.length)) process.exitCode=1;
