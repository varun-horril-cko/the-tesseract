# Quick Reference — The Tesseract Cheatsheet

## Starting a New Feature
```
You → "odysseus: I want to implement [feature description]"
Odysseus → asks 3-5 clarifying questions
You → answer questions
Odysseus → produces /plans/<feature-slug>.md
You + Odysseus → refine until APPROVED
```

## Kicking Off Implementation (parallel)
```bash
# Terminal 1: Rocky
claude "rocky: Implement the plan at plans/<feature>.md"

# Terminal 2: Marvin
claude "marvin: Write tests for plans/<feature>.md"

# Terminal 3: Babel
claude "babel: Document plans/<feature>.md"
```

## Preparing the PR
```
You → "muaddib: Write the PR for plans/<feature>.md"
```

## Handling Review Feedback
```
You → "ratatouille: Triage these comments: [paste all]"
You → "rocky: Apply these fixes: [paste FIX items]"
```

## Memory
```
"save memory"          — tell any agent to persist learnings
"update memory"        — same thing
make memory-status     — see entry counts per agent
make memory-reset      — reset all memory to empty templates
```

## Plan Statuses
Draft → In Review → Approved → In Progress → Complete

## Conventional Commit Types
feat | fix | docs | style | refactor | test | chore | perf | ci | build

## The Crew
🫩 Odysseus    — Architect    — "No plan survives first contact, so plan better"
🪨 Rocky       — Implementer  — "I am engineer!"
🤖 Marvin      — QA           — "Life. Don't talk to me about life."
🐠 Babel       — Docs         — Translates code across all dimensions
🧿 Muad'Dib    — PR Crafter   — "The spice (git history) must flow"
🐭 Ratatouille — Triager      — "If I don't love it, I don't swallow"
