import http from 'k6/http';import {check,sleep} from 'k6';
export const options={vus:2,duration:'30s',thresholds:{http_req_duration:['p(95)<2000'],checks:['rate>0.99'],http_req_failed:['rate<0.01']}};
export function setup(){if(__ENV.AUTHORIZED_LOAD_TEST!=='yes'||!__ENV.BASE_URL||!__ENV.TEST_LOGIN_PASSWORD||!__ENV.QA_CLOSED_SHEET_ID)throw Error('Solo ambiente QA autorizado');}
let logged=false;
export default function(){const base=__ENV.BASE_URL;if(!logged){const p=http.get(base+'/login/');const csrf=p.html().find('[name=csrfmiddlewaretoken]').attr('value');const r=http.post(base+'/login/',{username:'qa_regente',password:__ENV.TEST_LOGIN_PASSWORD,csrfmiddlewaretoken:csrf},{headers:{Referer:base+'/login/'},redirects:0});logged=check(r,{'login':x=>x.status===302});}const r=http.get(base+'/sheet/'+__ENV.QA_CLOSED_SHEET_ID+'/?comments_page=1');check(r,{'repositorio autorizado':x=>x.status===200&&x.body.includes('Comentarios al margen')});sleep(1);}
