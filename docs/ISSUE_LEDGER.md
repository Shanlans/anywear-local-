# 问题台账

|编号|严重性|复现/影响|原因与证据|状态|关联/修复/复测|
|---|---|---|---|---|---|
|BUG-001|P0|真实换装尚未验收|前版仅Token/UI通过|待现场验证|REQ-001 / TEST-002/003|
|BUG-002|P1|旧350px镜子且示意图混入|旧展示页设计|待办|REQ-002/003|
|BUG-003|P0|连接期间结束可能晚到连接|SDK connect返回前无断开句柄|待办|REQ-006|
|BUG-004|P1|iPhone暂停不一定ended|需持续帧/track检测|待办|REQ-004/006|
|BUG-005|P1|SDK时长累计语义需现场核对|不能认定为正式金额结算|待现场验证|REQ-007|

新问题包括复现、范围、证据、原因(未知可注明)、修复提交和复测，不因代码改动自动关闭视觉问题。

## BUG-006 · P0 · SDK认证配置不兼容

用户反馈：检查API通过、开始报认证失败。后端token实测200；本机SDK0.2.3 create-client schema无apiKeyProvider，构造时INVALID_API_KEY。前版API接入方案采用新文档而未核对已安装版本，这是实现错误，非用户密钥无效。修复升级官方npm SDK0.2.7，新增无永久key构造及拨号前provider调用回归测试；真实生成仍需重试。关联REQ-001/006、TEST-006。

## BUG-007 · P0 · 首帧前约25秒断开

用户现场报告等待AI约25秒后显示连接断开，Token检查正常。原因未定，已启用本机连接日志，等待重试后读取定位；不能先认定为网络/密钥/模型。状态进行中，关联TEST-002/REQ-001/006。

## BUG-008 · P1 · 人物过大

用户反馈iPhone画面像zoom；代码未设置硬件zoom，默认横画幅中央裁切成竖屏再放大导致主体过大。默认改完整取景，保留竖屏裁切可选；设备自身系统特效仍需现场确认。状态待现场验证，关联REQ-004/DEC-008。

## BUG-009 · P1 · 英文/缺图/迟到发送状态

重建页面新中文文案未全部进字典，已补英文及动态状态；旧后端过滤缺失单面导致正背面缺图不可见，已保留可用标记；旧发送finally可能清除新会话发送状态，已限定会话版本。代码修复，浏览器和自动检查复测。

## BUG-010 · P2 · 竖持 iPhone 仍为横画幅

用户在 iPhone 竖持后仍看到横画幅。2026-10-08本机日志实测cameraWidth=1280、cameraHeight=720、fps=30，完整取景不裁切；网页未设置硬件zoom。连续互通相机输出的尺寸以浏览器实际轨道为准，不按手机姿态猜测。新增输入旋转0/90/270/180°，与预览/模型输入同步，生成期间锁定；人物直立时不旋转，横画幅可保留完整取景，竖屏裁切仍会丢失两侧。代码完成，人物朝向和取景待用户验证。关联REQ-004/DEC-010/TEST-002。

### BUG-007 2026-10-08 调试增量

现场日志：后端5次令牌签发200，SDK视频阶段每次警告，37542ms状态断开，未出现首帧。尚不能确认具体网络/媒体原因。发现前端在connect尚未返回时处理disconnected先取消会话，使catch中的具体错误无法显示；已改为连接中等错误返回后统一清理。补充固定英文词表错误特征及worker/网络分类，拒绝记录原始消息、URL与动态值，继续现场定位。没有把令牌200或错误提示改良记为真人通过。

### BUG-007 第三次现场定位

