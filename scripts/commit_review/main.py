#!/usr/bin/env python3
"""
Commit Review - 代码提交审查工具

用法:
    uv run python scripts/commit_review/main.py

或者通过 pre-commit hook 自动调用
"""

import sys
import io
import threading
import time
from pathlib import Path

# Windows 下设置 stdout encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 确保当前目录是项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
import os
os.chdir(PROJECT_ROOT)

# 添加 scripts 目录到 path
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from commit_review.fetcher import (
    get_staged_diff,
    get_requirements_docs,
    get_changed_files,
    get_commit_message,
    format_diff_for_review,
    write_to_lark,
    write_annotation_to_lark,
    extract_new_findings,
)
from commit_review.reviewer import review_with_claude_code, set_streaming_callback
from commit_review.config import LARK_DOC_URL, LARK_KB_DOC_URL


# 审查结果（供 spinner 线程访问）
_review_result = None
_review_meta = {}  # 存储审查上下文，供 spinner 显示

# spinner 控制标志
_spin_running = False
_spin_elapsed = 0
_spin_phase = "初始化"
_dot_frames = ["   ", ".  ", ".. ", "..."]
_thinking_last_time = 0  # 上次 thinking/text 输出时间
_output_started = False   # 是否已开始输出（停止 spinner）


def _on_thinking_token(token: str):
    """被 reviewer 调用：实时显示 thinking/text 到屏幕"""
    global _thinking_last_time, _output_started, _spin_running

    # 首次收到输出时，立即停掉 spinner
    if not _output_started:
        _output_started = True
        _spin_running = False
        print("\r" + " " * 120 + "\r", end="", flush=True)

    # reviewer 发来带前缀的 token：
    # [THINK]xxx = thinking 片段
    # [TEXT]xxx = text 片段
    # [TEXT][DEBUG]xxx = 调试信息
    if token.startswith("[THINK]"):
        thinking_text = token[7:]
        print("  💭 " + thinking_text, end="", flush=True)
        _thinking_last_time = time.time()
    elif token.startswith("[TEXT]"):
        text = token[6:]
        print(text, end="", flush=True)
        _thinking_last_time = time.time()


def _spin():
    """显示等待动画"""
    global _spin_running, _spin_elapsed, _spin_phase

    phases = [
        "正在读取变更文件",
        "正在等待 Claude 响应",
        "正在分析代码语义",
        "正在生成审查报告",
    ]
    start_time = time.time()
    i = 0
    phase_idx = 0

    while _spin_running:
        # 如果 thinking/text 刚输出（2秒内），暂停 spinner 避免覆盖
        if time.time() - _thinking_last_time < 2.0:
            time.sleep(0.5)
            continue

        _spin_elapsed = int(time.time() - start_time)
        frame = _dot_frames[i % 4]
        _spin_phase = phases[phase_idx % len(phases)]
        # 每 10 秒换一次 phase
        if i > 0 and i % 20 == 0:
            phase_idx += 1
        diff_lines = _review_meta.get("diff_lines", 0)
        file_count = _review_meta.get("file_count", 0)

        bar = f"[{_spin_elapsed}s] {_spin_phase}{frame}"
        if diff_lines:
            bar += f" ({diff_lines} 行diff / {file_count} 个文件)"

        print("\r" + bar.ljust(100), end="", flush=True)
        time.sleep(1.0)  # 1秒刷新一次，避免频繁覆盖 thinking
        i += 1

    # 停止时清除行
    print("\r" + " " * 100 + "\r", end="", flush=True)


def print_header():
    print("\n" + "=" * 60)
    print("[Review] Commit Review - 代码提交审查")
    print("=" * 60 + "\n")


def print_review_result(result: str):
    """打印审查结果"""
    print("\n" + "-" * 60)
    print("[Result] 审查结果")
    print("-" * 60)
    print(result)
    print("-" * 60)


def print_next_steps():
    """打印用户决策选项"""
    print("\n[Next] 接下来你可以：")
    print("  1. 修改代码（符合需求）→ 重新提交")
    print("  2. 更新需求文档（记录新逻辑）→ 重新提交")
    print("  3. 直接提交（认为当前实现合理）")
    print("  4. 取消提交")
    print()


def ask_write_to_lark(result: str) -> bool:
    """询问用户是否要写入飞书文档"""
    if not LARK_KB_DOC_URL:
        print("[INFO] 未配置 LARK_KB_DOC_URL，跳过知识回流")
        return False

    print("\n[Ask] 是否将审查结果写入飞书文档（知识回流）？")
    print(f"  目标文档: {LARK_KB_DOC_URL}")
    print("  输入 y 确认，其他跳过: ", end="", flush=True)

    try:
        # Windows 上用 msvcrt
        import msvcrt
        key = msvcrt.getch()
        print(key.decode() if key else '')
        return key.decode().lower() == 'y'
    except:
        # 非 Windows 上用 input
        try:
            choice = input().strip().lower()
            return choice == 'y'
        except:
            return False


