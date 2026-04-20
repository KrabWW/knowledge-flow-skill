"""
配置管理
"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# ============ 飞书云文档配置 ============
# 需求文档的飞书 URL（支持 docx 格式）
LARK_DOC_URL = os.environ.get("LARK_DOC_URL", "https://www.feishu.cn/docx/LtvhdMMqvoKgNXxLP7acpyEonPc")

# 知识回流目标文档（默认等于需求文档，审查结果写入同一文档）
LARK_KB_DOC_URL = os.environ.get("LARK_KB_DOC_URL", LARK_DOC_URL)

# ============ 本地需求文档（备用） ============
REQUIRED_DOCS = [
    PROJECT_ROOT / "ticket_req.md",
]

# ============ 审查设置 ============
BLOCK_ON_ERROR = False  # 默认不拦截，用户决策
MAX_DIFF_LINES = 200  # 限制 diff 大小（Claude Code 需要快速响应）

# Claude Code CLI 路径
CLAUDE_CMD = os.environ.get("CLAUDE_CMD", "claude")
