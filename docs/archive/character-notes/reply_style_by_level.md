# 沈昼 · 分信任等级回复特征（索引）

> **运行时注入说明**：对话时**不再**整份注入本文件。  
> 系统按当前 TP 从 `reply_styles/` 目录加载**对应档位**的独立文件（见 `trust_system.json` → `reply_style_files`）。

---

## 档位与文件对照

| TP 区间 | 信任等级 | 注入文件 |
|---------|----------|----------|
| 0–20 | 一级 · 陌生礼貌期 | `reply_styles/tier_1.md` |
| 21–50 | 二级 · 松弛熟人期 | `reply_styles/tier_2.md` |
| 51–80 | 三级 · 亲密信赖期 | `reply_styles/tier_3.md` |
| 81–100 | 四级 · 核心例外期 | `reply_styles/tier_3.md` + `reply_styles/tier_4.md` |

各档位全文已拆分至 `reply_styles/` 目录。渐变区间说明见 `trust_system.json` → `gradient_bands`，运行时写入「当前信任度状态」块。

通用过渡原则见 `reply_styles/_transition.md`（每轮一并注入，篇幅很短）。

机器可读权限锁：`trust_system.json` → `permission_locks`
