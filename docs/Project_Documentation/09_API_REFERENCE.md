# 09_API_REFERENCE

> 基于 `server/main.py` + `server/*_routes.py` 汇总。  
> 说明：`/api/admin/*` 路由整体挂载了 developer 依赖（`require_developer_session`）。

## 鉴权说明

- `无鉴权`：可匿名访问（当前实现）
- `Bearer`：需要 `Authorization: Bearer <token>`
- `Developer`：登录且角色为 developer/admin
- `BridgeToken`：需要 `Authorization: Bearer <SHENZHOU_INTERNAL_TOKEN>`

---

## A. 核心聊天与账号 API

| Method | URL | 鉴权 | 参数 | 返回值（关键） | 前端调用位置 | 依赖模块 |
|---|---|---|---|---|---|---|
| GET | `/api/health` | 无鉴权 | 无 | `status` | `src/lib/chatApi.ts` | `server/main.py` |
| POST | `/api/login` | 无鉴权 | `username,password` | `access_token,role,is_admin` | `src/lib/authApi.ts` | `server/auth.py`, `server/auth_session.py` |
| POST | `/api/register` | 无鉴权 | `username,password` | `access_token,role,is_admin` | `src/lib/authApi.ts` | `server/auth.py` |
| GET | `/api/user/persona` | Bearer | 无 | `required,configured,persona` | `src/lib/userPersonaApi.ts` | `server/user_persona.py` |
| PUT | `/api/user/persona` | Bearer（user） | `display_name,style_prompt,*_api_key` | `persona` | `src/lib/userPersonaApi.ts` | `server/user_persona.py` |
| GET | `/api/character` | Bearer | `character_id`(query) | `id,name,ai_type,user_mbti` | `src/lib/chatApi.ts` | `neuralpal/characters/store.py` |
| POST | `/api/chat` | Bearer | `text,session_id,character_id,trace_id` + `X-Trace-Id` | `text,route,blocked,trust_delta,work_mode` | `src/lib/chatApi.ts` | `ChatService`, `neuralpal/memory/memory_system.py` |
| POST | `/api/reset` | Bearer | `session_id`（可省略） | `ok` | 无【未调用】 | `ChatService.reset_session` |
| POST | `/api/debug/trace` | 无鉴权 | debug payload | `ok` | 无【未调用】 | `server/main.py` |

---

## B. Agent、语音、Realtime、Trace API

| Method | URL | 鉴权 | 参数 | 返回值（关键） | 前端调用位置 | 依赖模块 |
|---|---|---|---|---|---|---|
| GET | `/api/agent/pending` | Bearer | 无 | `pending` | 无（聊天间接依赖） | `neuralpal/tools/agent/pending.py` |
| POST | `/api/agent/confirm` | Bearer | `session_id,character_id` | `handled,pending_action,execution_summary` | 无（聊天间接依赖） | `neuralpal/tools/agent/preprocess.py` |
| POST | `/api/agent/cancel` | Bearer | `session_id,character_id` | `cancelled,task_id` | 无（聊天间接依赖） | `neuralpal/tools/agent/pending.py` |
| POST | `/api/realtime/session` | Bearer | `character_id,session_id,mode` | `client_secret,model,voice,expires_at` | `src/lib/realtimeApi.ts` | `server/realtime_service.py` |
| GET | `/api/voice/status` | 无鉴权 | 无 | `stt_available,tts_available,...` | `src/lib/voiceApi.ts` | `server/voice_service.py` |
| POST | `/api/voice/stt` | 无鉴权 | `audio`(multipart),`purpose` | `text,wake_phrase,cleaned_text` | `src/lib/voiceApi.ts` | `server/voice_service.py` |
| POST | `/api/voice/tts` | 无鉴权 | `text,trace_id` + `X-Trace-Id` | `chunks[]` | `src/lib/voiceApi.ts` | `server/voice_service.py` |
| GET | `/api/trace/{trace_id}` | 无鉴权 | `trace_id`(path) | trace JSON | 无【未调用】 | `neuralpal/trace/storage.py` |
| POST | `/api/trace/client` | 无鉴权 | `trace_id,pipeline,tts,timings,errors...` | `ok,path` | `src/lib/executionTrace.ts` | `neuralpal/trace/recorder.py` |

---

## C. 信任度与系统 API

