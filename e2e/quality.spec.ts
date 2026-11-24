import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
const url=process.env.DEMO_URL||'http://localhost:8080';
for(const role of ['Regente','Empresa','Fiscalía','Administración','Soporte']){
 test(`visibilidad de borrador: ${role}`,async({page})=>{await page.goto(url);await page.locator('#role').selectOption(role);if(role==='Regente')await expect(page.locator('#draft')).toBeVisible();else await expect(page.locator('#draft')).toBeHidden();});
}
for(const width of [360,768,1280])test(`sin desbordamiento ${width}`,async({page})=>{await page.setViewportSize({width,height:800});await page.goto(url);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();});
test('accesibilidad automatizada',async({page})=>{await page.goto(url);const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();expect(result.violations).toEqual([]);});
