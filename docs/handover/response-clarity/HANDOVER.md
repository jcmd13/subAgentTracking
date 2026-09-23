# Handover: response clarity setup

Origin: cloud session "Session summary and decision clarity", 2026-09-23.

**Answer:** Add a fixed 4-line block (answer, decision, risk, done/not verified) to the top of every substantial Claude response, and apply the same decision-first structure to decks and strategy docs.
**Decision needed from you:** which of items 2 and 3 below to build next.
**Risk:** low. Short summaries hide nuance, so the block forces a "Not verified" line.
**Done / Not done / Not verified:** block text written, WSL install script written. Not yet applied anywhere. Session review was from session titles and status only; transcripts were not readable from the cloud session.

## Do on WSL (5 min)
1. `git fetch origin claude/session-summary-clarity-o3an70 && git checkout claude/session-summary-clarity-o3an70`
2. `docs/handover/response-clarity/install.sh` (appends `response-block.md` to `~/.claude/CLAUDE.md`, skips if already there)
3. Paste `response-block.md` into claude.ai Settings > Profile preferences so cloud and chat sessions get it too.

## What the session history showed
- ~50 cloud sessions in 4 weeks; 9 idle, not finished (IT roadmap, CUI/NIST, WI-720, TOC-Probe, SLA config, corporate deck).
- Several auto-named sessions (`jdavislt-*`) that are hard to re-enter.
- Most work is decks and docs, so the clarity problem hits twice: reading Claude's output and producing output for management.

## Reddit options, assessed
| Method | Verdict | Use for |
|---|---|---|
| Yes/no, then explain (BLUF) | Adopt as default | Any decision question |
| TL;DR | Weak alone, drops risk and gaps | Replaced by the 4-line block |
| ELI5 / ELI18 | On demand only | Learning unfamiliar areas |
| ASD-STE100 | Strong for procedures only | AI governance procedures, work instructions, forms |
| One-page HTML visual | Good at checkpoints; can look more finished than it is | Parking or re-entering a long session |

## Decks and docs
- Exec slides: one slide per decision, title states the conclusion, body is ask / why now / options / risk / cost. 3 slides plus appendix.
- Strategy docs: 1-page decision brief (BLUF, option/cost/risk/owner table, "changed since last version" box), detail in appendix.
- Procedures: STE rules. One action per sentence, active voice, <=20 words, one term per concept.

## Open items
1. Response block: applied via install.sh + claude.ai preferences (above).
2. `/brief` user-level skill (`~/.claude/skills/brief/`) that renders the 4-line block or a one-page HTML recap of a session, branch, or doc. Not built.
3. Decision-brief and 3-slide exec templates, demonstrated on the IT roadmap. Not built. Needs the roadmap content and the CFAN PPTX template from the laptop.
