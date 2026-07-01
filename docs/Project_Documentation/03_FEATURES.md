# 03_FEATURES

> 口径：按“用户可感知能力”而非代码目录分类。  
> 状态标记：`【已完成】` `【开发中】` `【规划中】` `【无入口】` `【未调用】` `【Demo/历史遗留】`

## 1) 聊天（文本对话）【已完成】

- 功能：角色化聊天与多轮上下文对话
- 作用：提供主交互界面，支持分段回复与状态反馈
- 用户价值：稳定、连续、可恢复的日常对话体验
- 入口位置：`src/components/boot/NeuralInterface.tsx`
- 对应页面：主对话面板（唤醒后）
- 依赖模块：`src/hooks/useChat.ts` `src/lib/chatApi.ts` `server/main.py:/api/chat`
- 未来规划：无（核心链路已可用）

## 2) 身份系统（登录/注册/会话）【已完成】

- 功能：登录、注册、会话令牌、角色权限
- 作用：区分 developer 与 user，并绑定独立会话 ID
- 用户价值：多用户隔离与访问控制基础
- 入口位置：`src/components/boot/StartGate.tsx`
- 对应页面：启动登录页
- 依赖模块：`src/hooks/useAuth.ts` `server/auth.py` `server/auth_session.py`
- 未来规划：密码哈希与更强安全策略（当前为明文存储）

## 3) 普通用户自定义 Persona【已完成】

- 功能：普通用户首次登录后创建 AI 人物（名称/风格/API Key）
- 作用：为 user 角色提供专属人格配置
- 用户价值：从“共享角色”升级为“个人角色”
- 入口位置：`StartGate` 的 persona 表单
- 对应页面：启动阶段 persona 创建页
- 依赖模块：`src/hooks/useUserPersona.ts` `server/user_persona.py` `/api/user/persona`
- 未来规划：将用户 API Key 接入模型运行时多租户策略【开发中】

## 4) 长短期记忆（记忆宫殿）【已完成】

- 功能：短期会话记忆、中期汇总、长期记忆双写与召回
- 作用：保障跨轮、跨天连续性
- 用户价值：减少重复解释，形成长期“懂你”
- 入口位置：聊天自动生效 + 开发者记忆后台
- 对应页面：主对话页、记忆面板
- 依赖模块：`neuralpal/memory/memory_system.py` `neuralpal/memory/memory_maintenance.py`
- 未来规划：继续提升召回精准度与归档策略

## 5) 记忆后台管理（开发者）【已完成】

- 功能：短/中/长期记忆浏览、详情、标记、删除、维护
- 作用：可视化管理记忆质量与会话数据
- 用户价值：运营可控、可审计、可清洗
- 入口位置：右下角“记忆”按钮
- 对应页面：`ShenzhouAdminPanel` 抽屉面板
- 依赖模块：`src/components/admin/ShenzhouAdminPanel.tsx` `/api/admin/*`
- 未来规划：增加更细粒度筛选与批量操作

## 6) 语音输入（语音转文字）【已完成】

- 功能：麦克风录音、STT 转写、填充输入框
- 作用：支持“先说再发”的输入模式
- 用户价值：提高输入效率
- 入口位置：输入框右侧麦克风按钮
- 对应页面：主对话页
- 依赖模块：`src/hooks/useVoiceInput.ts` `/api/voice/stt`
- 未来规划：优化识别稳定性与长语音策略

## 7) 语音对话（传统 STT->LLM->TTS）【已完成】

- 功能：唤醒词、VAD、连续跟随对话、TTS 播放
- 作用：实现“听-想-说”闭环
- 用户价值：免手打连续语音交互
- 入口位置：主对话页“语音对话”开关（Realtime 关闭时）
- 对应页面：主对话页
- 依赖模块：`src/hooks/useVoiceDialog.ts` `server/voice_service.py`
- 未来规划：继续优化唤醒词误触与噪音场景

## 8) Realtime Voice（WebRTC）【已完成】

- 功能：创建 ephemeral session、浏览器直连实时语音
- 作用：降低语音交互延迟
- 用户价值：更自然口语体验
- 入口位置：主对话页“Realtime 语音”开关（需 env 打开）
- 对应页面：主对话页
- 依赖模块：`src/hooks/useRealtimeVoice.ts` `/api/realtime/session` `server/realtime_service.py`
- 未来规划：完善网络异常与自动重连体验

## 9) 文字朗读 TTS【已完成】

- 功能：将助手回复切片合成为音频并顺序播放
- 作用：文字对话可“听出来”
- 用户价值：免盯屏、可边做事边听
- 入口位置：主对话页“文字朗读：开/关”
- 对应页面：主对话页
- 依赖模块：`src/hooks/useReadAloud.ts` `/api/voice/tts`
- 未来规划：多音色管理与更细粒度开关

## 10) AI Agent 电脑代办（确认后执行）【已完成】

