# Anywear 网页消费者实验室 v0.1

状态：实施中；代码完成、真实模型实验、真实市场效果分开记录。

## 协议

100 位 persona 在共享门店中互动，两个世界共用冻结 persona、商品潜在值、到达计划与外生随机表；记忆严格分离。条件为未提供 Anywear / 提供 Anywear，均保留普通镜子和实体试衣间。基准 SGD120，已逛20分钟、试3件不满意为给定前史。每30秒进入观察窗口，非完整营业日。

Persona 各轴独立分层均匀抽样：预算SGD50–500、剩余时间5–30分钟、隐私/信任/偏好0–1、接受阈值0.6–0.85。仅为假设，无人口代表性。六个剩余SKU每件价格相同、各20件；4试衣间180秒，收银30秒，Anywear45秒，浏览60秒、网格移动1秒/格。每人最多买1件。fit/穿着外观独立Uniform(0,1)；实体试穿揭示两者，虚拟预览仅外观加Uniform(-0.2,0.2)并clip，同persona-SKU重复使用同一信号。浏览只见商品元数据。不得向模型暴露潜在fit、另一世界或其他消费者私有记忆。

唯一引擎推进共同虚拟时间，冻结同刻观察后提交决策；模型墙钟延迟不计购物时间。库存满足initial=available+reserved+sold。支付提交才算购买。资源争用属于环境结果。有效行动安全上限64，CLI尝试预算10人200/100人2000、并发2、180秒超时。预算耗尽暂停；未知调用不自动重投，失败和未知均计预算。截尾不是离店。正式完整run必须所有计划persona自然终止且无unknown/error/censored。

整场门店为统计单位，单个100人run只报告描述差异。至少10对完整、真实Codex、从头且无任何历史unknown的世界后做整场配对bootstrap区间。DEMO和探索分支不具正式经营比较资格。敏感性价格30/120/300×四试衣间在t=0外生占用至0/15/30分钟，真实等待另记。首次自动实施仅10人验收＋100人基准；敏感性由网页预算预检后启动。

## 架构与安全

Phaser3/TypeScript /lab/，Node3001反代FastAPI8001；SQLite WAL事件/记忆/任务/快照；独立worker调用Concordia2.4.0自定义实体与CodexCLI适配器。使用现有Codex登录gpt-6.1-sol，无API key但消耗账号额度，金额未知；不将一次CLI视作一次底层计费请求。工具/插件/应用/外部记忆禁用与真实探针为M2门禁。采样参数不支持时明确报错。仅白名单持久化最终行动/简短中英理由/usage/安全错误，不保存reasoning或完整stdout/stderr。

稳定memory/event ID去重，组件从持久记录重建并校验schema/hash/READY。任务queued→leased→spawned→responded→committed，fencing/expected hash拒绝迟到结果；timeout/crash unknown暂停，支付幂等。每50逻辑事件及安全暂停/分支checkpoint。分支只在安全barrier建立，不继承未来答案。回放使用保存决策零调用。成本/经营目标仅新analysis版本，行为阈值仍属科学参数；事后目标标post-hoc。

## 经营、输出与验收

经营假设COGS60、capex3000、固定月费200、每月同类受挫消费者1000、预览可变费暂按0且未校准；未含退货/税/人工等。月增量现金贡献、回本、12月ROI只为情景测算。目标：增量贡献>0、离店不增加、达标购买不下降；单轮满足不等于稳健性/真实市场验证。

实时双店/人物详情/KPI/时间轴，pause/step/replay/fork；心跳、预算、模型/磁盘/任务告警，断点、不变量、问题台账；JSON/CSV/Markdown/独立HTML/ZIP白名单导出。动态文案中英完整，模型理由双语且仅为自述。

M0协议/依赖/隔离 → M1明确DEMO世界网页 → M2真实10人配对 → M3关闭网页10分钟与故障恢复 → M4真实100人、报告、CI、PR。Git基于远端feature/live-fitting-demo SHA 6affbf9d78560c7ccde921c0d55db1ba7e686d5e，游戏分支feature/experiment-game；PR暂堆叠、不合并main。既有摄像头真人验收保持独立。原sources只读，旧文字实验不补成游戏轨迹。

独立方案复审已关闭方案层面问题；真实隔离、provider可用性与恢复门禁尚待执行证据。无门禁通过证据不标真实实验完成。