def ask_write_annotation(findings: str) -> bool:
    """询问用户是否将【新发现】写入飞书文档（粉色批注）"""
    if not LARK_KB_DOC_URL:
        print("[INFO] 未配置 LARK_KB_DOC_URL，跳过批注回流")
        return False

    print(f"\n[Ask] 是否将 {findings.count(chr(10)) + 1} 条【新发现】写入飞书文档（粉色标注）？")
    print(f"  目标文档: {LARK_KB_DOC_URL}")
    print("  输入 y 确认，其他跳过: ", end="", flush=True)

    try:
        import msvcrt
        key = msvcrt.getch()
        print(key.decode() if key else '')
        return key.decode().lower() == 'y'
    except:
        try:
            choice = input().strip().lower()
            return choice == 'y'
        except:
            return False


def main():
    global _review_result

    # 检查非交互模式
    non_interactive = "--non-interactive" in sys.argv

    print_header()

    # 1. 检查是否有 staged 的变更
    diff = get_staged_diff()
    if not diff:
        print("[INFO] 没有 staged 的变更，跳过审查")
        sys.exit(0)

    # 2. 检查变更文件
    changed_files = get_changed_files()
    if not changed_files:
        print("[INFO] 没有变更的文件，跳过审查")
        sys.exit(0)

    print(f"[Files] 变更文件: {', '.join(changed_files)}")

    # 3. 读取需求文档（优先从飞书云文档）
    print(f"[Docs] 正在从飞书云文档获取需求...")
    requirements = get_requirements_docs()
    if requirements:
        print(f"[Docs] 加载了 {len(requirements)} 个需求文档")
        for name, content in requirements.items():
            print(f"   - {name} ({len(content)} 字符)")
        if "飞书需求文档" in requirements:
            print(f"   来源: {LARK_DOC_URL}")
    else:
        print("[WARN] 未找到需求文档，将进行基础审查")

    # 4. 获取 commit 消息
    commit_msg = get_commit_message()

    # 5. 格式化 diff
    formatted_diff = format_diff_for_review(diff)

    # 注入审查元数据，供 spinner 显示
    global _review_meta
    _review_meta = {
        "diff_lines": len(formatted_diff.split("\n")),
        "file_count": len(changed_files),
        "info": "",
    }

    # 6. 注册 thinking 实时显示回调
    set_streaming_callback(_on_thinking_token)

    # 7. 启动 spinner 线程，同时调用审查
    print()
    global _spin_running
    _spin_running = True
    spinner_thread = threading.Thread(target=_spin, daemon=True)
    spinner_thread.start()

    result = review_with_claude_code(
        diff=formatted_diff,
        requirements=requirements,
        changed_files=changed_files,
        commit_msg=commit_msg,
    )

    # 审查完成，停止 spinner
    _spin_running = False
    spinner_thread.join(timeout=1)
    _review_result = result

    # 7. 输出结果
    print_review_result(result)

    # 非交互模式：输出结构化信息后退出，由外部工具处理交互
    if non_interactive:
        findings = extract_new_findings(result)
        if findings:
            print("\n[ANNOTATION_FINDINGS]")
            print(findings)
            print("[/ANNOTATION_FINDINGS]")
        print("\n[REVIEW_COMPLETE]")
        return

    # 8. 知识回流：提取【新发现】，写入粉色批注
    findings = extract_new_findings(result)
    if findings:
        print(f"\n[发现] 审查中发现 {findings.count('【新发现】')} 条隐含业务规则")
        print(f"  {findings[:200]}...")
        try:
            if ask_write_annotation(findings):
                print("\n[OK] 正在写入粉色批注到飞书文档...")
                write_annotation_to_lark(LARK_KB_DOC_URL, findings)
        except Exception as e:
            print(f"\n[WARN] 批注写入失败: {e}")
    else:
        print("\n[INFO] 未发现新的隐含业务规则，跳过批注回流")

    # 9. 询问是否写入完整审查记录（可选）
    try:
        if ask_write_to_lark(result):
            print("\n[OK] 正在写入飞书文档...")
            write_to_lark(LARK_KB_DOC_URL, result, "Commit 审查记录")
    except Exception as e:
        print(f"\n[WARN] 写入飞书失败: {e}，跳过知识回流")

    print_next_steps()


if __name__ == "__main__":
    main()
