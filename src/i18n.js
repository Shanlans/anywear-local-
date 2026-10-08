// Canonical UI copy stays in Chinese. Runtime translations never rebuild video elements.
const en={
'试衣花费，一目了然。':'Try-on spending, at a glance.',
'按标准 VTON $0.02/生成秒估算，约 $1.20/分钟；仅供预算，非官方账单。':'Estimated at standard VTON $0.02 per generation second, about $1.20 per minute. A budget estimate, not an official bill.',
'本次估算':'Current estimate','累计估算':'Total estimate','平均每次':'Average per session','已结束次数':'Completed sessions','剩余金额估算':'Estimated remaining balance',
'仅含可估算的已结束会话':'Completed sessions with a known estimate only','从开始点击至结束记录':'Records each start-to-end attempt',
'真实账户余额未读取':'Actual account balance not retrieved','手动余额扣减本地估算':'Manual balance minus local estimates',
'平台当前余额 USD':'Current platform balance in USD','校准余额':'Set balance snapshot','清除校准':'Clear snapshot','查看官方账户 ↗':'Open official account ↗',
'公开 API 未查到金额余额查询接口。手动余额只扣减校准后本页面估算，不含其他应用、其他浏览器或平台调整；校准时请先结束会话。':'No public monetary-balance endpoint was found. The manual snapshot subtracts only estimates from this page after calibration, excluding other apps, browsers and platform adjustments. End the session before setting a snapshot.',
'开始时间':'Started at','点击到结束':'Start-to-end duration','估算生成时长':'Estimated generation time','估算花费':'Estimated cost','结果':'Result','统计依据':'Basis',
'开始一次实时试衣后，记录会出现在这里。':'Your live try-on sessions will appear here.',
'记录保存在此浏览器本机。预览与检查 API 不计入试衣次数；未确认生成的失败记录显示 —。SDK 时长仍不等于平台结算金额。页面异常中断需到平台核对。':'Records stay in this browser. Camera previews and API checks are excluded. Failed attempts without confirmed generation show —. SDK timing is not a settled bill. Verify interrupted sessions on the platform.',
'已结束':'Ended','失败待核对':'Failed · Verify charges','中断待核对':'Interrupted · Verify charges','进行中':'In progress','未确认生成':'Generation unconfirmed','SDK 回报时长估算':'SDK-reported duration estimate','本地生成时长估算':'Locally observed duration estimate',
'无法保存记录，请检查浏览器本地存储。':'Cannot save records. Check browser storage.',

'商品分类':'Product categories','手动填写':'Enter manually',
'你的衣橱，换一个看法。':'See your wardrobe differently.', '◉ 本地试衣间':'◉ Local fitting room',
'先心动，再试穿。':'Love it. Try it on.', '选一件喜欢的，让镜头里的你换个造型。':'Pick a favorite. See a new look on your live camera.',
'全部':'All','上衣':'Tops','裤子':'Bottoms','鞋子':'Shoes','实验':'Experimental',
'雾白圆领 T 恤':'Cloud white tee','鼠尾草绿卫衣':'Sage green hoodie','蓝色牛仔衬衫':'Blue denim shirt','经典直筒牛仔裤':'Straight-leg jeans','沙色宽腿长裤':'Sand wide-leg trousers','极简白色运动鞋':'Minimal white sneakers',
'原创示意':'Original illustration','实验性':'Experimental','你的上传':'Your upload',
'棉感 · 宽松短袖':'Cotton look · Relaxed fit','连帽 · 袋鼠口袋':'Hooded · Kangaroo pocket','双口袋 · 纽扣闭合':'Two pockets · Buttoned','中腰 · 直筒长裤':'Mid rise · Straight leg','宽腿 · 简洁剪裁':'Wide leg · Clean cut','低帮 · 鞋类实验':'Low top · Experimental',
'试试你自己的衣服':'Try your own garment','白底、单件、无人物的商品照片效果更好':'Use a clean product photo on a plain background.', '＋ 上传图片':'+ Upload image','上传品类':'Upload category','鞋子（实验性）':'Shoes (experimental)',
'预置图为本 Demo 原创无品牌示意图，非真实商品摄影；可用于演示。图案与面料还原请用你有权使用的商品照片验证。':'Preset images are original unbranded illustrations, suitable for demos. Test fabric and pattern fidelity with product photos you have permission to use.',
'接口与素材说明 ↗':'API & image details ↗',
'实时试衣使用 Decart 官方 JS SDK / WebRTC。视频和选中参考图会发送至 Decart，不保存在本地后端。上衣、裤子、鞋类均出现在官方提示词指南中；鞋类效果依赖脚部完整入镜，标为实验性。':'Real-time try-on uses the official Decart JS SDK / WebRTC. Video and the selected reference image are sent to Decart, not stored on this backend. The official guide covers tops, bottoms and shoes; shoes remain experimental here and need your feet fully in frame.',
'每次替换一个品类，不保证保留之前选择的其他单品。本 Demo 不做尺码测量或合身度保证。':'Each request replaces one category. Previously selected items may not persist. This demo does not measure size or guarantee fit.',
'查看官方品类与提示词指南':'Official categories & prompting guide', '此刻，试穿一下。':'Your next look, live.',
'检查配置中':'Checking configuration','密钥已配置':'Key configured','密钥未配置':'Key not configured','尚未开启':'Not started','这里，留给新的你。':'Room for a new you.',
'开启摄像头，走进你的实时试衣间。':'Turn on your camera to enter your fitting room.',
'光线充足 · 正面站立 · 保持身体入镜':'Good lighting · Face forward · Stay in frame',
'光线充足 · 正面站立 · 保持上半身入镜':'Good lighting · Keep your upper body in frame',
'鞋类实验 · 请让双脚完整入镜':'Experimental shoes · Keep both feet in frame',
'请向后站 · 让腰部和双腿完整入镜':'Step back · Keep your waist and legs in frame',
'原始摄像头':'Original camera','当前选择':'Selected item','待开始':'Ready when you are','开启实时试衣':'Start live try-on','结束':'End','仅预览摄像头':'Camera preview only','检查 API':'Check API','标准模式':'Standard mode',
'摄像头打不开？':'Camera trouble?',
'建议使用 Chrome 打开 localhost。点击地址栏摄像头图标允许访问；在「系统设置 → 隐私与安全性 → 摄像头」中允许浏览器，关闭正在占用摄像头的会议软件，再重试。裤子和鞋子需要向后站，让腿和脚完整入镜。':'Open localhost in Chrome. Allow camera access in the address bar and macOS System Settings → Privacy & Security → Camera. Close other apps using your camera, then retry. Step back for trousers and shoes so your legs and feet are fully visible.',
'发送参考图…':'Sending reference…','参考图已发送':'Reference sent','切换失败':'Switch failed',
'摄像头权限被拒绝。请在地址栏和 Mac 系统设置中允许摄像头，然后重试。':'Camera permission denied. Allow access in your browser and macOS System Settings, then retry.',
'未发现摄像头，请连接摄像头后重试。':'No camera found. Connect a camera and retry.',
'摄像头无法读取，可能被其他应用占用，请关闭会议或录制软件后重试。':'Camera unavailable. Close meeting or recording apps that may be using it, then retry.',
'Decart 身份验证失败，请检查密钥、令牌和账户权限。':'Decart authentication failed. Check your key, token and account permissions.',
'Decart 额度或并发限制，请检查账户余额并结束其他会话。':'Decart credit or session limit reached. Check your balance and end other sessions.',
'实时连接失败或超时，请检查网络、防火墙和 Decart 服务状态后重试。':'Connection failed or timed out. Check your network, firewall and Decart status, then retry.',
'当前浏览器不支持摄像头，请用 Chrome 打开 http://localhost:3000。':'This browser does not support camera capture. Open http://localhost:3000 in Chrome.',
'摄像头已断开，请重新开启。':'Camera disconnected. Start again.',
'后端未配置密钥，请填写 .env 并重启。':'Backend key missing. Configure .env and restart.',
'等待摄像头授权…':'Waiting for camera permission…', '正在连接 Decart 实时试衣…':'Connecting to Decart live try-on…',
'连接中 · 尚无 AI 输出':'Connecting · No AI output yet','已收到远端流，等待第一帧…':'Remote stream received. Waiting for the first frame…','● AI 实时输出':'● Live AI output',
'已收到远端流，但尚未解码到画面。请检查网络，或结束后重试。':'A remote stream arrived but no frame has decoded. Check your network, or end and retry.',
'API · 连接中':'API · Connecting','API · 已连接':'API · Connected','API · 生成中':'API · Generating','API · 重连中':'API · Reconnecting','API · 已断开':'API · Disconnected',
'网络波动，正在重新连接…':'Network interrupted. Reconnecting…','重连中 · 暂停显示':'Reconnecting · Display paused','已断开 · 暂无实时输出':'Disconnected · No live output',
'网络 · 良好':'Network · Good','网络 · 一般':'Network · Fair','网络 · 较差':'Network · Poor','网络 · 不稳定':'Network · Critical',
'Decart 已结束本次会话。可以重新开启试衣。':'Decart ended this session. You can start a new one.',
'会话已结束，摄像头已关闭。':'Session ended. Camera turned off.', '仅摄像头预览 · 无 AI':'Camera preview only · No AI',
'右下角是原始摄像头。尚未连接 Decart，不会进行换装。':'The small window shows your original camera. Decart is not connected; no try-on is running.',
'API 令牌验证通过':'API token verified','API 验证失败':'API check failed',
'Decart 已成功签发短期令牌。尚未打开视频生成会话；点击「开启实时试衣」验证画面。':'Decart successfully issued a short-lived token. No video generation session is open. Press Start live try-on to test the output.',
'请上传 10MB 以内的 JPEG、PNG 或 WebP 商品图。':'Upload a JPEG, PNG or WebP product image smaller than 10 MB.',
'你的商品图 · 本次页面有效':'Your image · This page session only',
'图片已上传，但小于 512px，建议使用更清晰的白底商品图。':'Image uploaded, but it is smaller than 512 px. Use a sharper product photo on a plain background.',
'无法读取图片，请选择有效的 JPEG、PNG 或 WebP。':'Cannot read this image. Choose a valid JPEG, PNG or WebP.',
'本地后端无法连接，请重启服务。':'Cannot reach the local backend. Restart the service.',
'请在 .env 中配置 DECART_API_KEY，然后重启服务。':'Configure DECART_API_KEY in .env and restart the service.',
'Decart 拒绝密钥或权限，请检查密钥与账户权限。':'Decart rejected the key or permissions. Check your key and account.',
'Decart 无法签发会话令牌，请检查网络、密钥和账户额度。':'Decart could not issue a session token. Check your network, key and account credits.',
'请求太快，请稍后再试。':'Too many requests. Please try again shortly.',
};
export const locales={'zh-CN':{name:'中文',dictionary:{}},en:{name:'English',dictionary:en}};
let locale=localStorage.getItem('anywear-language')||'zh-CN';if(!locales[locale])locale='zh-CN';
const memory=new WeakMap();
function translate(s){if(locale==='zh-CN')return s;const trim=s.trim();const dictionary=locales[locale].dictionary;const direct=dictionary[trim];if(direct)return s.replace(trim,direct);
 const substitutions=[
 [/^请允许浏览器使用摄像头。开启实时试衣后，视频和商品图将发送至 Decart，并按账户规则计费；每次最多 (\d+) 分钟。$/,(_,n)=>`Allow camera access. Starting live try-on sends video and product images to Decart and may incur usage charges. Each session lasts up to ${n} minutes.`],
 [/^已向 Decart 发送「(.+)」；请在 AI 视频中观察实际换装效果。(.*)$/,(_,n,extra)=>`Sent “${en[n]||n}” to Decart. Check the AI video for the actual result.${extra?' Shoes are experimental; keep both feet in frame.':''}`],
 [/^已连接 (.+)。参考图已发送；请观察实际 AI 输出，点击左侧可切换单品。$/,(_,m)=>`Connected to ${m}. Reference sent. Check the actual AI output; select an item on the left to switch.`],
 [/^已达到本次 (\d+) 秒上限，会话已停止。$/,(_,n)=>`The ${n}-second limit was reached. Session stopped.`],
 [/^未确认记录 (\d+)$/,(_,n)=>`Unconfirmed records: ${n}`],
 [/^等待服务空位 · 队列 (\d+)$/,(_,n)=>`Waiting for a server · Queue position ${n}`],
 [/^无法完成操作(.*)。请检查网络、账户额度和摄像头权限后重试。$/,(_,code)=>`Unable to complete this action${code}. Check your network, account credits and camera permissions, then retry.`],
 ];for(const [pattern,replace]of substitutions)if(pattern.test(trim))return trim.replace(pattern,replace);return s;}
