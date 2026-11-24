import {test,expect} from '@playwright/test';
test('perfil empresa no crea borradores',async({page})=>{await page.goto(process.env.DEMO_URL||'http://localhost:8080');await page.locator('#role').selectOption('Empresa');await expect(page.locator('#draft')).toBeHidden();await expect(page.getByText('Inspección de almacenamiento')).toBeVisible();});
