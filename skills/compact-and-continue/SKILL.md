---
name: compact-and-continue
description: Compress the current Codex task into a concise, self-contained handoff and create a fresh user-owned Codex task in the same project to continue. Use when the user says the context is too long, wants to reduce token usage, asks to compact or summarize and continue in a new chat/task, or explicitly invokes $compact-and-continue, including Chinese requests such as “压缩上下文”“开新任务继续”“上下文太长了”.
---

# Compact and Continue

Transfer the active work into a fresh Codex task with the minimum context needed to continue safely and correctly.

## Workflow

1. Treat invocation as explicit authorization to create one new user-owned Codex task. Do not spawn a subagent.
2. Inspect the current task and workspace state. Resolve obvious facts from files or read-only checks instead of asking the user to restate them.
3. Write a compact, self-contained handoff containing only:
   - Current objective and intended outcome
   - Relevant workspace, directories, files, branches, and artifacts
   - Completed work and verification results
   - Decisions, constraints, and durable user preferences that still apply
   - Current blockers, risks, and unresolved questions
   - Exact next action to take
4. Remove conversational filler, repeated explanations, superseded requests, raw logs, lengthy tool output, and failed attempts unless a failure prevents repeating a known mistake. Never include secrets or credentials.
5. Keep the handoff proportional to the task. Target 600–1200 Chinese characters or 400–800 English words; exceed this only when omission would make continuation unsafe or incorrect.
6. Build the new task's initial prompt using this form:

   ```text
   继续下面的任务。把这份交接摘要和当前工作区状态作为事实来源；从“下一步”直接开始，不要重新执行已经完成的工作。只读取当前步骤必需的文件和内容，保持后续上下文精简。

   <handoff>
   目标：...
   工作区与关键文件：...
   已完成与验证：...
   有效决策与约束：...
   阻塞与风险：...
   下一步：...
   </handoff>
   ```

7. Search for and use the available Codex task/thread creation tool, normally `create_thread`, preserving the current project or workspace when the tool supports it. Give the new task a short title derived from the objective.
8. If creation is asynchronous, use the available task-waiting mechanism to confirm that the new task was accepted or to surface an immediate request for attention. Do not wait for the entire transferred task to finish.
9. After successful creation, return the new task link or product-provided task directive and stop substantive work in the old task.

## Boundaries

- Do not run `/compact` before creating the new task; a fresh task already removes the old transcript from model-visible context, while premature compaction may discard handoff details.
- Do not copy the full transcript into the new task.
- Do not create or update a handoff file in the user's repository unless explicitly requested.
- Do not silently broaden the objective or authorize new external actions.
- If no task-creation tool is available or creation fails, state that clearly and return the complete handoff prompt in a fenced block for the user to paste into a new task manually.
