import type { ChatHistoryMessage } from './adminApi'

/** 从短期记忆 markdown 正文中解析用户 / 助手轮次（纯对话文本）。 */
export function parseMemoryChatBody(body: string): ChatHistoryMessage[] {
  const stripped = body.replace(/^---[\s\S]*?---\s*/m, '').trim()
  const messages: ChatHistoryMessage[] = []

  const blockRe = /^###\s*(用户|助手)\s*\r?\n([\s\S]*?)(?=^###\s*(?:用户|助手)\s*\r?\n|$)/gm
  let match: RegExpExecArray | null
  while ((match = blockRe.exec(stripped)) !== null) {
    const role = match[1] === '用户' ? 'user' : 'assistant'
    const content = match[2].trim()
    if (content) {
      messages.push({ role, content })
    }
  }

  if (messages.length > 0) {
    return messages
  }

  // 兜底：旧格式「用户：…」「助手：…」行
  for (const line of stripped.split(/\r?\n/)) {
    const trimmed = line.trim()
    if (trimmed.startsWith('用户：') || trimmed.startsWith('用户:')) {
      messages.push({ role: 'user', content: trimmed.replace(/^用户[:：]\s*/, '') })
    } else if (trimmed.startsWith('助手：') || trimmed.startsWith('助手:')) {
      messages.push({ role: 'assistant', content: trimmed.replace(/^助手[:：]\s*/, '') })
    }
  }

  return messages
}

/** 短期记忆卡片标题：日期 + 会话名（不展示冗长 AI 摘要标题）。 */
export function shortMemorySessionLabel(item: { title: string; date_label: string; rel_path: string }): string {
  const sessionName = item.rel_path.split('/').pop()?.replace(/\.md$/i, '') ?? ''
  const date = item.date_label?.trim()
  if (date && sessionName) return `${date} · ${sessionName}`
  return sessionName || date || item.title || '会话'
}
