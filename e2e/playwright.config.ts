import {defineConfig,devices} from '@playwright/test';
export default defineConfig({reporter:[['html',{open:'never'}],['list']],projects:[{name:'chromium',use:devices['Desktop Chrome']},{name:'firefox',use:devices['Desktop Firefox']},{name:'webkit',use:devices['Desktop Safari']}],use:{trace:'retain-on-failure',screenshot:'only-on-failure'}});
