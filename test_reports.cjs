const fs=require('fs'),vm=require('vm'),assert=require('assert');
let writes=[];
const env={DB:{prepare(sql){assert(sql.startsWith('INSERT INTO correction_reports'));return {bind(...values){return {async run(){writes.push(values);return {success:true}}}}}}}};
let src=fs.readFileSync('app/api/reports/route.ts','utf8').replace("import { env } from 'cloudflare:workers';",'').replace('export async function','async function').replace('req: Request','req').replace('data:unknown','data').replace(':Record<string,number>','').replace('env.DB!','env.DB').replace('(s:string)','(s)');
let mails=[];const ctx={env,Response,Request,TextDecoder,URL,AbortSignal,crypto:require('crypto').webcrypto,fetch:async(url,opt)=>{mails.push([url,JSON.parse(opt.body),opt.headers]);if(ctx.failMail)throw Error('down');return new Response('{}')}};vm.createContext(ctx);vm.runInContext(src,ctx);
const valid={kind:'名前の誤記',player:'テスト',correctedName:'正しい名前',season:'',className:'',details:'テスト報告',evidence:'',contact:'',website:''};
async function send(body,origin='https://example.test'){return ctx.POST(new Request('https://example.test/api/reports',{method:'POST',headers:{origin,'content-type':'application/json'},body:JSON.stringify(body)}))}
(async()=>{assert.equal((await send(valid)).status,201);assert.equal(writes.length,1);assert.equal((await send({...valid,details:''})).status,400);assert.equal((await send({...valid,evidence:'javascript:alert(1)'})).status,400);assert.equal((await send(valid,'https://else.test')).status,403);assert.equal((await send({...valid,website:'spam'})).status,400);assert.equal(writes.length,1);assert.equal(mails.length,0);
env.RESEND_API_KEY='k';env.REPORT_EMAIL_TO='to@example.test';
assert.equal((await send({...valid,player:'改行\nあり'})).status,201);assert.equal(mails.length,1);assert.equal(mails[0][0],'https://api.resend.com/emails');assert.deepEqual(mails[0][1].to,['to@example.test']);assert(!mails[0][1].subject.includes('\n'));assert(mails[0][1].text.includes('テスト報告'));
ctx.failMail=true;assert.equal((await send(valid)).status,201);
env.DB.prepare=()=>{throw Error('DB offline')};assert.equal((await send(valid)).status,503);console.log('Report validation, persistence call and failure handling passed')})();
