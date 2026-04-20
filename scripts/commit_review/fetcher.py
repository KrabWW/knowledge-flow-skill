"""
获取 Git diff、需求文档（飞书云文档）
"""

import subprocess
import sys
import os
import re
import json
import time
import requests
from pathlib import Path
from typing import Optional

from commit_review.config import REQUIRED_DOCS, MAX_DIFF_LINES, LARK_DOC_URL


def get_staged_diff() -> Optional[str]:
    """获取 staged 的 diff（排除临时文件内容）"""
    try:
        result = subprocess.run(
            ["git", "diff", "--staged", "--no-color"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False
        )
        if result.returncode != 0:
            print(f"[WARN] 获取 diff 失败: {result.stderr}", file=sys.stderr)
            return None

        diff = result.stdout
        if not diff:
            return diff

        # 按 diff 块分割过滤（每个块以 "diff --git" 开头）
        import re
        blocks = re.split(r"(?=diff --git)", diff)

        filtered_blocks = []
        for block in blocks:
            if not block.strip():
                continue
            # 提取块对应的文件路径
            m = re.match(r"diff --git a/(.+) b/", block)
            if m:
                file_path = m.group(1)
                if _should_ignore(file_path):
                    continue
            filtered_blocks.append(block)

        return "\n".join(filtered_blocks)
    except FileNotFoundError:
        print("[WARN] git 命令未找到", file=sys.stderr)
        return None


def get_commit_message() -> Optional[str]:
    """获取当前 commit message"""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def get_requirements_docs() -> dict[str, str]:
    """
    读取需求文档

    优先从飞书云文档读取（如果配置了 LARK_DOC_URL）
    否则从本地文件读取
    """
    docs = {}

    # 1. 尝试从飞书云文档读取
    if LARK_DOC_URL:
        lark_content = fetch_from_lark(LARK_DOC_URL)
        if lark_content:
            docs["飞书需求文档"] = lark_content
            return docs

    # 2. 回退到本地文件
    for doc_path in REQUIRED_DOCS:
        if doc_path.exists():
            docs[doc_path.name] = doc_path.read_text(encoding="utf-8")
        else:
            print(f"[WARN] 需求文档不存在: {doc_path}", file=sys.stderr)

    return docs


def fetch_from_lark(doc_url: str) -> Optional[str]:
    """从飞书云文档获取内容"""
    try:
        # 使用 lark-cli 获取文档
        result = subprocess.run(
            ["lark-cli", "docs", "+fetch", "--doc", doc_url, "--format", "markdown"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env={**os.environ, "NO_COLOR": "1"}
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

        print(f"[WARN] 飞书文档获取失败: {result.stderr[:200] if result.stderr else '无输出'}", file=sys.stderr)
        return None

    except subprocess.TimeoutExpired:
        print("[WARN] 飞书文档获取超时", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("[WARN] lark-cli 未找到，请安装: npm install -g @larksuite/cli", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[WARN] 获取飞书文档异常: {e}", file=sys.stderr)
        return None


def write_to_lark(doc_url: str, content: str, section_title: str = "审查记录") -> bool:
    """
    将内容追加到飞书文档（知识回流）

    Args:
        doc_url: 飞书文档 URL
        content: 要写入的内容
        section_title: 小节标题

    Returns:
        是否成功
    """
    try:
        # 构建要追加的内容（Markdown 格式）
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        markdown_content = f"""
## {section_title} - {timestamp}

{content}

---
"""

        # 使用 lark-cli 追加内容到文档（append 模式追加到末尾）
        result = subprocess.run(
            [
                "lark-cli", "docs", "+update",
                "--doc", doc_url,
                "--mode", "append",
                "--markdown", markdown_content,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env={**os.environ, "NO_COLOR": "1"}
        )

        if result.returncode == 0:
            print(f"[OK] 已写入飞书文档")
            return True

        print(f"[WARN] 写入飞书文档失败: {result.stderr[:200] if result.stderr else result.stdout[:200]}", file=sys.stderr)
        return False

    except Exception as e:
        print(f"[WARN] 写入飞书文档异常: {e}", file=sys.stderr)
        return False


def _extract_doc_token(doc_url: str) -> str:
    """从飞书文档 URL 中提取 doc token"""
    # URL 格式: https://xxx.feishu.cn/docx/TOKEN 或直接是 TOKEN
    m = re.search(r'/docx/([a-zA-Z0-9]+)', doc_url)
    if m:
        return m.group(1)
    # 直接是 token
    return doc_url.strip()


def _lark_api(method: str, path: str, data: dict = None, as_user: bool = False) -> Optional[dict]:
    """通过 lark-cli 调用飞书 API（自动处理认证）"""
    cmd = ["lark-cli", "api", method, path]
    if as_user:
        cmd.append("--as")
        cmd.append("user")
    if data:
        cmd += ["--data", json.dumps(data, ensure_ascii=False)]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
            env={**os.environ, "NO_COLOR": "1"}
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
        print(f"[WARN] lark-cli api 调用失败: {result.stderr[:200] if result.stderr else result.stdout[:200]}", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("[WARN] lark-cli api 调用超时", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("[WARN] lark-cli 未找到", file=sys.stderr)
        return None


def write_annotation_to_lark(doc_url: str, annotation: str, label: str = "【新发现】") -> bool:
    """
    将业务规则批注写入飞书文档（知识回流）

    用粉色文字写入文档末尾，作为需求补充标注。
    通过 lark-cli api 调用，自动处理认证。

    Args:
        doc_url: 飞书文档 URL
        annotation: 批注文本（支持多行）
        label: 批注标记，默认 "【新发现】"

    Returns:
        是否成功
    """
    doc_token = _extract_doc_token(doc_url)

    # 1. 获取文档 block 列表，找到最后一个 block（用用户身份访问）
    result = _lark_api("GET", f"/docx/v1/documents/{doc_token}/blocks", as_user=True)
    if not result or result.get("code") != 0:
        print(f"[WARN] 获取文档 blocks 失败: {result}", file=sys.stderr)
        return False

    items = result.get("data", {}).get("items", [])
    if not items:
        print("[WARN] 文档为空，跳过批注", file=sys.stderr)
        return False
    last_block_id = items[-1].get("block_id")

    # 2. 构建粉色文字的 text block
    # Feishu text_color enum: 1=pink, 2=orange, 3=yellow, 4=green, 5=blue, 6=purple, 7=gray
    lines = annotation.strip().split("\n")
    text_elements = []
    for line in lines:
        if line.strip():
            text_elements.append({
                "type": "text_run",
                "text_run": {
                    "content": line + "\n",
                    "text_element_style": {
                        "text_color": 1,  # 粉色
                        "bold": True,
                    }
                }
            })
        else:
            text_elements.append({
                "type": "text_run",
                "text_run": {"content": "\n"}
            })

    if not text_elements:
        return False

    # 3. 在最后一个 block 下插入新文本块
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    blocks_to_create = [
        {
            "block_type": 2,  # TextBlock
            "text": {
                "elements": [
                    {
                        "type": "text_run",
                        "text_run": {
                            "content": f"📌 {label} {timestamp}\n",
                            "text_element_style": {
                                "text_color": 1,
                                "bold": True,
                            }
                        }
                    }
                ]
            }
        },
        {
            "block_type": 2,
            "text": {
                "elements": text_elements
            }
        }
    ]

    result = _lark_api(
        "POST",
        f"/docx/v1/documents/{doc_token}/blocks/{last_block_id}/children",
        {"children": blocks_to_create, "index": -1},
        as_user=True
    )
    if result and result.get("code") == 0:
        print("[OK] 已将批注写入飞书文档（粉色标注）")
        return True
    else:
        print(f"[WARN] 写入批注失败: {result}", file=sys.stderr)
        return False


def extract_new_findings(review_result: str) -> Optional[str]:
    """
    从审查结果中提取【新发现】部分

    知识回流：将代码中发现的隐含业务规则写回需求文档。
    """
    # 提取所有 【新发现】 段落（包含标题行）
    pattern = r"(【新发现】[^\n]*\n(?:[\s\S]*?))(?=\n【|\n##|\Z)"
    matches = re.findall(pattern, review_result)

    if not matches:
        return None

    return "\n".join(m.strip() for m in matches if m.strip())


# 需要过滤的临时文件模式
IGNORE_PATTERNS = {
    "__pycache__", ".pyc", ".pyo", ".pyd",
    ".git", ".svn",
    "node_modules", ".venv", "venv",
    ".DS_Store", "Thumbs.db",
    ".idea", ".vscode",
    ".iml",  # IntelliJ / PyCharm 模块文件
}

# 已知不需要审查的路径前缀
IGNORE_PREFIXES = (
    ".git/", "scripts/commit_review/__pycache__/",
)


def _should_ignore(path: str) -> bool:
    """判断文件是否应该被忽略"""
    # 检查完整路径是否匹配
    for prefix in IGNORE_PREFIXES:
        if path.startswith(prefix):
            return True
    # 检查路径片段是否匹配（如目录名）
    parts = path.replace("\\", "/").split("/")
    for part in parts:
        if part in IGNORE_PATTERNS:
            return True
    return False


def get_changed_files() -> list[str]:
    """获取 staged 的文件列表（排除临时文件）"""
    try:
        result = subprocess.run(
            ["git", "diff", "--staged", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False
        )
        if result.returncode == 0:
            files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
            filtered = [f for f in files if not _should_ignore(f)]
            if len(filtered) < len(files):
                ignored = set(files) - set(filtered)
                print(f"[INFO] 已过滤临时文件: {', '.join(sorted(ignored))}")
            return filtered
        return []
    except Exception:
        return []


def format_diff_for_review(diff: str, max_lines: int = MAX_DIFF_LINES) -> str:
    """格式化 diff，限制大小"""
    lines = diff.split("\n")
    if len(lines) > max_lines:
        return "\n".join(lines[:max_lines]) + f"\n... (共 {len(lines)} 行，已截断)"
    return diff


def fetch_openapi_spec(base_url: str = "http://localhost:8080") -> Optional[dict]:
    """
    从运行中的服务获取 OpenAPI 规范
    
    Args:
        base_url: 后端服务基础 URL
        
    Returns:
        OpenAPI 规范字典，失败返回 None
    """
    try:
        response = requests.get(f"{base_url}/v3/api-docs", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[WARN] 无法获取 OpenAPI 规范: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[WARN] 获取 OpenAPI 异常: {e}", file=sys.stderr)
        return None


def load_openapi_from_file(file_path: Path = None) -> Optional[dict]:
    """
    从文件加载 OpenAPI 规范
    
    Args:
        file_path: OpenAPI 文件路径，默认为 docs/openapi.json
        
    Returns:
        OpenAPI 规范字典，失败返回 None
    """
    if file_path is None:
        file_path = Path(__file__).parent.parent.parent / "docs" / "openapi.json"
    
    try:
        with open(file_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[WARN] OpenAPI 文件不存在: {file_path}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"[WARN] OpenAPI 文件格式错误: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[WARN] 加载 OpenAPI 文件异常: {e}", file=sys.stderr)
        return None


def extract_api_endpoints(openapi_spec: dict) -> list[dict]:
    """
    从 OpenAPI 规范提取所有 API 端点信息
    
    Args:
        openapi_spec: OpenAPI 规范字典
        
    Returns:
        端点列表，每个端点包含 method, path, operationId 等
    """
    endpoints = []
    
    for path, methods in openapi_spec.get('paths', {}).items():
        for method, details in methods.items():
            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                endpoint = {
                    'method': method.upper(),
                    'path': path,
                    'operationId': details.get('operationId', ''),
                    'summary': details.get('summary', ''),
                    'tags': details.get('tags', []),
                    'parameters': details.get('parameters', []),
                    'requestBody': details.get('requestBody', {})
                }
                endpoints.append(endpoint)
    
    return endpoints


def format_openapi_diff(before: dict, after: dict) -> str:
    """
    对比两个 OpenAPI 规范，生成差异报告
    
    Args:
        before: 修改前的 OpenAPI 规范
        after: 修改后的 OpenAPI 规范
        
    Returns:
        Markdown 格式的差异报告
    """
    lines = []
    
    # 提取端点
    before_endpoints = {f"{ep['method']} {ep['path']}" for ep in extract_api_endpoints(before)}
    after_endpoints = {f"{ep['method']} {ep['path']}" for ep in extract_api_endpoints(after)}
    
    # 检测新增的端点
    added = after_endpoints - before_endpoints
    if added:
        lines.append("### ➕ 新增接口")
        for endpoint in sorted(added):
            lines.append(f"- {endpoint}")
        lines.append("")
    
    # 检测删除的端点
    removed = before_endpoints - after_endpoints
    if removed:
        lines.append("### ➖ 删除接口")
        for endpoint in sorted(removed):
            lines.append(f"- {endpoint}")
        lines.append("")
    
    if not (added or removed):
        lines.append("### ✅ 无 API 变更")
        lines.append("")
    
    return "\n".join(lines)
