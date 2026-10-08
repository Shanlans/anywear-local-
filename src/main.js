import { createDecartClient, models, resolveFpsNumber } from '@decartai/sdk';
import './style.css';
import {installI18n} from './i18n.js';
import {mountBilling,billing} from './billing.js';
const $=id=>document.getElementById(id);
const products=[
{id:'tee',name:'雾白圆领 T 恤',category:'tops',color:'雾白',detail:'棉感 · 宽松短袖',prompt:'Substitute the upper body garment with an off-white plain cotton crew-neck short-sleeve t-shirt with a relaxed fit.'},
{id:'hoodie',name:'鼠尾草绿卫衣',category:'tops',color:'浅绿',detail:'连帽 · 袋鼠口袋',prompt:'Substitute the upper body garment with a sage green pullover hoodie with long sleeves, drawstrings and a kangaroo pocket.'},
{id:'shirt',name:'蓝色牛仔衬衫',category:'tops',color:'靛蓝',detail:'双口袋 · 纽扣闭合',prompt:'Substitute the upper body garment with a blue denim long-sleeve collared shirt, buttoned closed, with two chest pockets.'},
{id:'jeans',name:'经典直筒牛仔裤',category:'bottoms',color:'靛蓝',detail:'中腰 · 直筒长裤',prompt:'Substitute the lower body garment with indigo blue straight-leg denim jeans with front pockets and visible seams.'},
{id:'trousers',name:'沙色宽腿长裤',category:'bottoms',color:'沙色',detail:'宽腿 · 简洁剪裁',prompt:'Substitute the lower body garment with sand beige wide-leg tailored trousers with a clean waistband and front pleats.'},
{id:'sneakers',name:'极简白色运动鞋',category:'shoes',color:'白色',detail:'低帮 · 鞋类实验',prompt:'Substitute the footwear with white low-top leather sneakers with white laces, a clean toe box and a thin rubber sole.'},
];
for(const p of products)p.image=`/products/${p.id}.png`;
let selected=products[0],category='all',camera=null,portrait=null,rt=null,raf=0,epoch=0,busy=false,applying=false,selectionVersion=0,config=null,sessionTimer=0,frameTimer=0;
const objectURLs=[];
const promptDrafts=new Map();
let requested=null;
const draftKey=()=>selected.id+'|'+selected.image;
function showPrompt(){ $('promptEditor').value=promptDrafts.get(draftKey())??selected.prompt; }
function submitDraft(){const prompt=$('promptEditor').value.trim();if(!prompt){message('请填写提示词，或恢复默认提示词。',true);return false;}requested={...selected,prompt};selectionVersion++;return true;}
document.querySelector('#app').innerHTML=`
<header><a class="brand" href="/">anywear<span class="brand-dot"></span></a><span class="header-caption">你的衣橱，换一个看法。</span><span class="local-tag">◉ 本地试衣间</span></header>
<main><section class="wardrobe"><div class="eyebrow">THE EDIT / 01</div><h1>先心动，再试穿。</h1><p class="intro">选一件喜欢的，让镜头里的你换个造型。</p>
<div class="tabs" role="tablist" aria-label="商品分类"><button class="active" data-category="all" role="tab" aria-selected="true">全部</button><button data-category="tops" role="tab" aria-selected="false">上衣</button><button data-category="bottoms" role="tab" aria-selected="false">裤子</button><button data-category="shoes" role="tab" aria-selected="false">鞋子 <small>实验</small></button></div>
<div id="products" class="products"></div><div id="referenceViews" class="reference-views" hidden></div><p id="referenceNote" class="source" hidden></p>
<div class="upload-box"><div><strong>试试你自己的衣服</strong><p>白底、单件、无人物的商品照片效果更好</p></div><button id="upload" class="secondary">＋ 上传图片</button><input id="file" type="file" accept="image/jpeg,image/png,image/webp" hidden></div>
<div class="upload-options"><label>上传品类 <select id="uploadCategory"><option value="tops">上衣</option><option value="bottoms">裤子</option><option value="shoes">鞋子（实验性）</option><option value="outfit">整套穿搭（实验性）</option></select></label></div>
<p class="source">本机商品图仅用于本地试穿，未上传公共仓库；另有原创示意图。含模特的参考图可能影响还原，文字、标志及背面细节需要实测。</p>
<details><summary>接口与素材说明 ↗</summary><p>实时试衣使用 Decart 官方 JS SDK / WebRTC。视频和选中参考图会发送至 Decart，不保存在本地后端。上衣、裤子、鞋类均出现在官方提示词指南中；鞋类效果依赖脚部完整入镜，标为实验性。</p><p>每次替换一个品类，不保证保留之前选择的其他单品。本 Demo 不做尺码测量或合身度保证。</p><a href="https://docs.platform.decart.ai/models/realtime/vton-3.5-prompting" target="_blank" rel="noreferrer">查看官方品类与提示词指南</a></details>
</section>
<section class="fitting"><div class="fitting-heading"><div><div class="eyebrow">YOUR FITTING ROOM</div><h2>此刻，试穿一下。</h2></div><span id="apiStatus" class="status">检查配置中</span></div>
<div class="mirror"><video id="output" autoplay playsinline muted hidden></video><div id="empty" class="empty"><div class="mirror-mark">a.</div><h3>这里，留给新的你。</h3><p>开启摄像头，走进你的实时试衣间。</p><span class="outline-person">♧</span></div><div class="mirror-top"><span id="videoBadge">尚未开启</span><span>9:16</span></div><div id="loading" class="loading" hidden><span class="spinner"></span><span id="loadingText">连接中…</span></div><div id="previewWrap" class="preview" hidden><video id="preview" autoplay playsinline muted></video><span>原始摄像头</span></div><div class="mirror-bottom"><span id="mirrorHint">光线充足 · 正面站立 · 保持身体入镜</span></div></div>
<div class="selection-line"><span class="selection-dot"></span><div><small>当前选择</small><strong id="selectedName"></strong></div><span id="applyStatus">待开始</span></div>
<section class="prompt-panel"><label for="promptEditor">试衣提示词 · Prompt</label><p>默认提示词可直接修改。选商品或正反面只更新草稿，点击应用后才发送；编辑期间当前会话继续计费。</p><textarea id="promptEditor" rows="6" spellcheck="false"></textarea><div class="prompt-actions"><button id="resetPrompt" class="secondary">恢复默认</button><button id="applyPrompt" class="primary">应用并实时试衣</button></div><p id="promptState" role="status">草稿 · 尚未应用</p><p>每次发送一张参考图；正反面需分别选择并应用，不会自动融合。</p></section><div class="controls"><button id="start" class="primary">开启实时试衣 <span>↗</span></button><button id="stop" class="secondary" disabled>结束</button></div>
<div class="utility"><button id="previewOnly">仅预览摄像头</button><button id="checkApi">检查 API</button><span id="quality">标准模式</span></div>
<div id="message" class="message" role="status" aria-live="polite">请允许浏览器使用摄像头。点击实时试衣后，视频将发送至 Decart 并按账户规则计费；每次最多 5 分钟。</div>
<details class="help"><summary>摄像头打不开？</summary><p>建议使用 Chrome 打开 localhost。点击地址栏摄像头图标允许访问；在「系统设置 → 隐私与安全性 → 摄像头」中允许浏览器，关闭正在占用摄像头的会议软件，再重试。裤子和鞋子需要向后站，让腿和脚完整入镜。</p></details>
</section></main><footer><span>LOOK GOOD. FEEL LIKE YOU.</span><span>Powered by Decart Lucy VTON · Local demo</span></footer>`;
function message(text,error=false){$('message').textContent=text;$('message').classList.toggle('error',error);}
function loading(show,text=''){ $('loading').hidden=!show;if(text)$('loadingText').textContent=text; }
function renderProducts(){
 const list=products.filter(p=>category==='all'||p.category===category);
 $('products').replaceChildren(...list.map(p=>{
 const button=document.createElement('button');button.className=`product ${selected.id===p.id?'selected':''}`;button.setAttribute('aria-pressed',String(selected.id===p.id));
 const image=document.createElement('img');image.src=p.image;image.alt=p.name;image.loading='lazy';
 const art=document.createElement('div');art.className='product-art';art.append(image);
 const badge=document.createElement('span');badge.className='product-badge';badge.textContent=p.local?'本机商品图':p.category==='shoes'?'实验性':p.upload?'你的上传':'原创示意';art.append(badge);
 const tick=document.createElement('span');tick.className='tick';tick.textContent='✓';art.append(tick);
 const name=document.createElement('strong');name.textContent=p.name;
 const detail=document.createElement('span');detail.className='product-detail';detail.textContent=p.detail;
 button.append(art,name,detail);button.onclick=()=>select(p);return button;
 }));
 $('selectedName').textContent=selected.name;
 $('referenceViews').hidden=!(selected.views?.length>1);
 $('referenceViews').replaceChildren(...(selected.views||[]).map(view=>{
  const button=document.createElement('button');button.className='secondary';button.textContent=view.label;button.setAttribute('aria-pressed',String(selected.image===view.image));button.onclick=()=>{selected.image=view.image;selected.prompt=view.prompt;renderProducts();showPrompt();$('promptState').textContent='草稿 · 尚未应用';};return button;
 }));
 $('referenceNote').hidden=!selected.local&&selected.category!=='outfit';
 $('referenceNote').textContent=selected.views?.length>1?'正面与背面分别发送单张参考图。转身时可手动切换；这不是自动多视角重建，背面还原不保证。':selected.category==='outfit'?'整套穿搭实验：替换参考图中的衣服组合，需要全身入镜；人物外观与服装细节可能出现偏差。':'本机原始商品图；含模特图片尚未去人物。只替换所选品类，效果与图案细节需实测。';
 $('mirrorHint').textContent=selected.category==='shoes'?'鞋类实验 · 请让双脚完整入镜':selected.category==='outfit'?'整套实验 · 请让全身完整入镜':selected.category==='bottoms'?'请向后站 · 让腰部和双腿完整入镜':'光线充足 · 正面站立 · 保持上半身入镜';
}
function select(p){selected=p;renderProducts();showPrompt();$('promptState').textContent='草稿 · 尚未应用';if(!rt)$('applyStatus').textContent='待开始';}
async function imageBlob(p){if(p.blob)return p.blob;const r=await fetch(p.image);if(!r.ok)throw Error('商品参考图加载失败');return r.blob();}
async function applyLatest(){
 if(applying||!rt)return;applying=true;const connection=rt;const run=epoch;
 try{
  let version;
  do{version=selectionVersion;const item=requested;$('applyStatus').textContent='发送参考图…';
   const blob=await imageBlob(item);if(run!==epoch||rt!==connection)return;
   await connection.set({image:blob,prompt:item.prompt,enhance:false});
   if(run!==epoch||rt!==connection)return;
   if(version===selectionVersion){$('applyStatus').textContent='参考图已发送';message(`已向 Decart 发送「${item.name}」；请在 AI 视频中观察实际换装效果。${item.category==='shoes'?'鞋类为实验性，请保持双脚入镜。':''}`);}
  }while(version!==selectionVersion);
 }catch(e){if(run===epoch){$('applyStatus').textContent='切换失败';message(friendly(e),true);}}
 finally{applying=false;}
}
function friendly(e){
 if(e.name==='NotAllowedError')return '摄像头权限被拒绝。请在地址栏和 Mac 系统设置中允许摄像头，然后重试。';
 if(e.name==='NotFoundError')return '未发现摄像头，请连接摄像头后重试。';
 if(e.name==='NotReadableError')return '摄像头无法读取，可能被其他应用占用，请关闭会议或录制软件后重试。';
 // Keep SDK request URLs / credentials out of UI and logs.
 const code=String(e.code||'');
 if(/AUTH|TOKEN|UNAUTHORIZED/.test(code))return 'Decart 身份验证失败，请检查密钥、令牌和账户权限。';
 if(/QUOTA|LIMIT|CREDIT/.test(code))return 'Decart 额度或并发限制，请检查账户余额并结束其他会话。';
 if(/CONNECT|TIMEOUT|NETWORK/.test(code))return '实时连接失败或超时，请检查网络、防火墙和 Decart 服务状态后重试。';
 return e.safeMessage || `无法完成操作${code?'（'+code+'）':''}。请检查网络、账户额度和摄像头权限后重试。`;
}
async function openCamera(run){
 if(camera)return;
 if(!navigator.mediaDevices?.getUserMedia){const e=Error();e.safeMessage='当前浏览器不支持摄像头，请用 Chrome 打开 http://localhost:3000。';throw e;}
 const stream=await navigator.mediaDevices.getUserMedia({audio:false,video:{facingMode:'user',width:{ideal:1280},height:{ideal:720},frameRate:{ideal:25}}});
 if(run!==epoch){stream.getTracks().forEach(t=>t.stop());return;}
 camera=stream;const video=$('preview');video.srcObject=stream;await video.play();$('previewWrap').hidden=false;$('stop').disabled=false;
 for(const track of camera.getTracks())track.onended=()=>{if(camera){stop();message('摄像头已断开，请重新开启。',true);}};
}
function croppedStream(){
 const canvas=document.createElement('canvas');canvas.width=720;canvas.height=1280;const ctx=canvas.getContext('2d');const v=$('preview');
 let last=0;const fps=resolveFpsNumber(models.realtime(config.model).fps);
 function draw(now){if(now-last>=1000/fps&&v.videoWidth){last=now;const w=v.videoWidth,h=v.videoHeight,ratio=9/16;const sw=Math.min(w,h*ratio),sh=sw/ratio;ctx.save();ctx.translate(720,0);ctx.scale(-1,1);ctx.drawImage(v,(w-sw)/2,(h-sh)/2,sw,sh,0,0,720,1280);ctx.restore();}raf=requestAnimationFrame(draw);}
 draw(performance.now());return canvas.captureStream(fps);
}
async function token(){const res=await fetch('/api/token',{method:'POST',headers:{'X-Anywear-Request':'1'}});const data=await res.json();if(!res.ok){const e=Error();e.safeMessage=data.error;throw e;}return data.apiKey;}
async function start(){
 if(busy||rt)return;if(!submitDraft())return;$('promptState').textContent='已提交当前草稿';billing.begin(config?.model||'lucy-vton-latest');busy=true;const run=++epoch;$('start').disabled=true;$('stop').disabled=false;loading(true,'等待摄像头授权…');
 try{
  if(!config?.configured){const e=Error();e.safeMessage='后端未配置密钥，请填写 .env 并重启。';throw e;}
  await openCamera(run);if(run!==epoch)return;
  portrait=croppedStream();const p=requested,version=selectionVersion;const blob=await imageBlob(p);if(run!==epoch)return;
  loading(true,'正在连接 Decart 实时试衣…');$('videoBadge').textContent='连接中 · 尚无 AI 输出';
  const client=createDecartClient({apiKeyProvider:token});
  const connection=await client.realtime.connect(portrait,{
   model:models.realtime(config.model),mirror:false,
   initialState:{image:blob,prompt:{text:p.prompt,enhance:false}},
   onRemoteStream:stream=>{if(run===epoch)billing.state('generating');if(run!==epoch){stream.getTracks().forEach(t=>t.stop());return;}const video=$('output');video.srcObject=stream;video.hidden=false;$('empty').hidden=true;video.play().catch(()=>{});loading(true,'已收到远端流，等待第一帧…');
    const ready=()=>{if(run!==epoch)return;clearTimeout(frameTimer);loading(false);$('videoBadge').textContent='● AI 实时输出';};
    if(video.requestVideoFrameCallback)video.requestVideoFrameCallback(ready);else video.onloadeddata=ready;
    frameTimer=setTimeout(()=>{if(run===epoch){loading(false);message('已收到远端流，但尚未解码到画面。请检查网络，或结束后重试。',true);}},30000);
   },
   onConnectionChange:state=>{if(run!==epoch)return;billing.state(state);const labels={connecting:'连接中',connected:'已连接',generating:'生成中',reconnecting:'重连中',disconnected:'已断开'};$('apiStatus').textContent=`API · ${labels[state]||state}`;if(state==='reconnecting'){loading(true,'网络波动，正在重新连接…');$('output').hidden=true;$('videoBadge').textContent='重连中 · 暂停显示';}if(state==='disconnected'){$('output').hidden=true;$('videoBadge').textContent='已断开 · 暂无实时输出';loading(false);}if(state==='generating'||state==='connected'){$('output').hidden=!$('output').srcObject;loading(false);}},
   onConnectionQuality:report=>{if(run===epoch)$('quality').textContent='网络 · '+({good:'良好',fair:'一般',poor:'较差',critical:'不稳定'}[report.quality]||report.quality);},
   onQueuePosition:queue=>{if(run===epoch)loading(true,`等待服务空位 · 队列 ${queue.position}`);}
  });
  if(run!==epoch){connection.disconnect();return;}rt=connection;
  rt.on('error',e=>{if(run===epoch)message(friendly(e),true);});
  rt.on('generationTick',data=>{if(run===epoch)billing.report(data.seconds);});
  rt.on('generationEnded',data=>{if(run===epoch)billing.report(data.seconds);});
  rt.on('sessionEnded',()=>{if(run===epoch){stop();message('Decart 已结束本次会话。可以重新开启试衣。');}});
  $('applyStatus').textContent='参考图已发送';message(`已连接 ${config.model}。参考图已发送；请观察实际 AI 输出，选择单品或编辑提示词后，点击应用更新。`);
  if(version!==selectionVersion)await applyLatest();
  sessionTimer=setTimeout(()=>{if(run===epoch){stop();message(`已达到本次 ${config.maxSessionSeconds} 秒上限，会话已停止。`);}},config.maxSessionSeconds*1000);
 }catch(e){if(run===epoch){stop('失败待核对');message(friendly(e),true);}}
 finally{if(run===epoch){busy=false;$('start').disabled=!!rt;}}
}
function stop(result='已结束'){
 billing.end(result);
 ++epoch;clearTimeout(sessionTimer);clearTimeout(frameTimer);cancelAnimationFrame(raf);rt?.disconnect();rt=null;
 portrait?.getTracks().forEach(t=>t.stop());portrait=null;camera?.getTracks().forEach(t=>{t.onended=null;t.stop();});camera=null;
 $('output').srcObject=null;$('output').hidden=true;$('preview').srcObject=null;$('previewWrap').hidden=true;$('empty').hidden=false;
 busy=false;loading(false);$('start').disabled=false;$('stop').disabled=true;$('videoBadge').textContent='尚未开启';$('apiStatus').textContent=config?.configured?'密钥已配置':'密钥未配置';$('applyStatus').textContent='待开始';$('quality').textContent='标准模式';
}
$('promptEditor').oninput=()=>{promptDrafts.set(draftKey(),$('promptEditor').value);$('promptState').textContent='草稿 · 尚未应用';};
$('resetPrompt').onclick=()=>{promptDrafts.delete(draftKey());showPrompt();$('promptState').textContent='草稿 · 尚未应用';};
$('applyPrompt').onclick=async()=>{if(busy||applying){message('正在连接或发送，请稍后再应用。');return;}if(rt){if(!submitDraft())return;$('promptState').textContent='已提交当前草稿';await applyLatest();}else await start();};
$('start').onclick=start;$('stop').onclick=()=>{stop();message('会话已结束，摄像头已关闭。');};
$('previewOnly').onclick=async()=>{if(busy||rt)return;busy=true;const run=++epoch;$('start').disabled=true;$('stop').disabled=false;try{await openCamera(run);if(run!==epoch)return;loading(false);$('videoBadge').textContent='仅摄像头预览 · 无 AI';message('右下角是原始摄像头。尚未连接 Decart，不会进行换装。');}catch(e){if(run===epoch){stop();message(friendly(e),true);}}finally{if(run===epoch){busy=false;$('start').disabled=false;}}};
$('checkApi').onclick=async()=>{const b=$('checkApi');b.disabled=true;try{await token();$('apiStatus').textContent='API 令牌验证通过';message('Decart 已成功签发短期令牌。尚未打开视频生成会话；点击「开启实时试衣」验证画面。');}catch(e){$('apiStatus').textContent='API 验证失败';message(friendly(e),true);}finally{b.disabled=false;}};
for(const tab of document.querySelectorAll('[data-category]'))tab.onclick=()=>{category=tab.dataset.category;for(const t of document.querySelectorAll('[data-category]')){t.classList.toggle('active',t===tab);t.setAttribute('aria-selected',String(t===tab));}renderProducts();};
$('upload').onclick=()=>$('file').click();
$('file').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{
 if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>10*1024*1024){message('请上传 10MB 以内的 JPEG、PNG 或 WebP 商品图。',true);return;}
 const bitmap=await createImageBitmap(file);const min=Math.min(bitmap.width,bitmap.height);bitmap.close();
 const c=$('uploadCategory').value,url=URL.createObjectURL(file);objectURLs.push(url);
 const region={tops:'upper body garment',bottoms:'lower body garment',shoes:'footwear',outfit:'outfit'}[c];
 const item={id:crypto.randomUUID(),name:file.name.replace(/\.[^.]+$/,''),category:c,image:url,blob:file,upload:true,detail:'你的商品图 · 本次页面有效',prompt:`Substitute the ${region} with the item in the reference image, matching its visible color, shape and details.`};products.unshift(item);category='all';document.querySelector('[data-category="all"]').click();select(item);if(min<512)message('图片已上传，但小于 512px，建议使用更清晰的白底商品图。');
 }catch{message('无法读取图片，请选择有效的 JPEG、PNG 或 WebP。',true);}finally{e.target.value='';}};
window.addEventListener('pagehide',()=>{stop();objectURLs.forEach(URL.revokeObjectURL);});
renderProducts();
showPrompt();
mountBilling();
installI18n();
fetch('/api/status').then(r=>r.json()).then(data=>{config=data;$('apiStatus').textContent=data.configured?'密钥已配置':'密钥未配置';message(`请允许浏览器使用摄像头。开启实时试衣后，视频和商品图将发送至 Decart，并按账户规则计费；每次最多 ${Math.round(data.maxSessionSeconds/60)} 分钟。`);}).catch(()=>{message('本地后端无法连接，请重启服务。',true);});

fetch('/api/local-products').then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{if(data.products?.length){products.unshift(...data.products);if(!camera&&!busy&&!rt&&selected.id==='tee')select(products.find(p=>p.id==='local-pride')||products[0]);else renderProducts();}}).catch(()=>{message('本机商品列表未加载，请确认本地服务已更新。',true);});