2026-10-08 08:09 UTC：再次36717ms失败。固定词表错误特征为`could not establish signal connection failed rtcpeerconnection unsupported`，说明服务端视频协商中的RTCPeerConnection操作失败；媒体warn为LiveKit room disconnected，并非worker构造警告。免费创建本地视频SDP offer检查在内置浏览器与外部Chrome均通过，所以不认定整个浏览器缺失WebRTC；需Chrome真实连接复测区分协商兼容性。已添加启动免费能力检查，能力不足时禁止开始，保留预览，不创建Decart会话。外部Chrome页已更新，用户控制摄像头与付费开始。BUG-007仍进行中，根因细节和修复效果未确认。

### BUG-007 Chrome路径进展

TEST-008：用户在外部Chrome启动后首次attempt成功，2.19秒connected、4.1秒真实首帧，没有此前RTCPeerConnection unsupported。外部Chrome可用路径已验证，内置浏览器的完整服务端协商兼容性仍未解决；基础SDP检查通过不等于所有远端配置通过。建议现场演示使用Chrome。视觉换装尚待反馈，BUG-001与M4不因首帧通过而关闭。

## BUG-011 · P1 · Chrome全屏时完整取景画面过小

用户反馈Chrome全屏预览太小。原因：输入虽完整横画幅，显示仍被固定9:16窄容器限制；主布局最大1600px也限制大屏宽度。修复：完整取景容器铺满右侧，视频contain保留全部范围、不拉伸；主布局用全部窗口宽度。竖屏裁切仍保留9:16。新增放大试衣区/退出/Esc，运行时保持开始/应用、结束可见，不触发模型重连或改变计费。浏览器DOM检查：1280×720下完整容器与stage宽度均849px；放大区覆盖1280×720，结束按钮底部571.9px在视口内，中英切换通过。实际摄像头大小待用户复核。关联REQ-002/004、DEC-011、TEST-009。

## BUG-012 · P2 · 摄像头错误误归类ICE、首段FPS偏低

本机旧日志camera-error中device包含ice子串，被/ice/误归为ICE。改为优先识别浏览器摄像头异常名并匹配独立ICE词/明确错误码，新增回归覆盖NotFound/NotAllowed/NotReadable/Overconstrained和真实ICE错误。首段输出FPS的计时曾含连接等待，现从decoded首帧开始独立统计；补充每约3秒输出FPS/实际视频尺寸及应用请求耗时的脱敏日志。15项自动检查通过，新日志指标待现场产生。旧日志分类有误保留历史，不用它声称网络故障。关联REQ-006/TEST-010。

## BUG-013 · P2 · 大图费用面板被遮住

放大试衣区固定覆盖页面，费用面板原在main之后，点击后仍在覆盖层后方。费用入口现在先退出大图再展开记录，保持连接和计费状态。浏览器复测expanded=false、panelHidden=false、bodyLocked=false，面板顶部在视口内；费用数据不入公共记录。关联REQ-007/TEST-010。程序通过。

## BUG-014 · P2 · 首次授权未自动沿用iPhone优先选择

免费预览原先先开默认设备，授权后虽然列表优先iPhone，却用默认轨道设置覆盖选择，导致仍需手动切换。现在获取摄像头前刷新可用设备，优先当前明确选择、上次偏好、iPhone、默认；首次无明确偏好时，授权后若发现iPhone会在免费预览阶段重新获取，旧轨道关闭，迟到授权仍按cameraEpoch清理。独立设备优先级回归通过，实际首次授权流程待现场验证。运行中摄像头切换仍锁定，不自动更改活动模型输入。关联REQ-004/TEST-010。

## BUG-015 · P1 · 额度/并发错误与SDK有意终止原因被覆盖 · 2026-10-13

复查发现2026-10-10 11:24:02（Asia/Singapore）的真实会话先记录WEBRTC_SERVER_ERROR / reason=credit，随后disconnected触发泛化“连接已断开”。旧friendly仅对错误码中的QUOTA/LIMIT/CREDIT提示额度类错误，未采用已有reason=credit；通用WEBRTC_SERVER_ERROR因此遗漏。SDK0.2.7源码finishTerminally先setState(disconnected)再emit(sessionEnded)，旧页面在disconnected立即取消lane，后续具体sessionEnded回调失效。这是界面错误保留和事件时序缺陷，不证明供应商或今日账户的具体问题。

