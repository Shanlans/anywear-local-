import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import http from 'node:http';
const port=3067,base=`http://127.0.0.1:${port}`;
test('local server protects credentials and token issuance',async()=>{
 const child=spawn(process.execPath,['server.mjs'],{env:{...process.env,PORT:String(port),DECART_API_KEY:''},stdio:['ignore','pipe','pipe']});
 try{
  await Promise.race([once(child.stdout,'data'),once(child,'exit').then(()=>{throw Error('Server exited before listening')}),new Promise((_,reject)=>{const timer=setTimeout(()=>reject(Error('Startup timeout')),10000);timer.unref();})]);
  let r=await fetch(base+'/api/status');let status=await r.json();assert.equal(status.configured,false);assert.equal(Object.hasOwn(status,'apiKey'),false);
  r=await fetch(base+'/api/local-products');assert.equal(r.status,200);const catalog=await r.json();assert.ok(Array.isArray(catalog.products));
  for(const p of catalog.products){for(const view of p.views){const photo=await fetch(base+view.image);assert.equal(photo.status,200);assert.match(photo.headers.get('content-type'),/^image\//);assert.ok((await photo.arrayBuffer()).byteLength>0);}}
  r=await fetch(base+'/local-products/%2e%2e%2f.env');assert.equal(r.status,404);
  r=await fetch(base+'/src/local-catalog.js');assert.equal(r.status,404);
  r=await fetch(base+'/.env');assert.equal(r.status,404);
  r=await fetch(base+'/server.mjs');assert.equal(r.status,404);
  const badHost=await new Promise((resolve,reject)=>{const req=http.request(base+'/api/status',{headers:{Host:'evil.example'}},res=>{res.resume();resolve(res.statusCode);});req.on('error',reject);req.end();});assert.equal(badHost,403);
  r=await fetch(base+'/api/token',{method:'POST'});assert.equal(r.status,403);
  r=await fetch(base+'/api/token',{method:'POST',headers:{'X-Anywear-Request':'1',Origin:'https://evil.example'}});assert.equal(r.status,403);
  r=await fetch(base+'/api/token',{method:'POST',headers:{'X-Anywear-Request':'1'}});assert.equal(r.status,503);
  r=await fetch(base);assert.equal(r.status,200);assert.match(await r.text(),/Anywear/);
 }finally{child.kill('SIGTERM');await once(child,'exit');}
});
