---
name: personal-skill-catalog
description: Scan the user's personal Codex skill roots and maintain an up-to-date Markdown catalog containing each skill's name, display name, purpose, trigger conditions, invocation example, source path, and modification time. Use when the user asks what personal skills exist, where their skills are stored, wants a skill inventory or directory, asks to refresh the personal skill list, or explicitly invokes $personal-skill-catalog, including “我的技能有哪些”“个人 Skill 列表”“更新技能目录”.
---

# Personal Skill Catalog

Maintain a deterministic inventory of the user's standalone personal skills.

## Workflow

1. Run `scripts/update_catalog.py` with the system Python. Do not reconstruct the catalog manually.
2. Read the generated catalog path printed by the script.
3. Summarize additions, removals, or notable metadata gaps when relevant; otherwise link to the catalog and report the current count.
4. If a skill lacks `agents/openai.yaml`, retain it in the catalog and derive its display name and invocation example from `SKILL.md`.
5. Treat the live skill files as the source of truth. Never edit another skill merely to make the catalog prettier unless the user explicitly requests that repair.

## Defaults

- 扫描 `~/.codex/skills` 和 `~/.agents/skills`，也可通过 `--root` 指定目录。
- 识别符号链接并去重。若输出位于 Obsidian 知识库中，库内文件会使用相对链接。
- 默认将目录写到当前路径的 `skill-catalog.md`。在 Skill 目录中可以运行：

```bash
python3 scripts/update_catalog.py --output ./skill-catalog.md
```

实际生成的目录可能包含本机路径及私有 Skill 的描述，仅用于本地整理，不要直接公开。
