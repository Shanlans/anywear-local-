import http from 'node:http';

export function proxyLab(req,res){
  const port=Number(process.env.ANYWEAR_LAB_API_PORT||8001);
  const headers={host:`127.0.0.1:${port}`};
  for(const name of ['content-type','content-length','accept','origin','x-lab-nonce','last-event-id','if-none-match'])
    if(req.headers[name])headers[name]=req.headers[name];
  const upstream=http.request({hostname:'127.0.0.1',port,path:req.url,method:req.method,headers},response=>{
    res.writeHead(response.statusCode||502,response.headers);response.pipe(res);
  });
  upstream.on('error',()=>{
    if(!res.headersSent)res.writeHead(503,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});
    res.end(JSON.stringify({error:'LAB_BACKEND_UNAVAILABLE'}));
  });
  let size=0;
  req.on('data',chunk=>{size+=chunk.length;if(size>65536){upstream.destroy();if(!res.headersSent)res.writeHead(413);res.end();}});
  res.on('close',()=>upstream.destroy());req.pipe(upstream);
}
