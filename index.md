---
name: knowledge-flow
description: 从飞书提取知识并回写到项目
trigger:
  - "知识回流"
  - "飞书知识"
  - "同步会议"
  - "会议纪要"
  - "wiki sync"
---

# 知识回流 Skill

从飞书的多媒体内容中提取知识，自动回写到项目知识库。

## 使用前检查

确保已安装飞书 CLI:

```bash
lark-cli --version
npx skills list | grep larksuite
```

如果未安装，运行一键安装器:

```bash
npx @your-org/knowledge-flow-installer
```

## 使用方法

### 1. 同步会议纪要

> "把最近7天的飞书会议纪要同步到项目"

> "提取昨天的会议中关于 API 设计的讨论"

> "知识回流会议纪要，关键词: 性能优化"

### 2. 同步 Wiki 更新

> "检查飞书知识库的 API 设计文档更新"

> "同步 Wiki 中关于数据库 schema 的修改"

> "知识回流 Wiki，时间范围: 1w"

### 3. 提取消息待办

> "从飞书群聊中提取与本项目相关的待办事项"

> "汇总产品群中的需求讨论"

> "知识回流消息，关键词: bug, 优化"

### 4. 全量同步

> "知识回流全部内容，最近1个月"

> "同步飞书所有相关知识到项目"

### 5. 代码审查回流（自动触发）

> "启用代码提交审查"

> "配置 Commit Review Hook"

**自动 Hook 功能**：

每次 `git commit` 时自动触发代码审查：
- ✅ 对比代码变更与飞书需求文档
- ✅ 使用 Claude Code 检查一致性
- ✅ 将审查结果写回飞书文档
- ✅ 提取【新发现】标注为粉色批注

**安装 Hook**：

```bash
cd /path/to/your/project
bash scripts/commit_review/install.sh
```

**环境变量配置**：

```bash
# 飞书需求文档 URL（必需）
export LARK_DOC_URL="https://www.feishu.cn/docx/..."

# 知识回流目标文档（可选，默认等于需求文档）
export LARK_KB_DOC_URL="https://www.feishu.cn/docx/..."
```

**手动触发审查**：

```bash
# 方法 1：通过 Claude Code
运行审查：检查当前代码与需求文档的一致性

# 方法 2：直接运行脚本
uv run python scripts/commit_review/main.py
```

**跳过审查（临时）**：

```bash
git commit --no-verify -m "your message"
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| source | 知识来源: meeting/wiki/doc/im/all | all |
| timeRange | 时间范围: 7d/1w/1m/1y | 7d |
| keywords | 关键词过滤 (数组) | [] |
| outputFormat | 输出格式: markdown/json/summary | summary |

## 输出位置

知识回写到项目以下位置:

```
project/
├── .knowledge/
│   ├── meetings/          # 会议纪要
│   ├── wiki/              # Wiki 文档
│   ├── decisions/         # 决策记录
│   └── action-items/      # 待办事项
└── README.md              # 自动更新项目摘要
```

## 示例命令

```bash
# 直接使用 lark-cli (高级用法)
lark-cli vc +list                    # 列出会议纪要
lark-cli wiki +list                  # 列出知识库
lark-cli im +message --help          # 发送消息
```

## 故障排除

### 认证过期

```bash
lark-cli auth login --recommend
```

### 权限不足

确保飞书应用有以下权限:
- `vc:video_minute:readonly` - 查看会议纪要
- `wiki:wiki:readonly` - 查看知识库
- `im:message` - 读取消息

### 更多帮助

```bash
lark-cli --help
lark-cli [command] --help
```
