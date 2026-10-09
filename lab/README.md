# Anywear 消费者实验室 / Consumer Lab v0.1

这是共享门店中的合成消费者实验，不是真实市场数据，也不是真人换装效果。游戏入口 `/lab/` 与原摄像头试衣页 `/` 独立。普通镜子和实体试衣间在两店均保留，实验干预仅为是否提供 Anywear 外观预览。

## 安装与启动

要求 macOS/Linux、Node 24、pnpm 11.25、Python **3.12**。Concordia 固定 **2.4.0**，Python 完整依赖见 `requirements.lock`。服务管理使用 POSIX 进程与文件锁；Windows 原生暂不支持，可在 WSL 中运行。首次安装：

```sh
pnpm install --frozen-lockfile
python3.12 -m venv .venv
.venv/bin/python -m pip install -r lab/requirements.lock
pnpm lab:doctor
pnpm lab:start
```

打开 <http://127.0.0.1:3001/lab/>。API 为 `127.0.0.1:8001`，仅本机绑定。默认创建 **DEMO**，规则机器人仅验证软件；真实模式绝不使用规则机器人补失败结果。

```sh
pnpm lab:status
pnpm lab:stop
pnpm lab:restart
pnpm lab:test
pnpm build
pnpm test
```

管理器拒绝覆盖占用端口。网页关闭后 supervisor、API、worker 继续运行；本机睡眠不会补跑购物时间。恢复后从当前逻辑时刻继续。关机/注销导致进程退出，重新启动会校验持久状态；不确定的模型调用会暂停等待明确重提交。持续在线依赖本机供电、登录和网络，不提供云端 24/7 保证。

macOS 登录后启动：`pnpm lab:install-login`；移除：`pnpm lab:uninstall-login`。安装器写 `~/Library/LaunchAgents/local.anywear.consumer-lab.plist`，保留本机路径和可执行文件路径，不写凭据。安装前先构建。安装登录启动后，`pnpm lab:stop` 会先卸载当前 launchd 任务，避免 KeepAlive 自动重启；`pnpm lab:start` / `lab:restart` 重新加载，登录启动配置保留。卸载命令会停止服务并移除配置。

## 暂停、停止与退出网页

游戏顶部提供 **暂停 / 继续 / 停止本场**。暂停保留进度，可继续。停止不再发起新模型调用；已经发出的调用允许结束（或超时），随后冻结世界、释放队列和库存预约，未完成消费者记为 `CENSORED: operator_stop`，不计作主动离店。记录、用量和不确定调用均保留；不能继续已停止的实验，可新建或创建探索分支。已自然完成的场次不能再停止。关闭网页继续运行；`lab:stop` 则停止整个本机服务，重启后按持久状态恢复。

Pause resumes. **Stop this run** is final for that run: no new calls, active calls settle first, pending shoppers are censored, and records remain. Stopping does not undo consumed allowance. Closing the browser keeps experiments running.

## 真实模型：无需 API key，消耗账号额度

安装并登录官方 Codex CLI，`codex login status` 应显示有效 ChatGPT 登录。模型固定显式 `gpt-6.1-sol`。使用现有 Codex 登录，不读取、导出或记录 auth 文件。可用 `ANYWEAR_CODEX` 指定 CLI 的绝对路径。CLI 升级或适配器/组件改变后必须重新实测隔离：

```sh
pnpm lab:doctor --probe
```

该命令真实调用一次模型，消耗账号额度。通过后网页才开放真实模式。每次消费者决策新建 ephemeral CLI 会话、空工作目录，只传该消费者在该条件中的 persona、可见观察及私有记忆。Concordia EntityAgent、观察组件、AssociativeMemoryBank、行动组件实际参与；记忆使用固定 SHA256 字符三元组嵌入，不额外请求嵌入 API。

CLI 提示词本身不是安全边界。每次调用的本机随机 nonce 网关限制最多一次转发，重写上游请求：一个消费者输入、固定系统指令、`tools=[]`、`tool_choice=none`、`store=false`，移除 CLI 注入的项目文档、其他上下文、历史引用和工具。上游地址固定为 ChatGPT Codex 官方端点；认证头仅在内存转发。输出只保存行动、简短双语自述理由、可观测 usage 和固定错误码；不保存 reasoning 内容或完整 CLI 事件流。该适配器依赖 CLI/登录端点兼容性，门禁失败时暂停，不切换成假数据。

