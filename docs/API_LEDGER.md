# Decart API 使用与计费台账

本 Demo 通过 Decart Lucy VTON 把实时摄像头流与单件商品参考图组合成远端生成视频。当前实现使用官方 JavaScript SDK 和短期令牌，永久密钥只保存在本机后端。接口签发已通过，真实人物试穿效果仍待本机摄像头验收。

最近更新：2026-10-08，Asia/Singapore。价格以美元计，本台账不是账户余额或账单。所有永久密钥和短期令牌均不记入本文。

## API 接入记录

| 项目 | 当前记录 | 来源或证据 |
| --- | --- | --- |
| 供应商 | Decart AI | [官方平台](https://platform.decart.ai) |
| 密钥入口 | 登录账户，在 API Keys 页面创建密钥 | [认证指南](https://docs.platform.decart.ai/getting-started/authentication) |
| 已配置 | 用户提供的密钥已写入本机 .env，权限 600；值不入仓库 | 本机配置检查 |
| SDK | @decartai/sdk 0.2.7，锁定版本 | package.json 与 pnpm-lock.yaml |
| 默认模型 | lucy-vton-latest | 后端 .env 配置 |
| 当前别名 | 官方模型页列为 lucy-vton-3.5；3.6 虽已可用，但不要把 latest 自动描述成 3.6 | [模型页](https://docs.platform.decart.ai/getting-started/models) |
| 通信 | 浏览器官方 SDK 建立 WebRTC / LiveKit 连接，直接上传实时视频 | [官方 SDK 示例](https://github.com/DecartAI/sdk) |
| 本地入口 | http://localhost:3000，仅绑定 127.0.0.1 | server.mjs |
| 后端作用 | 签发短期令牌和提供静态前端，不代理或存储摄像头视频 | server.mjs |
| 实际 API 检查 | 2026-10-08 浏览器点击检查 API，显示 API 令牌验证通过 | 实际调用 client.tokens.create |
| 未验收部分 | 摄像头授权、远端第一帧、人物上衣/裤子/鞋类效果、真实延迟和账户扣费 | 需要用户站到镜头前验证 |

## 使用流程与接口

后端用环境变量 DECART_API_KEY 创建官方 client。浏览器点击开始后先申请摄像头，再由 apiKeyProvider 向本地 POST /api/token 获取凭据；每次重新拨号也会获取新令牌。随后调用 realtime.connect，并用 onRemoteStream 接收 AI 输出。初始参考图和提示词放在 initialState；之后用 set({image, prompt, enhance}) 替换单品，无需主动重建会话。[实时接入说明](https://docs.platform.decart.ai/models/realtime/virtual-try-on)

| 本地接口 | 方法 | 用途 | 返回信息 |
| --- | --- | --- | --- |
| /api/status | GET | 读取配置状态 | configured、model、maxSessionSeconds，不返回密钥 |
| /api/token | POST | 签发短期凭据 | apiKey、expiresAt，Cache-Control 为 no-store |

token 请求必须包含 X-Anywear-Request: 1。后端拒绝其他 Host 与跨来源请求；两次签发最少间隔 2 秒。此限制用于本机 Demo，不能替代公网认证。

## 认证与会话限制

官方令牌默认有效 60 秒，可配置 1 至 3600 秒；allowedModels 与 allowedOrigins 可限制模型和浏览器来源。expiresIn 限制开启连接的时间，maxSessionDuration 限制已经开启的会话。仅令牌到期不会终止已运行的视频生成。[Client Tokens](https://docs.platform.decart.ai/getting-started/client-tokens)

本 Demo 设定：60 秒 TTL、仅默认 VTON 模型、仅本机两个来源、最多 300 秒会话。后端把时长限制写入令牌，前端也设置停止计时器。页面刷新和结束按钮释放摄像头并断开会话。多标签页会有多个独立会话；本 Demo 没有跨标签页总消费额度限制。

## VTON 功能台账

| 能力 | 官方支持 | 本 Demo 状态 | 验证条件与限制 |
| --- | --- | --- | --- |
| 实时虚拟试衣 | 支持 | 官方 SDK 接入完成 | 真实远端流尚待摄像头验收 |
| 上衣 | 官方指南列出 | 3 张预置示意图，可上传 | 正面、上半身清晰入镜 |
| 裤子与下装 | 官方指南列出 | 2 张预置示意图，可上传 | 腰部与腿部完整入镜 |
| 鞋子 | 官方指南明确列出 footwear | 1 张预置图，实验性标记 | 双脚完整入镜；本机效果尚未验证 |
| 帽子、项链等配饰 | 官方提示词指南列出 | 未增加商品分类 | 后续功能，不纳入当前验收 |
| 参考图与文字提示词 | 支持 | 已实现 | 预置详细提示词，上传采用品类提示词 |
| 动态切换参考图 | 支持 set / setImage | 已实现，点击应用发送草稿快照 | 发送成功不等于画面还原成功 |
| 提示词增强 | enhance | 上传启用，预置关闭 | 不是额外视觉识别服务 |
| 套装 | 指南列出 outfit | 未实现多参考图合成 | 单件切换不保证保留此前衣服 |
| 图片格式 | JPEG / PNG / WebP | 已限制类型和 10MB 上传大小 | 10MB 是本 Demo 自定限制 |
| 画幅 | 官方支持竖屏与横屏 | 720×1280 竖屏输入 | 摄像头中心裁切，两侧画面会丢失 |
| 网络质量 | SDK 提供质量回调 | 页面显示等级 | 不是实际端到端毫秒延迟 |
| 视频文件批处理 | VTON queue API | 未接入 | 与实时试衣是不同计费入口 |
| 尺码测量、合身度 | 本项目不作保证 | 未实现 | 生成视觉不能替代服装量体 |

依据：[VTON 功能和格式](https://docs.platform.decart.ai/models/realtime/virtual-try-on)、[品类和提示词](https://docs.platform.decart.ai/models/realtime/vton-3.5-prompting)、[SDK 回调](https://github.com/DecartAI/sdk)。鞋子不是官方不支持，而是此 Demo 尚未实测，所以保留实验性标签。

## 计费方式与价格

Decart 官方使用按量计费；实时接口按活跃生成秒数计费，视频批处理按生成视频秒数计费，图片按生成次数计费。官方说明无订阅和最低消费，新账户有试用额度，但具体额度和用户余额需在账户内确认。[官方价格](https://docs.platform.decart.ai/getting-started/pricing)

| 模型或模式 | 720p 官方价格 | 用途 | Demo 选择 |
| --- | --- | --- | --- |
| VTON 3.5 / 3.6 实时标准 | $0.02 / 生成秒 | 实时试衣 | 默认标准 |
| VTON 3.5 / latest fast | $0.04 / 生成秒 | 更低延迟档位 | 关闭 |
| VTON 3.6 fast | 不支持 | 无该档位 | 不使用 |
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

官方实时 VTON 文档列出单个 `image`（JPEG/PNG/WebP），没有图片数组或 front_image/back_image 多视角参数。允许文字、参考图或两者组合，故 Prompt 并非 API 必填；本 Demo 为可控试验要求编辑框非空，并总是发送当前单图+Prompt，enhance=false。初始连接用 initialState，已连接用 set；set 整体替换状态，不能把先发正面、再发背面视作积累两张图。来源：[实时 VTON](https://docs.platform.decart.ai/models/realtime/virtual-try-on)。

公开请求无 gender 参数或性别识别结果；品类通过提示词指定目标区域。outfit 可以描述整套服饰，但不代表复制模特身份，也不保证先前单品保留。含模特参考建议先提取服装，当前未实现该步骤。来源：[提示词指南](https://docs.platform.decart.ai/models/realtime/vton-3.5-prompting)。

前后面通过手动选择不同参考图+相应描述测试，模型没有公开的背面精确保真承诺。缺失视角、印花/商标、背部开口和接缝都需真人实测。该 Demo 未实现姿态识别、自动切图、多视图融合或 3D 服装重建；不能宣称背面准确。

## 2026-10-08 · SDK兼容性纠正与真实连接调试

前版安装0.2.3未实现apiKeyProvider，令牌签发通过不能证明SDK能构造实时客户端。BUG-006已定位并升级官方npm0.2.7，新增provider拨号前调用回归。上游官方npm latest核对0.2.7；旧版本事实保留在Git/问题记录。实时使用connect/set，绝不使用Batch替代。

官方价格重新核查：标准VTON3.5/3.6均$0.02/活跃生成秒；3.5快速$0.04，3.6无快速。来源https://docs.platform.decart.ai/getting-started/pricing 。当前latest底层具体版本以供应商为准，记录为未知；没有启用快速模式。

后端令牌200已验证。用户报告开始等待约25秒后断开，BUG-007待脱敏日志确认，无真实AI画面验证成功。本机日志字段白名单排除认证/Prompt/媒体/原始URL。
