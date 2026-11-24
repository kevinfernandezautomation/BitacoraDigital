import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
const base=process.env.FULLSTACK_URL, password=process.env.TEST_LOGIN_PASSWORD,id=process.env.QA_CLOSED_SHEET_ID;
test.skip(!base||!password||!id,'Configurar hoja cerrada QA del regente');
test.beforeEach(async({page})=>{await page.goto(base+'/login/');await page.locator('#id_username').fill('qa_regente');await page.locator('#id_password').fill(password!);await page.getByRole('button',{name:'Ingresar'}).click();await page.goto(base+'/sheet/'+id+'/');});
test('COM-001 publicar sin cambiar expediente',async({page})=>{const url=base+'/sheet/'+id+'/';const before=await (await page.request.get(url+'integrity/')).body();const note='QA '+Date.now();await page.getByLabel('Comentario al margen').fill(note);await page.getByRole('button',{name:'Publicar comentario'}).click();await expect(page.getByText(note,{exact:true})).toBeVisible();const after=await (await page.request.get(url+'integrity/')).body();expect(after.equals(before)).toBeTruthy();});
test('COM-006 CSRF',async({page})=>{expect((await page.request.post(base+'/sheet/'+id+'/action/',{form:{action:'comment',body:'QA'}})).status()).toBe(403);});
test('COM-008 responsive',async({page})=>{await page.setViewportSize({width:320,height:720});await expect(page.getByLabel('Comentario al margen')).toBeVisible();expect(await page.locator('#comentarios').evaluate(e=>e.scrollWidth<=e.clientWidth+1)).toBeTruthy();});
test('COM-009 accesibilidad',async({page})=>{expect((await new AxeBuilder({page}).include('#comentarios').withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([]);});
