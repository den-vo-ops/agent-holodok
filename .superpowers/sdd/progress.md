# SDD Progress — Holodok Agent Phase 1

Branch: phase-1-core
Plan: docs/superpowers/plans/2026-07-03-holodok-agent-core.md (Tasks 1-12 = Phase 1A)
Plan.md §1B = Phase 1B error handling (1B-1..1B-4)

## Ledger
(pending)
Task 1: complete (commit a16062d, scaffold)
Task 2: complete (commit 5abc828, config, 3 tests)
Task 3: complete (commit 1d6ae16, db, 7 tests)
Task 4: complete (commit f7ff078, auth, 2 tests)
Task 5: complete (commit 1a94f69, client, 2 tests)
Task 6: complete (commit 3269396, style, 5 tests)
Task 7: complete (commit 020c79c, rules, 5 tests)
Task 8: complete (commit 782ef81, content, 8 tests)
Task 9: complete (commit b667f6d, keyboards, 7 tests)
Task 10: complete (commit a87b6a7, handlers+main, 8 tests) [plan said 9, block has 8 — plan typo]
Task 11: complete (commit 94acb32, scheduler, 2 tests)
Task 12: complete (commit 13906ce, deploy+README) [manual smoke/VPS pending]
=> Phase 1A code complete: 49 passed. Manual Telegram smoke + VPS deploy pending (need owner creds/VPS).
Task 1B-1: complete (commit b29fd23, errors.py, 8 tests)
Task 1B-2: complete (commit 47d1f49, client error-wrap, +1 test)
Task 1B-3: complete (commit 105ca35, handlers catch LLMError, +2 tests)
Task 1B-4: complete (commit 68c6166, global aiogram error handler) [live wrong-key smoke pending]
=> Phase 1B complete: 60 passed. Behavioral check green (mapping + hidden technical text + global handler).

## Plan: 2026-07-04-reply-menu (branch groq-migration, base 9bbdaeb)
(pending)
Task 1: complete (commit 6ff4738, keyboards build_main_menu +5 label consts, +1 test, review clean)
Task 2: complete (commit 2700726, handlers menu wiring + main-menu after /start, +5 tests, 67 passed, review clean)
Minor (defer to final review): shallow assert in test_handle_menu_create_content (only checks reply_markup present) — inherited from brief.
Open item: doc updates (CLAUDE.md §2, Plan.md, spec.md §6) pending.
FINAL REVIEW: 1 Important (stale FSM state on menu-button interrupt) → fixed commit 5c5c02c (state.clear in 3 handlers, tests updated, 67 passed). 1 Minor (shallow assert) accepted.
Feature COMPLETE: commits 6ff4738, 2700726, 5c5c02c. All green.
