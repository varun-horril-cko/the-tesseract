# CLAUDE.md — The Tesseract

## Project Context
This is a FinTech codebase. All code, docs, and processes must reflect financial-grade quality standards: correctness, auditability, security, and regulatory awareness.

## The Tesseract — Agent Crew
This repo uses a multi-agent workflow. Each agent has a dedicated persona and system prompt in `/agents/<name>/SYSTEM.md`. Active feature plans live in `/plans/`.

| Agent       | Emoji | Role                        | When to Invoke                        |
|-------------|-------|-----------------------------|---------------------------------------|
| Odysseus    | 🫩    | Architect & Planner         | New feature ideation, plan refinement |
| Rocky       | 🪨    | Implementer                 | Writing production code               |
| Marvin      | 🤖    | QA & Test Engineer          | Tests, coverage, edge cases           |
| Babel       | 🐠    | Documentation & Diagrams    | Docs, ADRs, Mermaid diagrams          |
| Muad'Dib    | 🧿    | PR & Commit Crafter         | Commit messages, PR descriptions      |
| Ratatouille | 🐭    | Feedback Triager            | Copilot/reviewer feedback triage      |

## Conventional Commits
All commits MUST follow: `<type>(<scope>): <description>`

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`

Examples:
- `feat(payments): add idempotency key to transfer endpoint`
- `fix(ledger): correct rounding in multi-currency conversion`
- `test(auth): add MFA token expiry edge cases`

## Code Standards
- All money values use decimal/BigDecimal types — NEVER floating point
- All API endpoints require authentication and authorization checks
- All database mutations must be wrapped in transactions
- Error responses must never leak internal state or stack traces
- Logging must never include PII or credentials

## Test Standards
- Minimum 80% line coverage, enforced in CI
- All public API endpoints must have integration tests
- All business logic must have unit tests with edge cases
- Test names follow: `should <expected behavior> when <condition>`

## PR Standards
- Title matches conventional commit format
- Description includes: Summary, Motivation, Changes, Testing, Rollback Plan
- All PRs require at least one approval before merge
- Linked to a plan document in `/plans/` when applicable

## Documentation Standards
- Architecture diagrams use Mermaid syntax
- ADRs follow MADR format in `/docs/adr/`
- API docs stay in sync with implementation — never aspirational

## Agent Memory
Each agent has a persistent memory file at `memory/<agent>.md`. These accumulate learnings across sessions — codebase patterns, past decisions, gotchas, reviewer preferences, and lessons learned.

- Agents MUST read their memory file at the start of every session
- Agents SHOULD update their memory file at the end of a session when new learnings were discovered
- The engineer can trigger a memory update by saying "save memory" or "update memory"
- Memory files are version-controlled — git history provides the audit trail
- Stale entries should be pruned periodically to keep memory focused and useful
