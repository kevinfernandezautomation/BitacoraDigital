import http from 'k6/http';
import {check,sleep} from 'k6';
import {Rate} from 'k6/metrics';
const failures=new Rate('login_failures');
export const options={vus:2,duration:'20s',thresholds:{http_req_duration:['p(95)<2000'],login_failures:['rate<0.01']}};
export default function(){
 const base=__ENV.BASE_URL; if(!base||!__ENV.TEST_LOGIN_PASSWORD||__ENV.AUTHORIZED_LOAD_TEST!=='yes')throw new Error('Configure ambiente autorizado');
 const page=http.get(base+'/login/'); const token=page.html().find('input[name=csrfmiddlewaretoken]').attr('value');
 const res=http.post(base+'/login/',{username:__VU===1?'qa_regente':'qa_empresa',password:__ENV.TEST_LOGIN_PASSWORD,csrfmiddlewaretoken:token},{headers:{Referer:base+'/login/'},redirects:0});
 failures.add(!check(res,{'login redirect':r=>r.status===302,'dashboard':r=>r.headers.Location==='/'}));
 const home=http.get(base+'/'); const csrf=home.html().find('input[name=csrfmiddlewaretoken]').attr('value');
 http.post(base+'/logout/',{csrfmiddlewaretoken:csrf},{headers:{Referer:base+'/'},redirects:0});sleep(2);
}
