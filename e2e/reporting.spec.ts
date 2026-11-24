import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
const base=process.env.FULLSTACK_URL,password=process.env.TEST_LOGIN_PASSWORD;
test.skip(!base||!password,'Configurar QA');
async function login(page:any,role:string){await page.goto(base+'/login/');await page.locator('#id_username').fill('qa_'+role);await page.locator('#id_password').fill(password!);await page.getByRole('button',{name:'Ingresar'}).click();}
test('filtros y exportación',async({page})=>{await login(page,'admin');await page.goto(base+'/reports/');await page.getByLabel('Desde').fill('2026-01-01');await page.getByLabel('Hasta').fill('2026-12-31');await page.getByRole('button',{name:'Filtrar'}).click();await expect(page).toHaveURL(/start=2026-01-01/);const r=await page.request.get(base+'/reports/?format=csv');expect(r.headers()['content-type']).toContain('text/csv');});
test('empresa no autorizada',async({page})=>{await login(page,'empresa');expect((await page.request.get(base+'/reports/')).status()).toBe(403);expect((await page.request.get(base+'/reports/?format=csv')).status()).toBe(403);});
test('responsive y accesibilidad',async({page})=>{await login(page,'fiscalia');await page.setViewportSize({width:320,height:720});await page.goto(base+'/reports/');expect(await page.locator('#fiscalizacion').evaluate(e=>e.scrollWidth<=e.clientWidth+1)).toBeTruthy();expect((await new AxeBuilder({page}).include('#fiscalizacion').withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([]);});