- 功能：propose -> confirm -> execute -> pending 状态管理
- 作用：把“建议”变成“可执行动作”
- 用户价值：提高执行效率并保留安全确认
- 入口位置：通过聊天自然触发
- 对应页面：主对话页（无独立任务页）
- 依赖模块：`neuralpal/tools/agent/*` `/api/agent/pending|confirm|cancel`
- 未来规划：新增任务队列可视化与执行回放【规划中】

## 11) 工作模式与加班机制【已完成】

- 功能：工作/陪伴/加班状态判断，影响工具可用性
- 作用：将角色行为与时间规则绑定
- 用户价值：行为一致性更强
- 入口位置：开发者可见 WorkModeBadge
- 对应页面：主对话页状态区
- 依赖模块：`neuralpal/schedule/work_mode.py` `/api/system/work-mode`
- 未来规划：开放给普通用户查看（当前偏开发者）

## 12) 信任度 TP 系统【已完成】

- 功能：信任分快照、手动调节、规则分层
- 作用：驱动关系阶段与回复风格边界
- 用户价值：关系演进可视化
- 入口位置：开发者可见 IntimacyBar
- 对应页面：主对话页右侧条形控件
- 依赖模块：`data/characters/沈昼/rules/trust_system.json` `/api/trust` `/api/admin/trust`
- 未来规划：自动评分策略持续调优

## 13) macOS 权限引导【已完成】

- 功能：权限检测、自动拉起系统设置、状态面板
- 作用：支撑 Agent 对系统能力访问
- 用户价值：降低授权门槛
- 入口位置：左下角“权限”按钮 + 系统弹层
- 对应页面：`SystemModalsShell` 下权限模态
- 依赖模块：`src/hooks/useMacPermissions.ts` `/api/system/permissions*`
- 未来规划：更多平台兼容（当前重点 Darwin）

## 14) PWA 安装与更新【已完成】

- 功能：安装引导、SW 更新提示、后端 Git 更新提示
- 作用：让 Web 应用具备接近桌面应用体验
- 用户价值：低门槛安装与持续升级
- 入口位置：系统模态层
- 对应页面：`PwaInstallModal` `UpdatePromptModal`
- 依赖模块：`vite.config.ts` `src/hooks/usePwaInstall.ts` `src/hooks/useBackendUpdate.ts`
- 未来规划：更新策略分渠道细化

## 15) Shenzhou 世界引擎同步【已完成】

- 功能：同步用户日数据、拉取 life context、主动触达、归档
- 作用：让 AI 获得“今天发生了什么”的外部上下文
- 用户价值：对话更贴近现实时间线
- 入口位置：后端 API（前端无统一管理页）
- 对应页面：无前端控制台
- 依赖模块：`neuralpal/shenzhou/*` `/api/shenzhou/*` `/world/*`
- 未来规划：前端可视化运营面板【规划中】

## 16) 执行追踪 Trace【已完成】

- 功能：trace_id 贯通、前后端 patch 合并、trace 文件落盘
- 作用：调试延迟、错误、TTS链路
- 用户价值：提高可维护性与排障效率（主要面向开发者）
- 入口位置：自动上报（无专门 UI）
- 对应页面：无
- 依赖模块：`src/lib/executionTrace.ts` `/api/trace/client` `data/traces/*.json`
- 未来规划：增加可视化 Trace Viewer【规划中】

## 17) Topic Radar 话题雷达【开发中】

- 功能：CPC 画像、搜索目标、对话种子模型定义
- 作用：计划提供外部热点到对话种子的生产链路
- 用户价值：更主动、更有新鲜度的话题推荐
- 入口位置：无
- 对应页面：无
- 依赖模块：`neuralpal/topic_radar/config.py` `models.py`
- 现状说明：`topic_radar_service` / `bridge.py` 等关键实现文件缺失
- 未来规划：补齐 service/scheduler/bridge 后再接入主链路

## 18) Reminder 插件化工具【开发中】

- 功能：提醒工具桥接框架已存在
- 作用：预留可插拔工具调用能力
- 用户价值：潜在的待办提醒与定时服务
- 入口位置：无显式 UI
- 对应页面：无
- 依赖模块：`neuralpal/tools/reminder/langchain_bridge.py` `tools.py`
- 现状说明：`build_reminder_langchain_tools()` 当前返回空列表（占位）
- 未来规划：补齐真实提醒工具实现

## 无入口 / 未调用 / Demo 清单

- `/api/auth/role`：前端存在 `authRoleApi`，但未被调用【未调用】
- `/api/reset`：`resetChatSession` 定义存在，但无实际调用【未调用】
- `/api/shenzhou/*`：后端能力齐全，前端无对应管理入口【无入口】
- `/api/trace/{trace_id}`：可读接口存在，前端当前仅写不读【未调用】
- 根 `README.md` 仍描述为“wakeup 动画项目”【Demo/历史遗留】

