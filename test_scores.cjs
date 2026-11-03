const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const page=fs.readFileSync('page.html','utf8');
const achievements=page.slice(page.indexOf('function achievementRows('),page.indexOf('function summarize('));
const code=page.slice(page.indexOf('const MODELS='),page.indexOf('function renderScore()'));
const api=vm.runInNewContext(`const pkey=r=>r.personKey||r.name;const norm=s=>s.normalize('NFKC').toLowerCase();${achievements}${code};({MODELS,scoreTotals,achievementRows})`);
for(const model of Object.keys(api.MODELS)){
 const scores=[100,101,999].map(rank=>api.scoreTotals([{name:'player',rank,cr:1900}],model).get('player').score);
 assert.equal(scores[0],scores[1]);assert.equal(scores[0],scores[2]);assert.ok(Number.isFinite(scores[0]));
 for(const rank of [null,0,undefined,-1])assert.equal(api.scoreTotals([{name:'player',rank,cr:1900}],model).size,0);
 const total=api.scoreTotals([{name:'player',rawName:'OLD',rank:1,cr:1900},{name:'player',season:'next',rank:2,cr:1900}],model).get('player');
 assert.equal(total.score,api.MODELS[model].f(1)+api.MODELS[model].f(2));assert.ok(total.search.has('old'));
}
console.log('3 models: rank cap, invalid ranks, totals and old-name search passed');

for(const model of Object.keys(api.MODELS)){const rows=[{name:'あ',season:'s',className:'c',rank:17,cr:1860},{name:'あ',season:'s',className:'c',rank:50,cr:1855}];const a=api.scoreTotals(rows,model).get('あ');assert.equal(a.count,1);assert.equal(a.score,api.MODELS[model].f(17));assert.equal(rows.length,2)}
