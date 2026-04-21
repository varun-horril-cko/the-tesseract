# The Tesseract — Workflow Orchestration

## How the Crew Works Together

```
You (Engineer)
  │
  ├─── "I want to implement feature X"
  │
  ▼
🫩 Odysseus (Architect) ── Q&A ── You ── Refine ── APPROVE
  │
  │ produces: /plans/<feature>.md (status: APPROVED)
  │
  ├──────────────────┬──────────────────┐
  │                  │                  │
  ▼                  ▼                  ▼
🪨 Rocky          🤖 Marvin          🐠 Babel
(implement)       (write tests)      (write docs)
  │                  │                  │
  ├──────────────────┘                  │
  │ (integrate: code + tests)           │
  ▼                                     │
Coverage Check (>80%)                   │
  │                                     │
  ├─────────────────────────────────────┘
  │ (merge all outputs)
  ▼
🧿 Muad'Dib (PR description + commit cleanup)
  │
  ▼
PR Submitted ──── Copilot/Reviewers ──── Feedback
  │
  ▼
🐭 Ratatouille (triage: FIX / REFINE / ACKNOWLEDGE)
  │
  ▼
🪨 Rocky (apply fixes) ── 🤖 Marvin (update tests if needed)
  │
  ▼
PR Approved & Merged
  │
  ▼
Plan status → COMPLETE
```

## Practical Execution with Claude

### Using Claude Code (CLI) — Recommended
Each agent corresponds to a Claude Code session with a project-level `CLAUDE.md` (shared) and agent-specific instructions.

**Parallel execution**: Open multiple terminals, each with different agent context:
```bash
# Terminal 1 — Rocky
cd your-repo
claude "Read agents/rocky/SYSTEM.md and the plan at plans/payment-idempotency.md. Implement the feature."

# Terminal 2 — Marvin (simultaneously)
claude "Read agents/marvin/SYSTEM.md and the plan at plans/payment-idempotency.md. Write the test suite."

# Terminal 3 — Babel (simultaneously)
claude "Read agents/babel/SYSTEM.md and the plan at plans/payment-idempotency.md. Create documentation."
```

### Using Claude.ai (Web/App)
Use separate conversations, each starting with the relevant SYSTEM.md pasted as the first message. Keep plan documents in a shared location (repo or local folder) and paste relevant sections into each conversation.

### Plan Persistence
Plans live in `/plans/` as markdown files, versioned in git. They persist until you explicitly mark them `COMPLETE` after the PR merges. This means:
- Any agent can reference the plan at any time
- The plan evolves as decisions are made during implementation
- The revision history at the bottom tracks all changes
- Git history provides full audit trail

## Status Tracking
Update the plan status as work progresses:
1. `DRAFT` — Odysseus is still gathering requirements
2. `IN_REVIEW` — Plan written, engineer is reviewing
3. `APPROVED` — Engineer signed off, implementation can begin
4. `IN_PROGRESS` — Rocky/Marvin/Babel are working
5. `COMPLETE` — PR merged, feature shipped
