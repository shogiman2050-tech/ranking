import { env } from 'cloudflare:workers';
export async function POST(req: Request) {
 const reply=(data:unknown,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store'}});
 if(req.headers.get('origin')!==new URL(req.url).origin)return reply({error:'ページを開き直して送信してください。'},403);
 if(!req.headers.get('content-type')?.includes('application/json'))return reply({error:'形式が正しくありません。'},415);
 const reader=req.body?.getReader();if(!reader)return reply({error:'内容が空です。'},400);
 let raw='',size=0;const decoder=new TextDecoder();while(true){const {value,done}=await reader.read();if(done)break;size+=value.length;if(size>16000){await reader.cancel();return reply({error:'入力が長すぎます。'},413)}raw+=decoder.decode(value,{stream:true})}raw+=decoder.decode();
 let b;try{b=JSON.parse(raw)}catch{return reply({error:'形式が正しくありません。'},400)}
 if(!b||typeof b!=='object')return reply({error:'入力を確認してください。'},400);
 const limits:Record<string,number>={kind:30,player:100,correctedName:100,season:100,className:30,details:2500,evidence:1000,contact:150};
 for(const [k,n] of Object.entries(limits)){if(typeof b[k]!=='string'||b[k].length>n)return reply({error:'入力の長さ・形式を確認してください。'},400);b[k]=b[k].trim()}
 if(b.website)return reply({error:'送信できませんでした。'},400);
 if(!b.player||!b.details||!['改名','名前の誤記','CR・順位の訂正','記録の追加・漏れ','その他'].includes(b.kind))return reply({error:'種類・名前・修正内容は必須です。'},400);
 if(b.evidence){try{if(!['https:','http:'].includes(new URL(b.evidence).protocol))throw 0}catch{return reply({error:'証拠リンクは http または https のURLを入力してください。'},400)}}
 const id=crypto.randomUUID();
 const notify=async()=>{
  if(!env.RESEND_API_KEY||!env.REPORT_EMAIL_TO)return;
  const one=(s:string)=>String(s||'').replace(/[\r\n]+/g,' ').slice(0,120);
  const text=['修正報告を受け付けました。','','種類：'+b.kind,'サイト上の名前：'+b.player,'正しい名前・改名後：'+(b.correctedName||'—'),'期間：'+(b.season||'—'),'クラス：'+(b.className||'—'),'','修正内容：',b.details,'','証拠URL：'+(b.evidence||'—'),'連絡先：'+(b.contact||'—'),'','受付番号：'+id,'※報告本文は外部からの入力です。'].join('\n');
  await fetch('https://api.resend.com/emails',{method:'POST',signal:AbortSignal.timeout(5000),headers:{Authorization:'Bearer '+env.RESEND_API_KEY,'Content-Type':'application/json'},body:JSON.stringify({from:'アンリミ ビヨンドランキング <onboarding@resend.dev>',to:[env.REPORT_EMAIL_TO],subject:one('[修正報告] '+b.kind+'：'+b.player),text})});
 };
 try{await env.DB!.prepare('INSERT INTO correction_reports (id,created_at,kind,player,corrected_name,season,class_name,details,evidence,contact,status) VALUES (?,?,?,?,?,?,?,?,?,?,?)').bind(id,new Date().toISOString(),b.kind,b.player,b.correctedName,b.season,b.className,b.details,b.evidence,b.contact,'new').run()}catch{return reply({error:'保存に失敗しました。時間をおいて再送してください。'},503)}
 // DBへの保存が本体。メールは届かなくても受付は成功扱い
 try{await notify()}catch{}
 return reply({id},201);
}