`temperature`、`top_p`、`top_k`、模型 seed 和硬 token 上限不受当前适配器支持；界面/能力清单明确标注。世界 seed 固定环境，不保证重新请求模型得到相同回答。真实调用有额度成本；**金额未知**，token 可观测部分与缺失数分别报告。CLI 尝试预算并非底层请求/计费的精确上限。默认并发 2、超时180秒；失败和未知也计尝试预算。10人配对上限200次，100人配对上限2000次；增加预算必须在面板明确操作。超时/崩溃未知不会自动重投，重提交可能再次计费。

## 实验与操作

先运行10人配对验收，再100人正式基准。两店各100个独立消费者上下文，200个逻辑实例；不是一个对话扮演所有人。两条件共用 persona、外生商品真值、进入时间，私有记忆分离。消费者在共享世界中争用资源；库存、支付、时钟均由唯一引擎提交，模型只提议动作。

冻结假设和指标见 [协议](../docs/GAME_PLAN.md)，可直接使用 `lab/configs/acceptance-10.json`、`baseline-100.json`。此前逛20分钟和试3件失败为给定前史，轨迹从此刻的观察窗口开始。

- 暂停等待正在执行的响应安全保存；继续、单事件、决策批次用于观察。**决策批次**提交同一时刻全部已冻结决策，防止逐个点击改变同刻消费者的信息。单事件在零事件的 stale agenda 上也可能不增加可见序号。
- 人物点击/下拉展示私有上下文、双语理由、记忆摘要、预算/时间和目标。观察者能看全局；消费者只看到自己的信息与公开资源/库存。
- 画面速度、缩放、跟随、路径热图只影响展示，不影响购物时钟。回放零模型调用，滑块会吸附至已提交的完整决策批次。
- 改价格、资源、库存、信号噪声或未来客流必须暂停后分支；父实验不变，子分支不继承父未来答案。人数、seed、开场占用变化需从头新建。中途分支/手工干预标为探索，不能当完整正式对照。已观测预览信号保持缓存，改变噪声仅影响尚未预览的商品。
- 成本/经营目标修改创建不可变分析版本，不调用模型。已有事件后修改目标标“事后分析”。原分析保留。
- Debug 提供决策断点、任务/错误、库存/支付/时间不变量、状态 hash、预算增加、失败重试和明确未知重提交；永久保留历史失败记录。未知处理后先继续才会再次调用。
- 敏感性3×3与至少10个seed的重复世界批次先生成预算计划，点击启动才调用。未运行/失败/不完整格保留。首次自动验收不启动这些额外批次。

报告用事件和支付记录计算，简短模型理由不构成因果证明。购买率分母为全部计划人数，离店率包括主动离店与时间耗尽；截尾、未进入、未完成另列。等待分布使用已关闭的排队片段（服务/放弃，含零等待），开放队列单列。正式完整要求全部消费者自然终止、无未提交任务、无截尾；恢复后成功的历史错误尝试仍保留；任何历史unknown的轨迹即使恢复完整也不具正式比较资格。DEMO同样不参与正式经营判定或配对区间。首个100人实验是**一对共享世界**，仅描述差异；不能把消费者当100次独立重复。>=10对完整从头世界才按整场配对差值 bootstrap，仍是模拟证据。

经营测算假设 COGS SGD60、设备 SGD3000、固定月费 SGD200、每月同类受挫消费者1000人、预览可变费暂为0且未校准。未含退货、税、人工、获客及模型金额；ROI 仅是假设情景，不是真实回报验证。

## 数据、报告与 API

默认数据目录 `.lab-data/`，可用 `ANYWEAR_LAB_DATA` 指定绝对路径。SQLite WAL 保存事件、私有记忆、任务、attempt、checkpoint、分析版本、问题与心跳。完整轨迹、数据库与所有账号资料留本机。备份时先安全暂停/停止服务，再备份整个数据目录及对应源码版本。不要只复制运行中的 `.sqlite3` 而遗漏 WAL。

API 同源，通过 Node 转发。GET `/api/lab/session` 返回当前页面写入 nonce；POST 带 `X-Lab-Nonce`，其他 Origin/Host 拒绝。主要端点：`runs`、`runs/{id}/state`、`agents/{world}/{id}`、`control`、`fork`、`analyses`、`replay`、`report`、`export`、`stream`、`debug`、`health`、`batches`。SSE `Last-Event-ID`/`after` 支持补流。事件包含schema/seq/world/agent/virtual_time，SSE另加run/branch；报告包含源码/协议/config/persona/外生hash与模型依据。

