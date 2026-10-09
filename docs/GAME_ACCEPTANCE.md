# 消费者实验室 v0.1 完成审计

2026-10-09。**尚未完成 M4，不能标记整个目标完成。** 本文件跟踪用户批准方案；冻结科学协议仍见 GAME_PLAN.md。

|要求|可核验证据|当前结论|
|---|---|---|
|Concordia 2.4.0、Python3.12、Phaser、Vite/pnpm及锁文件|lab/requirements.lock、pnpm-lock.yaml、Concordia实际组件metadata、CI|已验证|
|独立persona、每消费者每条件私有记忆、每决策新会话|lab/agents.py、model.py；10人36唯一session/20逻辑上下文完整验证JSON|旧适配器真实通过；新传输实现须重跑探针|
|强制单消费者上下文且无工具/跨消费者访问|RequestGuard重写input/tools/历史；真实探针及每次调用metadata；gateway回归|旧指纹通过；新指纹待实际探针|
|配对共享世界、相同初始条件、给定20分钟/3失败前史|engine.py/common.py；privacy/frozen-frontier回归；config/persona/latent哈希|已验证|
|库存、队列、资源、走路、支付、预览噪声由引擎决定|engine.py；库存竞争/预约/等待估计/固定信号回归；完整10人不变量验证|已验证|
|独立后台、关闭网页仍运行|LaunchAgent及health实际PID；独立DEMO无客户端620.55秒、seq1169→4234、自然完成|已验证；未做整机断电/休眠实测|
|暂停、继续、停止、单事件/决策、分支与零调用回放|API与顶部控制；停止竞态/fence/未知/原子分支测试；浏览器停止、双语与回放|已验证；当前100人场人工暂停须恢复选择|
|两店游戏、人物详情、七项参数、已知商品、记忆/理由|Phaser实际200标记、浏览器消费者观察/热图/中英文|已验证|
|实时指标、分母/缺失、资源利用率、收入贡献、调用/预算/心跳|reports.py、main.ts、health；完整/部分报告及截尾回归|已验证|
|监控/debug、问题/严重度/复现/修复/回归依据|worker/API健康；issues及BUG-015～019、TEST-015～019；真实未知调用自动暂停|已验证；CLI截止修复部署门禁待执行|
|超时/恢复/迟到拒绝、稳定记忆、库存资金时间不变量|DEMO worker SIGKILL后fence2恢复并回放；32项pytest含管道截止、模型身份与未知/fence|离线与进程验证通过；新适配器真实探针待执行|
|报告JSON/CSV/Markdown/独立HTML图表、行为漏斗与迁移|8文件报告ZIP；verify_lab_run.py漏斗CSV；migration/reasons/goal/issues/provenance字段|真实10人完整产物已生成；100人仍部分|
|敏感性与多seed、统计单位与区间门禁|9格/10对批次预算计划，0格启动；API整场bootstrap>=10完整真实无历史unknown|实现与无调用计划验证通过；额外批次按方案未启动，无区间|
|成本/目标分析版本与事后标注|analyses API/回归；完整合成报告假设经济字段；部分报告ROI为空|已验证，不能宣称真实ROI|
|10人真实配对验收先于100人正式基准|run-c0c1de370f35，d7e7da1，20上下文/36会话，全部自然终止且库存/回放一致|通过；结果control购买1/10、Anywear0/10，仅模拟|
|100人完整真实基准|首场215尝试/2未知归档；新场run-9964389c8988，143/200自然终止、307尝试、0失败/未知，暂停|未完成；保留原2000总预算，尚余1478次|
|Github独立checkout、依赖PR、CI、台账|feature/experiment-game基于6affbf9；PR #2堆叠#1；此前公开9b38d0e CI通过|已完成基础发布；本阶段修复候选独立提交并随CI核验|
|源码ZIP、README、配置与真实报告下载|源码白名单ZIP、10人报告/精确源码、部分100人报告、persona CSV/JSON与验证依据留本机|已有可下载中间产物；最终100人报告/综合包待完成|
|保留原真人试衣验收与隐私边界|原anywear-local checkout未改；DB/轨迹/auth/照片/raw streams排除Git及源码ZIP|已验证；真人视觉验收仍独立待现场确认|

本机证据目录为 `anywear-game/.lab-data/deliverables/`，不提交完整轨迹。关键文件：`acceptance-10-verification.json`、`run-c0c1de370f35-verification.json`、`m3-process-recovery.json`、`m3-headless-and-load-verification.json`、`interrupted-100-verification.json`、`paused-100-verification.json`。报告来源、源码/配置/模型/提示与私有组件哈希可逐项核验。

发布候选在独立 `anywear-release` 副本准备，当前3001/8001实验服务仍使用冻结的b34f849内核和旧适配器。不会因为修复副本通过离线测试就将真实100人验收或新的隔离门禁记为成功。
