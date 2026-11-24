import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
const base=process.env.FULLSTACK_URL;
const password=process.env.TEST_LOGIN_PASSWORD||'';
test.skip(!base||!password,'Configure FULLSTACK_URL y TEST_LOGIN_PASSWORD; ejecute seed_login_test');
const url=(path:string)=>new URL(path,base).href;
for(const role of ['regente','empresa','fiscalia','admin','soporte']){
 test(`login y logout ${role}`,async({page})=>{
  await page.goto(url('/login/')); await page.getByLabel('Usuario',{exact:true}).fill('qa_'+role); await page.getByLabel('Contraseña',{exact:true}).fill(password); await page.getByRole('button',{name:'Ingresar'}).click(); await expect(page).toHaveURL(url('/')); await expect(page.getByText(`qa_${role} (${role})`,{exact:false})).toBeVisible(); await page.getByRole('button',{name:'Salir'}).click(); await expect(page).toHaveURL(url('/login/'));
 });
}
for(const [name,user,pass] of [['incorrecta','qa_regente','wrong'],['inexistente','qa_missing','wrong'],['inactivo','qa_inactive',password]]){
 test(`rechazo ${name}`,async({page})=>{await page.goto(url('/login/'));await page.locator('#id_username').fill(user);await page.locator('#id_password').fill(pass);await page.getByRole('button',{name:'Ingresar'}).click();await expect(page.getByRole('alert')).toHaveText('Usuario o contraseña incorrectos.');});
}
test('CSRF obligatorio',async({request})=>{expect((await request.post(url('/login/'),{form:{username:'qa_regente',password}})).status()).toBe(403);});
test('acceso anónimo',async({page})=>{await page.goto(url('/'));await expect(page).toHaveURL(/\/login\/\?next=/);});
test('sin redirección externa',async({page})=>{await page.goto(url('/login/?next=https://example.invalid'));await page.locator('#id_username').fill('qa_regente');await page.locator('#id_password').fill(password);await page.getByRole('button',{name:'Ingresar'}).click();await expect(page).toHaveURL(url('/'));});
for(const width of [320,360,768,1280])test(`responsive ${width}`,async({page})=>{await page.setViewportSize({width,height:800});await page.goto(url('/login/'));expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();await expect(page.getByRole('button',{name:'Ingresar'})).toBeVisible();});
test('mostrar contraseña',async({page})=>{await page.goto(url('/login/'));await page.getByRole('button',{name:'Mostrar'}).click();await expect(page.locator('#id_password')).toHaveAttribute('type','text');await page.getByRole('button',{name:'Ocultar'}).click();await expect(page.locator('#id_password')).toHaveAttribute('type','password');});
test('accesibilidad login',async({page})=>{await page.goto(url('/login/'));expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([]);});