修复DEV-009/DEC-015：错误原因映射为脱敏可操作提示，代码型CREDITS也可分类；每次连接独立保存提示，成功恢复后清除。断开处理延到微任务，在同轮sessionEnded先到时由结构化原因完成清理，迟到回调不能结束新连接。区分insufficient_credits、session_limit、内容策略和未知原因，未知值不写日志/界面。终止代码白名单进入本机日志，录像清理沿用既有stop。

TEST-018三项新增回归/总24项通过，浏览器模拟SDK顺序genericStops=0，中英具体提示通过。程序修复通过；真实同类错误复测待现场，不能据旧日志认定今天额度不足，更没有账户余额数字。关联REQ-006/TEST-017/018，修复提交以本阶段Git历史追溯。

## BUG-016 · P2 · 本机预置图片服务缺少JPEG声明 · 2026-10-13 · 程序通过

新增James.jpg时发现服务mime表只有PNG/WebP，JPG会返回application/octet-stream并带nosniff。补齐.jpg/.jpeg→image/jpeg及扩展名小写匹配；本机真实JPEG路由200、图片预加载/小图/大图正常，既有server回归对所有可用本机摄影检查image响应通过。未将其误报为Decart API格式故障。关联DEV-010/TEST-019；修复版本本阶段Git提交。

## BUG-017 · P1 · 将SDK通用policy关闭误报为内容审核 · 2026-10-13 · 程序通过／现场待复测

用户反馈“Decart因内容策略结束会话”。15:09现场日志在首帧前先有WEBRTC_SERVER_ERROR/reason=credit，再disconnected与SESSION_END_POLICY。DEV-009将moderation_violation和policy_violation映射为同一提示与同一诊断码，导致解释过强、信息丢失；这是本Demo错误，不是已证实的球衣审核拒绝。

已核对安装SDK0.2.7：terminalReasonFromClose把通用WebSocket1008映射policy_violation；只有明确moderation_violation才是内容审核终止。旧日志因聚合同码，无法事后还原本次原始枚举；credit是固定分类，也不能区分具体余额/并发数字。不得用这些记录断言詹姆斯照片违规或今天余额为0。

修复DEV-011/DEC-017：通用policy显示未知服务端规则，若此前有可信的额度/认证/来源/模型提示则保留；明确moderation仍单独显示内容审核。诊断码拆分SESSION_END_POLICY_GENERIC/SESSION_END_MODERATION；新增固定额度相关词，不存数字/账户身份/原始消息。新增三项回归，总27检查通过。当前可用额度等待用户在平台确认，不自动重试收费连接。修复版本本阶段Git提交，关联TEST-020/021。

## BUG-018 · 测试子进程先退出导致清理等待遗漏 · 2026-10-13 · 通过

严重性P2，仅测试工具。受限环境不能监听测试端口，子进程在finally前已退出；旧finally再次等待exit事件而挂起。先判断exitCode/signalCode，仅仍存活时注册退出监听并停止，修复版本DEV-013；允许本机端口环境31项回归通过。实际生产服务未受此测试工具问题影响。

## BUG-019 · 浏览器计时器接收者导致30秒限制抛错 · 2026-10-13 · 修复／浏览器复测通过

P1，DEV-014/TEST-026。自动录像合成浏览器测试发现SessionDeadline.start抛Illegal invocation：默认setTimeout/clearTimeout存为实例方法后以实例为this调用，部分浏览器要求Window接收者。此前Node假时钟未覆盖此约束，故31项程序通过不能证明浏览器截止可靠；之前的真实30秒截止仍未验收。改用显式globalThis包装，新增要求全局this的回归。没有发起收费生成。
