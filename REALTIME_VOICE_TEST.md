# Realtime Voice Chat 测试指南

OpenAI Realtime WebRTC 官方架构：

1. **后端** `POST https://api.openai.com/v1/realtime/client_secrets`（Bearer `OPENAI_API_KEY`）→ `response.value`（ephemeral token）
2. **前端** 永不接触真实 API Key
3. **浏览器** `POST https://api.openai.com/v1/realtime/calls`（Bearer ephemeral + SDP offer）
4. 麦克风入、远端 audio track 出、`oai-events` data channel 收发事件

---

## 1. 配置 `.env`

```bash
cd "/Users/dai/Desktop/贾维斯"
cp .env.example .env
```

必填：

```env
OPENAI_API_KEY=sk-...
OPENAI_REALTIME_MODEL=gpt-realtime
OPENAI_REALTIME_VOICE=alloy
VITE_ENABLE_REALTIME_VOICE=true
```

关闭 Realtime、回退旧链路：

```env
VITE_ENABLE_REALTIME_VOICE=false
```

旧链路仍需 ElevenLabs（Read Aloud / 旧 Voice Dialog）：

```env
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...
```

---

## 2. 启动后端

```bash
bash scripts/run_backend.sh
# 或
bash scripts/run_jarvis.sh
```

验证 ephemeral token 接口：

```bash
curl -s -X POST http://127.0.0.1:8766/api/realtime/session \
  -H 'Content-Type: application/json' \
  -d '{"character_id":"34750dfcf3be","session_id":"user-jason","mode":"voice_chat"}' \
  | python3 -m json.tool
```

期望返回：`client_secret`、`model`、`voice`、`expires_at`、`session_id`（**不含**真实 API Key）。

---

## 3. 启动前端

```bash
npm run dev
# 或 run_jarvis.sh 一并启动
```

打开 `http://127.0.0.1:5190`，登录后进入对话界面。

---

## 4. 浏览器麦克风权限

1. 点击 **Realtime 语音：关** 开启会话
2. 浏览器弹出麦克风授权 → 选择「允许」
3. Console 应出现：
   - `[RealtimeVoice] creating session`
   - `[RealtimeVoice] microphone ready`
   - `[RealtimeVoice] peer connection created`
   - `[RealtimeVoice] data channel open`
   - `[RealtimeVoice] connected`

---

## 5. 测试清单

| 步骤 | 操作 | 期望 |
|------|------|------|
| 开始 | 点击 Realtime 语音按钮 | 状态 Connecting → Listening |
| 说话 | 对着麦克风说「你好」 | 模型语音回复（沈昼口吻） |
| 打断 | 模型说话时点击 **Interrupt** 或继续说话 | 回复停止，回到 Listening |
| 停止 | 点击 **Stop** | 会话关闭，麦克风释放 |
| 文字聊天 | 输入框发文字 | 不受影响 |
| Read Aloud | 开启文字朗读 | 仍走 ElevenLabs `/api/voice/tts` |
| Fallback | `VITE_ENABLE_REALTIME_VOICE=false` | 旧唤醒词 Voice Dialog 可用 |

---

## 6. 常见错误

| 现象 | 原因 | 处理 |
|------|------|------|
| `未配置 OPENAI_API_KEY` | `.env` 缺 Key | 填写后重启后端 |
| `microphone permission denied` | 用户拒绝麦克风 | 浏览器设置 → 站点权限 → 麦克风允许 |
| `WebRTC connection failed` | 网络/防火墙 | 检查能否访问 `api.openai.com` |
| `ephemeral token expired` | token 约 1 分钟过期 | 重新点击开始语音 |
| `浏览器阻止自动播放` | autoplay 策略 | 点击页面任意处后再试 |
| Realtime 502 | OpenAI API 错误 | 查看后端 `[RealtimeSession] error` 日志（不含 Key） |

---

## 7. 后端日志关键字

```
[RealtimeSession] request received
[RealtimeSession] character_id
[RealtimeSession] session_id
[RealtimeSession] model
[RealtimeSession] token created
[RealtimeSession] error
```

---

## 8. 构建验证

```bash
npm run build
python3 -c "from server.realtime_service import create_realtime_session; print('ok')"
```
