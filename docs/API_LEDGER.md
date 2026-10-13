# Decart API 使用与计费台账

本 Demo 通过 Decart Lucy VTON 把实时摄像头流与单件商品参考图组合成远端生成视频。当前实现使用官方 JavaScript SDK 和短期令牌，永久密钥只保存在本机后端。接口签发已通过，真实人物试穿效果仍待本机摄像头验收。

最近更新：2026-10-13，Asia/Singapore。价格以美元计，本台账不是账户余额或账单。所有永久密钥和短期令牌均不记入本文。

## API 接入记录

| 项目 | 当前记录 | 来源或证据 |
| --- | --- | --- |
| 供应商 | Decart AI | [官方平台](https://platform.decart.ai) |
| 密钥入口 | 登录账户，在 API Keys 页面创建密钥 | [认证指南](https://docs.platform.decart.ai/getting-started/authentication) |
| 已配置 | 用户提供的密钥已写入本机 .env，权限 600；值不入仓库 | 本机配置检查 |
| SDK | @decartai/sdk 0.2.7，锁定版本 | package.json 与 pnpm-lock.yaml |
| 默认模型 | lucy-vton-latest | 后端 .env 配置 |
| 当前别名 | 2026-10-13官方映射为 lucy-vton-3.6；运行配置仍为latest，未固定版本；历史底层版本不能反推 | [模型页](https://docs.platform.decart.ai/getting-started/models) |
| 通信 | 浏览器官方 SDK 建立 WebRTC / LiveKit 连接，直接上传实时视频 | [官方 SDK 示例](https://github.com/DecartAI/sdk) |
| 本地入口 | http://localhost:3000，仅绑定 127.0.0.1 | server.mjs |
| 后端作用 | 签发短期令牌和提供静态前端，不代理或存储摄像头视频 | server.mjs |
| 实际 API 检查 | 2026-10-08 浏览器点击检查 API，显示 API 令牌验证通过 | 实际调用 client.tokens.create |
| 未验收部分 | 人物上衣/裤子/鞋类/眼镜效果、完整连续操作和实际账户扣费 | 需要用户站到镜头前验证 |

## 使用流程与接口

后端用环境变量 DECART_API_KEY 创建官方 client。浏览器先免费预览摄像头；用户点击开始后，由 apiKeyProvider 向本地 POST /api/token 获取凭据；每次重新拨号也会获取新令牌。随后调用 realtime.connect，并用 onRemoteStream 接收 AI 输出。首次及后续参考图都在连接后显式 await set({image, prompt, enhance})，等待回执再更新已发送；不再把connect返回当初始参考图确认，无需主动重建会话。[实时接入说明](https://docs.platform.decart.ai/models/realtime/virtual-try-on)

| 本地接口 | 方法 | 用途 | 返回信息 |
| --- | --- | --- | --- |
| /api/status | GET | 读取配置状态 | configured、model、maxSessionSeconds，不返回密钥 |
| /api/token | POST | 签发短期凭据 | apiKey、expiresAt，Cache-Control 为 no-store |

token 请求必须包含 X-Anywear-Request: 1。后端拒绝其他 Host 与跨来源请求；两次签发最少间隔 2 秒。此限制用于本机 Demo，不能替代公网认证。

## 认证与会话限制

官方令牌默认有效 60 秒，可配置 1 至 3600 秒；allowedModels 与 allowedOrigins 可限制模型和浏览器来源。expiresIn 限制开启连接的时间，maxSessionDuration 限制已经开启的会话。仅令牌到期不会终止已运行的视频生成。[Client Tokens](https://docs.platform.decart.ai/getting-started/client-tokens)

本 Demo 设定：60 秒 TTL、仅默认 VTON 模型、仅本机两个来源、最多 30 秒会话。后端把时长限制写入令牌，前端从点击开始即设置30秒停止计时器，包含连接等待；换衣/重连不重置。页面刷新和结束按钮释放摄像头并断开会话。同浏览器同来源使用Web Locks限制一个活动试衣实例；没有跨浏览器总消费额度限制。

## VTON 功能台账

| 能力 | 官方支持 | 本 Demo 状态 | 验证条件与限制 |
| --- | --- | --- | --- |
| 实时虚拟试衣 | 支持 | 官方 SDK 接入完成 | Chrome已出现真实远端首帧，服装效果待验收 |
| 上衣 | 官方指南列出 | 四件真实上衣、五张原图，可上传 | 正面、上半身清晰入镜 |
| 裤子与下装 | 官方指南列出 | 两件真实下装、两张原图，可上传 | 腰部与腿部完整入镜 |
| 鞋子 | 官方指南明确列出 footwear | 一张本机原图，实验性标记 | 双脚完整入镜；本机效果尚未验证 |
| 配件 | 官方指南概述及帽子/包/项链示例支持 | 新增配件分类、上传与黑框绿片太阳镜原图 | 本眼镜贴合/转头稳定性未验收，实验性；不新增专用API |
| 参考图与文字提示词 | 支持 | 已实现 | 预置详细提示词，上传采用品类提示词 |
| 动态切换参考图 | 支持 set / setImage | 已实现，点击应用发送草稿快照 | 发送成功不等于画面还原成功 |
| 提示词增强 | enhance | 预置与上传均关闭 | 不是额外视觉识别服务 |
| 套装 | 指南列出 outfit | 未实现多参考图合成 | 单件切换不保证保留此前衣服 |
| 图片格式 | JPEG / PNG / WebP | 已限制类型和 10MB 上传大小 | 10MB 是本 Demo 自定限制 |
| 画幅 | 官方支持竖屏与横屏 | 默认完整源画幅，可选720×1280中央裁切与手动旋转 | 预览与实际输入一致；运行中锁定取景 |
| 网络质量 | SDK 提供质量回调 | 页面显示等级 | 不是实际端到端毫秒延迟 |
| 视频文件批处理 | VTON queue API | 未接入 | 与实时试衣是不同计费入口 |
| 尺码测量、合身度 | 本项目不作保证 | 未实现 | 生成视觉不能替代服装量体 |

依据：[VTON 功能和格式](https://docs.platform.decart.ai/models/realtime/virtual-try-on)、[品类和提示词](https://docs.platform.decart.ai/models/realtime/vton-3.5-prompting)、[SDK 回调](https://github.com/DecartAI/sdk)。鞋子不是官方不支持，而是此 Demo 尚未实测，所以保留实验性标签。

## 计费方式与价格

Decart 官方使用按量计费；实时接口按活跃生成秒数计费，视频批处理按生成视频秒数计费，图片按生成次数计费。官方说明无订阅和最低消费，新账户有试用额度，但具体额度和用户余额需在账户内确认。[官方价格](https://docs.platform.decart.ai/getting-started/pricing)

| 模型或模式 | 720p 官方价格 | 用途 | Demo 选择 |
| --- | --- | --- | --- |
| VTON 3.5 / 3.6 实时标准 | $0.02 / 生成秒 | 实时试衣 | 默认标准 |
| VTON 3.5 / 3.6 / latest fast | $0.04 / 生成秒 | 2026-10-13官方已列3.6支持 | 关闭 |
| VTON 3.5 / 3.6 批处理 | $0.04 / 生成秒 | 已录制视频换装 | 未接入 |
| Lucy 2.5 实时 | $0.02 / 生成秒 | 通用实时视频编辑 | 未接入 |
| Lucy Restyle 2 实时 | $0.01 / 生成秒 | 风格化 | 未接入 |
| Lucy Image 2 720p | $0.02 / 次 | 图片编辑 | 未接入 |

预算推算：标准 VTON 连续生成 30 秒约 $0.60，60 秒约 $1.20，300 秒约 $6.00；fast 同时长为两倍。该估算假设整段时间均活跃生成，实际费用以平台记录为准。点击检查 API 只签发凭据，本次没有开启生成会话；尚未检查实际账单。

## 接入注意事项

set 会整体替换模型状态，遗漏字段会被清除，因此每次切换同时传 image、prompt、enhance。参考图优先单件、白底、无人物、至少 512px。prompt 指定 upper body garment、lower body garment、footwear 或 outfit；只描述图中可见细节，不凭空增加商标。[官方 VTON 指南](https://docs.platform.decart.ai/models/realtime/vton-3.5-prompting)

不设置 fast 参数就是标准模式；不能把字符串 standard 作为 speed 传入。模型别名和价格会变，后续升级需重新核对来源，记录更新时间。视频和图片由浏览器发送到 Decart；供应商留存与政策需要按其实际服务条款判断，本 Demo 没有声称供应商零留存。

## 变更记录

| 日期 | 变化 | 实测状态 |
| --- | --- | --- |
| 2026-10-08 | 建立 API 台账，核对 latest 与 3.6 差异、鞋类、token TTL 和计费 | 官方文档已核对 |
| 2026-10-08 | 以用户提供密钥签发限制模型和本机来源的短期令牌 | 已通过 |

## 试衣计费统计补充

2026-10-08 增加同页统计。每次实时试衣从点击开始记到结束，摄像头预览和 API 检查不计入次数。SDK generationTick / generationEnded 的 seconds 回报优先作为生成时长估算；未收到回报时采用观察到的 generating / 远端流时间。重连等待从本地观察时长中排除。生成秒数乘以本次固定单价，保留单次、累计和已结束可估算会话的平均值。

未确认发生生成的失败记录费用显示未知，不伪造为免费。SDK 回报不是正式结算；生成结束后最后时长可能尚未到达，突然关闭页面和网络异常可能造成低估，须在平台核对。

公开文档索引和 SDK 未提供可确认的金额余额查询方法；GET /v1/realtime/quota 仅返回并发 limit、active、remaining，不能映射为美元。[Quota 说明](https://docs.platform.decart.ai/api-reference/get-realtime-quota)

因此真实账户余额默认为未读取。用户可在平台确认金额后手动校准，剩余估算等于快照金额减去校准后的本地估算。其他应用、标签页、浏览器、充值和平台调整不在扣减范围；刷新保留此浏览器 localStorage。没有调用未公开的控制台接口，也没有上传用户账目到 GitHub。

## 2026-10-08 输入方式与背面核查

官方实时 VTON 文档列出单个 `image`（JPEG/PNG/WebP），没有图片数组或 front_image/back_image 多视角参数。允许文字、参考图或两者组合，故 Prompt 并非 API 必填；本 Demo 为可控试验要求编辑框非空，并总是发送当前单图+Prompt，enhance=false。旧版初始连接用initialState，现由DEC-020替代为连接后显式await set；SDK仍支持initialState，但连接完成不代表它已确认；set 整体替换状态，不能把先发正面、再发背面视作积累两张图。来源：[实时 VTON](https://docs.platform.decart.ai/models/realtime/virtual-try-on)。

公开请求无 gender 参数或性别识别结果；品类通过提示词指定目标区域。outfit 可以描述整套服饰，但不代表复制模特身份，也不保证先前单品保留。含模特参考建议先提取服装，当前未实现该步骤。来源：[提示词指南](https://docs.platform.decart.ai/models/realtime/vton-3.5-prompting)。

前后面通过手动选择不同参考图+相应描述测试，模型没有公开的背面精确保真承诺。缺失视角、印花/商标、背部开口和接缝都需真人实测。该 Demo 未实现姿态识别、自动切图、多视图融合或 3D 服装重建；不能宣称背面准确。

## 2026-10-08 · SDK兼容性纠正与真实连接调试

前版安装0.2.3未实现apiKeyProvider，令牌签发通过不能证明SDK能构造实时客户端。BUG-006已定位并升级官方npm0.2.7，新增provider拨号前调用回归。上游官方npm latest核对0.2.7；旧版本事实保留在Git/问题记录。实时使用connect/set，绝不使用Batch替代。

本节为10月8日历史核查，现行别名及快速模式以10月13日顶部表为准；旧判断已被替代。历史会话底层版本仍未知，未启用快速模式。

后端令牌200已验证。用户报告开始等待约25秒后断开，BUG-007待脱敏日志确认，无真实AI画面验证成功。本机日志字段白名单排除认证/Prompt/媒体/原始URL。

## 2026-10-08 连接兼容性调试

官方[网络与浏览器要求](https://docs.platform.decart.ai/integrations/network-requirements)推荐当前Chrome/Edge/Firefox/Safari，实际依赖运行时WebRTC能力。项目新增免费本地SDP视频offer检查，检查通过仍不代表远端ICE/SDP协商通过。实测令牌签发成功但约37秒后报RTCPeerConnection unsupported；内置浏览器/Chrome本地SDP均通过，远端Chrome待实测。记录于BUG-007，不能误记为密钥无效。用户iPhone竖持时轨道1280×720，新增输入旋转与完整画幅，模型与预览取景同步；镜像依旧仅显示。

## 配件能力复核 · 2026-10-08 · REQ-010 / DEC-013

[官方Lucy VTON提示词指南](https://docs.platform.decart.ai/models/realtime/vton-3.5-prompting)明确参考图可用于garments和accessories，建议附加配件使用Add动作并说明佩戴位置与可见细节，示例包含帽、包、项链。本次查阅未找到眼镜专属支持保证、精准贴合承诺或多图配件融合接口。新增太阳镜仍走官方实时VTON单image+prompt，不是图片叠加；一般配件支持已查证，本图眼镜视觉效果待TEST-013验证。默认Prompt保留原有衣服是请求而非质量保证，切换单图后此前生成服装也不保证保留。

## 本机录像能力 · 2026-10-13 · REQ-011 / DEC-014

新增对比录像使用[浏览器MediaRecorder](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder)与[Canvas captureStream](https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/captureStream)，不是Decart新增API。只合成本页现有原画与远端流，编码与下载在浏览器，不上传后端、不另开生成连接。试衣会话仍按已有规则运行，停止录像不停止生成；录像模块不参与费用计算。

isTypeSupported检测容器支持，优先video/mp4，后退video/webm;codecs=vp8/video/webm；最终扩展名从实际recorder.mimeType决定。停止后等待最终dataavailable和stop事件，再生成下载Blob。浏览器或硬件失败显示可操作错误，不报告已保存。此次内置浏览器测试实际得到video/mp4;codecs=avc1，下载文件ftyp/isom有效；不把该结果当所有浏览器兼容保证，Chrome真人录制仍需用户验收。

## SDK主动结束与错误分类复核 · 2026-10-13

本机安装SDK0.2.7的realtime/types.d.ts定义SessionEnded.reason：insufficient_credits、session_limit、moderation_violation、policy_violation及未知字符串；session_limit注释为并发会话上限。stream-session.js在finishTerminally先改变disconnected状态，再发sessionEnded。以已安装官方SDK为本次接入依据，参见[官方SDK仓库](https://github.com/DecartAI/sdk)。网页现按固定原因显示脱敏提示并记录固定code，不能记录未知原始原因或账户金额。

2026-10-10历史会话仅已有reason=credit分类和WEBRTC_SERVER_ERROR，没有采集当时sessionEnded.reason，不能区分实际额度不足/并发限制，更不能据此判定10月13日账户状态。当前配置检查HTTP200仍只表示后端已配置，未查询余额或创建生成会话。BUG-015修复具体原因被泛化覆盖，未声称供应商问题或账户额度已解决。

## 球衣输入与JPEG · 2026-10-13

新增James.jpg仍为上衣单image+prompt，不新增模型或收费服务。人物与球衣同图，默认仅请求转移球衣；参考图内人物/纹身/配饰/篮球不属于请求目标，模型是否遵循仍需实测。号码/文字不承诺精确还原。预置图片接口补齐.jpg/.jpeg的image/jpeg，扩展名匹配忽略大小写；前端上传本已支持JPEG，这次修复的是本机预置图响应声明。

## policy枚举语义纠正 · 2026-10-13 · BUG-017

安装SDK0.2.7的terminalReasonFromClose/terminalReasonFromError将WebSocket1008归policy_violation，不能等同于明确内容审核moderation_violation。旧Demo合并翻译与记录有误，现拆分诊断码及显示：通用关闭保留前置可信API提示，具体审核单独说明。15:09真实会话有先行credit类错误，无AI首帧，旧聚合码无法还原原始枚举；准确账户状态需用户查平台，不能据此要求换图或断言余额归零。没有发现也没有调用余额查询接口，没有自动重试收费生成。

## 模型与credits复核 · 2026-10-13 · DEV-012 / TEST-022

本机GET /api/status返回lucy-vton-latest；官方模型表和VTON页今日均明确解析为lucy-vton-3.6。这是文档映射，不是历次会话服务端版本回报。没有改模型或开启fast。平台Billing通用套餐10,000 credits / $100，对应100 credits / $1、1,000 credits / $10；标准VTON约2 credits/生成秒，30秒约60 credits/$0.60。来源：[模型表](https://docs.platform.decart.ai/getting-started/models)、[价格](https://docs.platform.decart.ai/getting-started/pricing)、[登录后Billing套餐](https://platform.decart.ai/billing)。个人余额/消费/账单截图不入仓库。用户已自行核对账户，恢复服务可用性后再复测。

再次检查[完整公开文档索引](https://docs.platform.decart.ai/llms.txt)，没有公开的账户余额、费用流水或账单查询接口；只能说未找到公开支持，不能断言平台内部不存在。GET /v1/realtime/quota只返回并发limit/active/remaining，不能转成钱。SDK generationTick/generationEnded提供时长，不提供最终扣款；Demo继续估算，正式金额通过平台Usage/Billing核对。

## 30秒限制与凭据更新 · 2026-10-13 · DEV-013

用户授权替换本机后端密钥，仅更新Git忽略的.env且权限600；不记录密钥、前缀、指纹或账户身份。服务重启后签发HTTP200，短期令牌载荷中maxSessionDuration=30已确认，未启动生成。令牌TTL仍60秒，它不代表允许生成60秒。[官方约束说明](https://docs.platform.decart.ai/getting-started/client-tokens)中maxSessionDuration为每个WebSocket会话限制；前端独立总截止时间包含连接和重连，不能因重新签发续时。浏览器后台计时或网络清理有延迟可能，供应商结算待核对，不宣称精确费用封顶。新key不证明余额/生成权限；API费用查询仍未公开支持。

## 默认自动录像 · 2026-10-13 · REQ-014 / DEC-019

用户授权AI输出就绪后自动开启本机原画＋AI录制，无新增Decart调用或费用入口。免费预览不录；同次会话只自动尝试一次，停止/重连不重复启动。手动停止录像不停止试衣；30秒试衣截止会收尾录像。视频仍由用户点击下载落盘，永久密钥/摄影/录制内容不入日志和Git。合成源的30秒测试不是远端模型效果证据。

## 参考图回执、内层错误与黑屏 · 2026-10-13 · DEV-016 / DEC-020

已安装SDK0.2.7的StreamSession.runOneConnect启动watchInitialStateAck后继续媒体连接，不等待初始参考图回执；watchInitialStateAck可能稍后发error。classifyWebrtcError将未知错误包装为WEBRTC_SIGNALING_ERROR/Signaling error，并把原Error放cause。原Demo只读外层且connect即标记发送，存在信息丢失和确认时序错误。现在按[官方JS示例](https://docs.platform.decart.ai/models/realtime/virtual-try-on)先connect、再显式await set完整单图+Prompt，发送失败不改已发送，不重开连接。

错误cause最多读取4层，防循环；仅保留固定分类和词表，长度240内，不保存原文/像素/URL/Prompt/金额。未知/信令错误不再推断为摄像头故障。远端解码首帧与可见非全黑帧分开记录；32×18本机像素只算黑屏分类，立即丢弃，日志只有状态，不上传或存图。可见内容与请求回执是自动录像门槛，但两者都不证明服装效果。当前远端黑屏根因尚未通过新真实请求定位，不能把检测功能说成修复了模型。

## 猴脸T恤参考 · 2026-10-13 · REQ-015 / DEV-017

monkey.jpg为700×700 JPEG，保持原始摄影，本机JPEG响应与浏览器解码通过。参考依旧单image+Prompt；明确只换印有猴脸的T恤，不请求换人脸。新增商品不代表API支持动物变身或图片处理成功，也不证明此前黑屏已解决；需新显式set回执和用户视觉验证。

## 显式set真实回执 · 2026-10-13 · TEST-031

新流程一次用户现场请求中首次set上衣回执1336ms成功，随后SDK进入generating并取得非黑visible分类；本轮无信令错误，20.112秒自动片段就绪。此证据说明当前连接后显式发送路径本轮可用，不能回溯17:01原始cause，也不能证明参考图视觉还原或下载质量。没有为了验证代用户调用生成。

## 真人视觉反馈 · 2026-10-13 · TEST-032

用户针对TEST-031本轮确认猴脸T恤换装正确、下载录像正常。显式单图+Prompt路径已有本轮视觉对应及回放证据，替代该轮尚待反馈状态；不反推此前黑屏的供应商根因，不声称模型全面保真、多图融合或所有品类通过。无新API调用、价格/模型配置改动或个人费用公开。
