# 06_CHANGELOG

> 基线来源：`git log --oneline --decorate`（当前分支 `main`）+ `package.json` 版本号。  
> 当前应用版本：`0.1.0`（无 tag 发布记录）。

## 版本策略说明

- 当前仓库未使用 Git Tag 管理语义化版本
- 前端/应用版本读取 `package.json.version = 0.1.0`
- 以下变更按提交顺序整理为“里程碑式历史”

---

## [0.1.0] - 当前主线

### 新增（Features）

- 新增普通用户 Persona API Key 字段与“至少填写 1 个 Key”校验  
  - 提交：`b9cc51b`
- 新增 PWA 安装提示（面向云端内测）  
  - 提交：`f6ba5db`
- 新增云端中心机部署脚本（systemd + Nginx 配置方案）  
  - 提交：`f5f4617`
- 新增本地世界引擎桥接 API（export/push）与相关调度策略  
  - 提交：`26930c3`

### 优化（Improvements）

- 修复 PWA 安装弹窗在云端链接下的显示行为  
  - 提交：`1f5d196`
- 修复 root 克隆仓库后的部署脚本权限与 git ownership 问题  
  - 提交：`4601346`

### 修复（Bug Fixes）

- 部署场景下 `safe.directory` 相关流程兼容性修正（`deploy_server.sh`）  
  - 提交：`4601346`
- PWA 安装提示触发条件修正  
  - 提交：`1f5d196`

### Breaking Changes（潜在）

- 普通用户 Persona 配置策略调整：创建人物时要求至少一个 API Key  
  - 影响：旧流程“只填名字和风格”不再通过
- 云端部署默认建议关闭部分本机能力（例如 Agent）  
  - 影响：与本地部署能力边界不同

---

## 历史里程碑（按提交）

- `503cdce` Initial import of NeuralPal / 贾维斯 project
- `f5f4617` Add cloud server deployment and shenzhou integration updates.
- `4601346` Fix deploy script git ownership for root-cloned repos.
- `26930c3` 本地世界引擎桥接：export/push API + 云端关闭 scheduler
- `f6ba5db` Add PWA install prompt for cloud internal testers.
- `1f5d196` Fix PWA install modal visibility on cloud links.
- `b9cc51b` add persona API key fields with one-of-four validation

---

## 版本推断结论

- 当前仍处于 `0.1.0` 的“快速迭代期”
- 产品核心能力已形成，但发布管理（tag/release note）尚未制度化
- 建议下一步引入：
  - 语义化版本（SemVer）
  - 发布分支与 tag
  - 自动化 CHANGELOG 生成流程

