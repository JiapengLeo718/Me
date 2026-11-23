#!/usr/bin/env python3
"""Generate a deterministic Markdown catalog of personal Codex skills."""

from __future__ import annotations

import argparse
import ast
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DEFAULT_ROOTS = (Path.home() / ".codex/skills", Path.home() / ".agents/skills")
DEFAULT_OUTPUT = Path('skill-catalog.md')


@dataclass(frozen=True)
class Skill:
    name: str
    display_name: str
    purpose: str
    triggers: str
    invocation: str
    source_root: str
    skill_file: Path
    source_file: Path
    modified: str


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        try:
            parsed = ast.literal_eval(value)
            return str(parsed)
        except (SyntaxError, ValueError):
            return value[1:-1]
    return value


def parse_simple_yaml(text: str, frontmatter: bool = False) -> dict[str, str]:
    lines = text.splitlines()
    if frontmatter:
        if not lines or lines[0].strip() != "---":
            return {}
        try:
            end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
        except StopIteration:
            return {}
        lines = lines[1:end]

    result: dict[str, str] = {}
    index = 0
    while index < len(lines):
        match = re.match(r"^\s*([A-Za-z0-9_-]+):\s*(.*)$", lines[index])
        if not match:
            index += 1
            continue
        key, raw = match.groups()
        if raw in {"|", ">", "|-", ">-", "|+", ">+"}:
            chunks: list[str] = []
            index += 1
            while index < len(lines) and (not lines[index].strip() or lines[index][:1].isspace()):
                chunks.append(lines[index].strip())
                index += 1
            result[key] = ("\n" if raw.startswith("|") else " ").join(chunks).strip()
            continue
        result[key] = unquote(raw)
        index += 1
    return result


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_description(description: str) -> tuple[str, str]:
    description = normalize_space(description)
    patterns = (
        r"\bUse when\b",
        r"\bUse for\b",
        r"\bUse this skill when\b",
        r"用户提到",
        r"当用户",
        r"用于[“\"]",
    )
    matches = [re.search(pattern, description, flags=re.IGNORECASE) for pattern in patterns]
    matches = [match for match in matches if match]
    if not matches:
        return description, ""
    first = min(matches, key=lambda match: match.start())
    return description[: first.start()].rstrip(" ;；。"), description[first.start() :].strip()


def source_label(root: Path) -> str:
    home = Path.home()
    try:
        return "~/" + str(root.relative_to(home))
    except ValueError:
        return str(root)


def load_skill(skill_file: Path, root: Path) -> Skill | None:
    try:
        text = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    metadata = parse_simple_yaml(text, frontmatter=True)
    name = normalize_space(metadata.get("name", ""))
    description = normalize_space(metadata.get("description", ""))
    if not name or not description:
        return None

    ui_file = skill_file.parent / "agents/openai.yaml"
    ui = {}
    if ui_file.is_file():
        try:
            ui = parse_simple_yaml(ui_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            ui = {}

    purpose, triggers = split_description(description)
    display_name = normalize_space(ui.get("display_name", "")) or name.replace("-", " ").title()
    short_description = normalize_space(ui.get("short_description", ""))
    invocation = normalize_space(ui.get("default_prompt", "")) or f"使用 ${name} 处理相关任务。"
    if short_description:
        purpose = short_description
    if not triggers:
        triggers = f"显式调用 ${name}；或请求与上述功能明显匹配时自动触发。"

    try:
        source_file = skill_file.resolve()
    except OSError:
        source_file = skill_file.absolute()
    modified_dt = datetime.fromtimestamp(source_file.stat().st_mtime).astimezone()
    return Skill(
        name=name,
        display_name=display_name,
        purpose=purpose,
        triggers=triggers,
        invocation=invocation,
        source_root=source_label(root),
        skill_file=skill_file.absolute(),
        source_file=source_file,
        modified=modified_dt.strftime("%Y-%m-%d %H:%M %Z"),
    )


def discover(roots: list[Path]) -> list[Skill]:
    skills: list[Skill] = []
    seen_targets: set[Path] = set()
    for root in roots:
        root = root.expanduser().absolute()
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir(), key=lambda path: path.name.casefold()):
            if child.name.startswith("."):
                continue
            skill_file = child / "SKILL.md"
            if not skill_file.is_file():
                continue
            try:
                target = skill_file.resolve()
            except OSError:
                target = skill_file.absolute()
            if target in seen_targets:
                continue
            seen_targets.add(target)
            skill = load_skill(skill_file, root)
            if skill:
                skills.append(skill)
    return sorted(skills, key=lambda item: (item.display_name.casefold(), item.name.casefold()))