| Method | URL | 鉴权 | 参数 | 返回值（关键） | 前端调用位置 | 依赖模块 |
|---|---|---|---|---|---|---|
| GET | `/api/auth/role` | Bearer | `username`(query) | `role,is_admin` | 无【未调用】 | `server/trust_routes.py` |
| GET | `/api/trust` | Bearer（admin） | `character_id` | trust snapshot | `src/lib/trustApi.ts` | `server/trust_service.py` |
| PUT | `/api/admin/trust` | Bearer（admin） | `username,character_id,trust_points` | trust snapshot | `src/lib/trustApi.ts` | `server/trust_service.py` |
| GET | `/api/system/version` | 无鉴权 | 无 | `version,build_id,git_rev` | `src/lib/systemApi.ts` | `neuralpal/system/app_update.py` |
| GET | `/api/system/update/check` | 无鉴权 | `force`(query) | `update_available,commits_behind` | `src/hooks/useBackendUpdate.ts` | `app_update.py` |
| POST | `/api/system/update/dismiss` | 无鉴权 | `build_id` | `ok` | `src/hooks/useBackendUpdate.ts` | `app_update.py` |
| POST | `/api/system/update/apply` | 无鉴权 | 无 | `ok,message,steps` | `src/hooks/useBackendUpdate.ts` | `app_update.py` |
| GET | `/api/system/permissions` | 无鉴权 | `force`(query) | permissions snapshot | `src/hooks/useMacPermissions.ts` | `neuralpal/system/permissions.py` |
| POST | `/api/system/permissions/open` | 无鉴权 | `kind` | `ok,kind` | `src/hooks/useMacPermissions.ts` | `permissions.py` |
| POST | `/api/system/permissions/auto-setup` | 无鉴权 | 无 | `all_granted,steps,snapshot` | `src/hooks/useMacPermissions.ts` | `permissions.py` |
| GET | `/api/system/work-mode` | Bearer | `session_id,character_id` | work mode snapshot | `src/lib/workModeApi.ts` | `neuralpal/schedule/work_mode.py` |

---

## D. 管理后台 API（/api/admin/*，Developer）

| Method | URL | 鉴权 | 参数 | 返回值（关键） | 前端调用位置 | 依赖模块 |
|---|---|---|---|---|---|---|
| GET | `/api/admin/memory/summary` | Developer | `character_id` | `counts,maintenance_hint` | `src/lib/adminApi.ts` | `neuralpal/memory/admin_service.py` |
| GET | `/api/admin/memory` | Developer | `tier,character_id` | `items[]` | `src/lib/adminApi.ts` | `admin_service.py` |
| GET | `/api/admin/memory/detail` | Developer | `rel_path,character_id` | `title,body,category` | `src/lib/adminApi.ts` | `admin_service.py` |
| DELETE | `/api/admin/memory` | Developer | `character_id,rel_path` | `ok` | `src/lib/adminApi.ts` | `admin_service.py` |
| POST | `/api/admin/memory/mark` | Developer | `character_id,rel_path` | `ok,marked` | `src/lib/adminApi.ts` | `admin_service.py` |
| POST | `/api/admin/memory/maintenance` | Developer | `character_id,action,dry_run` | maintenance result | `src/lib/adminApi.ts` | `admin_service.py` |
| POST | `/api/admin/memory/titles` | Developer | `character_id,limit` | `queued` | `src/lib/adminApi.ts` | `admin_service.py` |
| POST | `/api/admin/memory/messages/delete` | Developer | `character_id,rel_path/session_id,indices[]` | delete result | `src/lib/adminApi.ts` | `admin_service.py`, `ChatService` |
| GET | `/api/admin/chat/history` | Developer | `session_id` | `messages,count` | `src/lib/adminApi.ts` | `ChatService` |
| DELETE | `/api/admin/chat/session` | Developer | `session_id` | `ok` | `src/lib/adminApi.ts` | `ChatService` |

---

## E. Shenzhou 与桥接 API

| Method | URL | 鉴权 | 参数 | 返回值（关键） | 前端调用位置 | 依赖模块 |
|---|---|---|---|---|---|---|
| POST | `/api/shenzhou/sync-user-day` | Developer | `session_id` | sync result | 无【无入口】 | `neuralpal/shenzhou/scheduler.py` |
| POST | `/api/shenzhou/pull-life-context` | Developer | 无 | pull result | 无【无入口】 | `scheduler.py` |
| POST | `/api/shenzhou/run-pipeline` | Developer | `skip_bulk_fix,skip_simulation` | pipeline result | 无【无入口】 | `scheduler.py` |
| POST | `/api/shenzhou/proactive-run` | Developer | `force` | proactive result | 无【无入口】 | `scheduler.py` |
| POST | `/api/shenzhou/archive-context` | Developer | `backfill` | archive result | 无【无入口】 | `scheduler.py` |
| GET | `/api/shenzhou/status` | Developer | 无 | enabled/schedule/reachable | 无【无入口】 | `scheduler.py`, `client.py` |
| GET | `/api/shenzhou/export-user-day` | BridgeToken | `session_id,day` | day payload | 无【桥接专用】 | `neuralpal/shenzhou/sync.py` |
| POST | `/api/shenzhou/push-life-context` | BridgeToken | life context payload | `ok,cache,date` | 无【桥接专用】 | `sync.py` |
| ALL | `/world/{path}` | Developer | path + request passthrough | proxy response | 无【无入口】 | `server/shenzhou_proxy.py` |

---

## F. App 模式静态路由

| Method | URL | 鉴权 | 参数 | 返回值（关键） | 说明 |
|---|---|---|---|---|---|
| GET | `/` | 无鉴权 | 无 | `index.html` | 仅 `JARVIS_APP_MODE=1` 启用 |
| GET | `/{full_path}` | 无鉴权 | 路径参数 | 静态文件或 `index.html` | `api/*` 与 `world/*` 会被排除 |

---

## API 风险提示（基于现状）

- `/api/voice/*` 当前无会话鉴权，公网部署需网关保护
- `/api/system/update/*` 当前无鉴权，建议改为 developer 限制
- `/api/trace/*` 可匿名写入，建议按环境加限流与鉴权

