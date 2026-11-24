import {test,expect} from '@playwright/test';
const base=process.env.FULLSTACK_URL, password=process.env.TEST_LOGIN_PASSWORD,rid=process.env.QA_APPROVED_REGENCY_ID;
test.skip(!base||!password||!rid,'Configurar QA');
test('CIE-001 cierre, expediente e integridad',async({page})=>{
 await page.goto(base+'/login/'); await page.locator('#id_username').fill('qa_regente'); await page.locator('#id_password').fill(password!); await page.getByRole('button',{name:'Ingresar'}).click();
 await page.goto(base+'/regency/'+rid+'/new/'); await page.locator('#id_date').fill('2026-11-24'); await page.locator('#id_title').fill('Cierre QA'); await page.locator('#id_body').fill('Contenido original'); await page.getByRole('button',{name:'Guardar borrador'}).click();
 await page.getByRole('checkbox').check(); await page.getByRole('button',{name:/Cerrar definitivamente/}).click(); await expect(page.getByText('Editar borrador')).toHaveCount(0); const url=page.url();
 expect((await page.request.get(url+'integrity/')).status()).toBe(200); expect((await page.request.get(url+'archive/')).status()).toBe(200);
 expect((await page.request.post(url+'action/',{form:{action:'close',confirm_close:'yes'}})).status()).toBe(403);
});