def md_escape(text: str) -> str:
    return normalize_space(text).replace("|", "\\|")


def find_vault_root(catalog_path: Path) -> Path | None:
    for candidate in catalog_path.expanduser().absolute().parents:
        if (candidate / ".obsidian").is_dir():
            return candidate
    return None


def file_reference(skill: Skill, catalog_path: Path) -> str:
    vault_root = find_vault_root(catalog_path)
    if vault_root:
        try:
            skill.source_file.relative_to(vault_root)
        except ValueError:
            pass
        else:
            relative = os.path.relpath(skill.source_file, start=catalog_path.expanduser().absolute().parent)
            return f"[SKILL.md](<{Path(relative).as_posix()}>)"
    return f"`{source_label(skill.source_file)}`"


def render(skills: list[Skill], roots: list[Path], catalog_path: Path) -> str:
    latest = max((skill.modified for skill in skills), default="无")
    lines = [
        "---",
        "type: moc",
        "status: active",
        "created: 2026-08-30",
        "source: personal-skill-catalog",
        "tags:",
        "  - system/skills",
        "---",
        "",
        "# 个人 Skill 手册",
        "",
        "> 此文件由 `personal-skill-catalog` 自动生成，请勿手工编辑。知识库中的 Skill 源文件是唯一事实来源；AI 加载入口可以是符号链接。",
        "",
        f"- Skill 数量：**{len(skills)}**",
        f"- 最新技能文件时间：{latest}",
        "- 扫描位置：" + "、".join(f"`{source_label(root.expanduser().absolute())}`" for root in roots),
        "",
        "## 快速清单",
        "",
        "| 调用名 | 显示名称 | 核心功能 | 源文件 |",
        "|---|---|---|---|",
    ]
    for skill in skills:
        lines.append(
            f"| `${skill.name}` | {md_escape(skill.display_name)} | {md_escape(skill.purpose)} | {file_reference(skill, catalog_path)} |"
        )

    lines.extend(["", "## 详细信息", ""])
    for skill in skills:
        lines.extend(
            [
                f"### {skill.display_name} (`${skill.name}`)",
                "",
                f"- **功能：** {skill.purpose}",
                f"- **触发条件：** {skill.triggers}",
                f"- **推荐调用：** `{skill.invocation.replace('`', '')}`",
                f"- **扫描来源：** `{skill.source_root}`",
                f"- **AI 加载入口：** `{source_label(skill.skill_file)}`",
                f"- **更新时间：** {skill.modified}",
                f"- **源文件：** {file_reference(skill, catalog_path)}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def atomic_write(path: Path, content: str) -> bool:
    path = path.expanduser().absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if path.read_text(encoding="utf-8") == content:
            return False
    except FileNotFoundError:
        pass
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    os.replace(temp_path, path)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", type=Path, help="Skill root to scan; repeat to add roots")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Markdown catalog path")
    parser.add_argument("--quiet", action="store_true", help="Suppress normal output")
    args = parser.parse_args()

    roots = args.root or list(DEFAULT_ROOTS)
    skills = discover(roots)
    changed = atomic_write(args.output, render(skills, roots, args.output))
    if not args.quiet:
        state = "已更新" if changed else "无需更新"
        print(f"{state}：{args.output.expanduser().absolute()}（{len(skills)} 个 Skill）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