function textNode(node){const entry=memory.get(node);let source=entry&&node.data===entry.rendered?entry.source:node.data;const rendered=translate(source);memory.set(node,{source,rendered});if(node.data!==rendered)node.data=rendered;}
function walk(root){if(root.nodeType===Node.TEXT_NODE){textNode(root);return;}const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);while(walker.nextNode())textNode(walker.currentNode);
 for(const el of root.querySelectorAll?.('[alt],[aria-label],[placeholder]')||[]){for(const attr of ['alt','aria-label','placeholder']){if(!el.hasAttribute(attr))continue;const key=`data-i18n-${attr}`;const source=el.getAttribute(key)||el.getAttribute(attr);el.setAttribute(key,source);el.setAttribute(attr,translate(source));}}
}
export function installI18n(){const box=document.createElement('select');box.id='language';box.setAttribute('aria-label','Language / 语言');for(const [code,value]of Object.entries(locales)){const option=document.createElement('option');option.value=code;option.textContent=value.name;box.append(option);}box.value=locale;document.querySelector('header').append(box);
 const apply=()=>{document.documentElement.lang=locale;document.title=locale==='en'?'Anywear · Local fitting room':'Anywear · 本地试衣间';walk(document.getElementById('app'));};
 box.onchange=()=>{locale=box.value;localStorage.setItem('anywear-language',locale);apply();};
 const observer=new MutationObserver(records=>{for(const r of records){if(r.type==='characterData')textNode(r.target);else for(const node of r.addedNodes)walk(node);}});
 observer.observe(document.getElementById('app'),{subtree:true,childList:true,characterData:true});apply();
}
