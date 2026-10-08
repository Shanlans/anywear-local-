# Anywear · 本机实时虚拟试衣 Demo

[![Build and verify](https://github.com/Shanlans/anywear-local-/actions/workflows/check.yml/badge.svg)](https://github.com/Shanlans/anywear-local-/actions/workflows/check.yml)

Mac 本地单页试衣网页，使用 Decart Lucy VTON 官方实时 SDK / WebRTC。左侧用户真实商品与可编辑 Prompt，右侧大试衣画面。当前迭代0.2，功能分支 `feature/live-fitting-demo`；最新状态以本文件和关联台账为准。

## 当前状态（2026-10-08）

|能力|状态|
|---|---|
|五件真实商品、六张本机图、正反面单图切换|已实现；公共仓库不含摄影|
|iPhone设备选择、免费预览、准确取景、原画/AI查看|已实现，iPhone真人待验收|
|可编辑Prompt、原子set、草稿/已发送区分|已实现，模型遵循程度待实测|
|真正实时远端视频|SDK链路已实现，真人效果尚未通过|
|认证|后端令牌200；SDK0.2.3回调不兼容已定位，升级0.2.7及回归测试通过；真人连接待重试|
|停止、超时、停帧、单标签会话保护|已实现，现场断连/连续操作待验收|
|中文/英文、费用与操作记录、手动余额|已实现，金额为估算而非正式账单|
|构建与自动检查|11项本机测试通过；GitHub CI按提交运行|

**页面可运行、令牌签发成功不代表真实服装还原已经通过。** 至少一件上衣和下装需各30秒运动观察，由用户确认效果，三次开始结束及三次切换不刷新。

## Mac 启动

安装 Node.js 24或更新LTS，首次运行 `npm install`（会构建），复制 `.env.example` 为 `.env`，填写 `DECART_API_KEY`。然后 `npm start` 或双击 `start.command`，保持终端运行，打开 <http://localhost:3000/>。已有本机项目已配置密钥，不要把密钥提交。

改源码后 `npm run build` 并刷新；改后端或.env后重启。开发检查 `npm test`。

本机项目路径：`/Users/admin/.codex/.chatgpt-projects/g-p-6ac736282ae08191bef605c199088656/anywear-local`。

## 安装真实商品图

六张用户提供图片放入 `src/local-products/`，原始文件名见 `src/local-catalog.js`。黑色上衣正反面归为同一件商品。目录已排除Git；照片来自用户，商业/再分发许可未核验。公共克隆没有摄影时展示安装说明，也可在网页上传自己的JPEG/PNG/WebP（10MB以内）。没有示意服装或虚构回退。上传与Prompt草稿仅当前页面有效。

## 现场使用

1. 固定并锁定 iPhone，后置摄像头朝向你。允许浏览器和Mac摄像头权限，点击免费预览；选iPhone设备，检查光线及站位。
2. 默认完整取景保留摄像头画幅；可选竖屏中央裁切，裁切会放大人物。预览就是模型输入范围。镜像只影响显示，输入默认不翻转。
3. 选择商品和默认Prompt，点击开始实时试衣。视频和参考图将发送Decart并计费；主窗标签区分免费预览与远端AI。
4. 修改Prompt或选择商品/正反面后，点击应用修改。同一会话发送单图+Prompt，不重新连接。右侧已发送只表示请求已提交，视觉效果看AI画面。
5. 可查看原画或小窗进行对比；看原画/编辑期间会话仍计费。结束会关闭本机视频和连接；连接中取消可能等待SDK返回后完成清理，异常记录须平台核对。
6. 测裤子须腰腿入镜，鞋须双脚入镜。正反面需手动分别应用，没有自动转身识别或多视角融合，背面/文字/鞋类效果不保证。

解锁iPhone、来电、暂停或系统视频特效可能影响取景。遇停帧，结束后锁定iPhone重新预览。建议关闭系统虚化/追踪等效果；一浏览器同来源只允许一个摄像头实例。

## 费用与限制

标准VTON按$0.02/活跃生成秒估算，约$1.20/分钟；非官方账单。SDK时长优先，未确认生成或中断标待核对。点击开始到结束记一条会话，每次应用另记操作和耗时。免费预览、检查API不计试衣次数。默认会话上限5分钟。

详细历史与平均花费折叠展示；实际金额余额接口未查到，手动余额减本页估算，不含其他浏览器/应用/平台变动。费用记录在浏览器本机，不上传Git。

只支持单参考图，不保证切换品类保留此前衣服；含模特照片尚未自动提取服装。套装上传为实验入口，没有多件组合、自动姿态识别、3D服装或尺码推荐。

## 文档与版本

- [实施计划](docs/IMPLEMENTATION_PLAN.md)、[六类台账索引](docs/LEDGER_INDEX.md)
- [产品设计与需求决策](docs/PRODUCT_DESIGN.md)、[API台账](docs/API_LEDGER.md)
- [开发/发布](docs/DEVELOPMENT_LEDGER.md)、[测试](docs/TEST_LEDGER.md)、[问题](docs/ISSUE_LEDGER.md)、[变更](CHANGELOG.md)

每阶段独立提交，调试问题关联需求/测试/修复版本；禁止把密钥、令牌、人像影像和个人费用记录提交公共仓库。实时功能使用 `realtime.connect`，预录视频Batch不是本Demo路径。

官方资料：[实时VTON](https://docs.platform.decart.ai/models/realtime/virtual-try-on)、[提示词](https://docs.platform.decart.ai/models/realtime/vton-3.5-prompting)、[价格](https://docs.platform.decart.ai/getting-started/pricing)、[iPhone连续互通相机](https://support.apple.com/en-us/102546)。

## 本机诊断日志

后台日志在 `.local/diagnostics.jsonl`，每个文件约1MiB后轮换，保留当前及两份历史。记录摄像头输入参数、连接阶段/状态、SDK错误码与分类、令牌成功状态、首帧与停止，不记录Prompt/图片/视频/密钥/令牌/原始SDK消息或URL；整个目录排除Git。前端经本机白名单接口写入，调试时读取此文件，不能从网页静态路径访问。

当前调试：约25秒无AI首帧后断开，BUG-007待日志定位；取景人物过大已定位为中央裁切，BUG-008调整默认完整取景。所有问题详见问题台账。