回放会校验引擎/数据类型源码hash；旧版本轨迹须恢复报告记录的源码版本，不会用新逻辑冒充精确回放。

报告导出包含 JSON、CSV、Markdown、独立HTML/内嵌图表及ZIP。CSV 防公式注入，HTML 转义模型文字。页面报告无需联网。源码下载：

```sh
pnpm lab:package --run RUN_ID
```

白名单只打包 Git 已追踪源码、协议、锁文件、测试夹具；产物 `.lab-data/deliverables/anywear-lab-v0.1-source.zip`。指定 run 的真实报告另成ZIP，不混入源码包。数据库、auth、.env、照片、原始模型流不打包。

## 版本管理与验收证据

游戏分支 `feature/experiment-game` 基于重新核验的远端 `feature/live-fitting-demo`，SHA `6affbf9d78560c7ccde921c0d55db1ba7e686d5e`。PR 暂以该功能分支为基底，依赖其既有代码；不自动合并 main。原摄像头真人服装效果和连续操作验收仍独立待现场确认。代码、协议、锁文件与明确的测试夹具入 Git；真实运行报告完整数据只留本机，公共台账只含脱敏摘要和依据。CI 不运行收费模型。

实际阶段状态见 [开发台账](../docs/DEVELOPMENT_LEDGER.md) 和本机 `deliverables/` 报告。未执行的实验没有结果；代码通过不等于真实模型实验通过，更不等于市场验证。

## Persona、记忆和价格的当前简化

每人7轴：预算、时间、风格、排队耐心、隐私、技术信任、接受阈值；均为假设分布独立分层抽样，不是经验证的人格或新加坡人口分布。没有预设年龄/职业。所有6个SKU使用同一单件价格（默认SGD120），不是平均价；低预算消费者可能买不起全部商品。

每条件保存私有亲历事件及稳定ID；提示载入最近12条加最多4条关联检索记忆（本地字符trigram embedding，并非经过验证的心理记忆模型）。右侧可查看已知商品信号和完整结构化记忆，模型没有全局观察者权限。

操作者停止时排队记录为censored，已观察等待单列，排除完整等待分位数及主动放弃数。画面监控显示本机FPS，以及最近最多100个已观察到的新状态版本的提交至接收延迟p95；首次历史快照和重复心跳不入样本。该观察采样不是每个事件的完整延迟分布，离开页面时不采样。

Persona uses seven assumed independent shopping axes, not a validated personality model. All six SKUs have the same per-item price. Memories are private to consumer and condition. Operator-stop queue observations are censored and excluded from completed waiting-time percentiles.

## 运行核验工具

`.venv/bin/python scripts/verify_lab_run.py RUN_ID` 对已完成的真实模型场次检查全部自然终止、独立会话、单消费者输入、零工具、模型与Concordia组件、库存/支付/资源、SQLite、checkpoint和零调用回放，导出验证JSON、行为漏斗CSV及报告ZIP/HTML。它拒绝不完整、历史失败/未知、探索分支和未提交源码启动的场次，不调用模型。使用运行报告记录的引擎版本；旧引擎hash不符会拒绝回放。

右侧个人目标区分“运行中／已达成（模拟）／未达成／数据不足”；技术截尾属于数据不足。完整记忆展开后保留滚动位置，避免后台心跳打断阅读。

## CLI 传输截止时间修复（发布副本）

输入与输出管道均使用非阻塞读写；CLI只输出半行或暂不读stdin时仍按截止时间取消。等待中的单条输出缓冲上限1MiB，超限作为未知调用暂停，不保存原始内容。超时另有有界进程清理时间；未知调用可能已消耗额度，不能自动重提交。四项离线假CLI回归覆盖半行阻塞、较大stdin、UTF-8分片/末行无换行和缓冲上限。它们不调用上游模型。适配器源码变更使隔离fingerprint失效，部署该版本前必须重新执行真实探针。

fd30c26修复候选于2026-10-09 12:26:42 UTC通过一次真实探针：actual gpt-6.1-sol、requests=1、input=1、tools=0、tool_event=false，结构化行动有效，token278+46，金额未知。探针仅验证适配器，不计入消费者实验或100人完成数。本机证据为candidate-fd30c26-isolation-probe.json。当前服务保持旧冻结版本，候选未部署；新安装或CLI/适配器指纹变化仍须在自己的本机重新执行探针，下载的源码不携带已通过门禁文件。
