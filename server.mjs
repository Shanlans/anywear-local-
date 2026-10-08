import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import dotenv from 'dotenv';
import { createDecartClient } from '@decartai/sdk';
const root = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({path:path.join(root,'.env'),quiet:true});
const port=Number(process.env.PORT||3000);
const model=process.env.DECART_MODEL||'lucy-vton-latest';
const maxSessionSeconds=Math.max(10, Math.min(1800,Number(process.env.MAX_SESSION_SECONDS)||300));
const client=process.env.DECART_API_KEY ? createDecartClient({apiKey:process.env.DECART_API_KEY}) : null;
const webRoot=path.join(root,'dist');
if(!fs.existsSync(path.join(webRoot,'index.html')))throw new Error('请先运行 npm run build');
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.png':'image/png','.json':'application/json'};
let lastMint=0;
const json=(res,status,body)=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});res.end(JSON.stringify(body));};
const server=http.createServer(async(req,res)=>{
  const host=req.headers.host;
  if(![`localhost:${port}`,`127.0.0.1:${port}`].includes(host)){return json(res,403,{error:'仅允许本机访问'});}
  if(req.url==='/api/status' && req.method==='GET')return json(res,200,{configured:!!client,model,maxSessionSeconds});
  if(req.url==='/api/token' && req.method==='POST'){
    const origin=req.headers.origin;
    if(origin && ![`http://localhost:${port}`,`http://127.0.0.1:${port}`].includes(origin))return json(res,403,{error:'不允许此来源'});
    if(req.headers['x-anywear-request']!=='1')return json(res,403,{error:'缺少本地请求标识'});
    if(!client)return json(res,503,{error:'请在 .env 中配置 DECART_API_KEY，然后重启服务。'});
    if(Date.now()-lastMint<2000)return json(res,429,{error:'请求太快，请稍后再试。'});
    lastMint=Date.now();
    try{
      const token=await client.tokens.create({expiresIn:60,allowedModels:[model],allowedOrigins:[`http://localhost:${port}`,`http://127.0.0.1:${port}`],constraints:{realtime:{maxSessionDuration:maxSessionSeconds}}});
      return json(res,200,{apiKey:token.apiKey,expiresAt:token.expiresAt});
    }catch(error){
      // Do not log credentials, upstream request headers or raw SDK errors.
      const status=Number(error.status||error.statusCode||0);
      return json(res,502,{error:status===401||status===403?'Decart 拒绝密钥或权限，请检查密钥与账户权限。':'Decart 无法签发会话令牌，请检查网络、密钥和账户额度。',code:error.code||'TOKEN_FAILED'});
    }
  }
  if(req.url?.startsWith('/api/'))return json(res,404,{error:'接口不存在'});
  if(req.method!=='GET' && req.method!=='HEAD')return json(res,405,{error:'方法不允许'});
  let pathname;
  try{pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);}catch{return json(res,400,{error:'无效路径'});}
  const file=path.resolve(webRoot,'.'+(pathname==='/'?'/index.html':pathname));
  if(!file.startsWith(webRoot+path.sep))return json(res,403,{error:'访问被拒绝'});
  try{const stat=fs.statSync(file);if(!stat.isFile())throw Error();res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'});if(req.method==='HEAD')return res.end();fs.createReadStream(file).pipe(res);}catch{return json(res,404,{error:'文件不存在'});}
});
server.listen(port,'127.0.0.1',()=>console.log(`Anywear 本地试衣已启动：http://localhost:${port}`));
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>{server.close(()=>process.exit(0));});
