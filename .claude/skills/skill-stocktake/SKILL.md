---
name: skill-stocktake
description: "Use when auditing Claude skills and commands for quality. Supports Quick Scan (changed skills only) and Full Stocktake modes with sequential subagent batch evaluation."
origin: ECC
---

# skill-stocktake

Slash command (`/skill-stocktake`) that audits all Claude skills and commands using a quality checklist + AI holistic judgment. Supports two modes: Quick Scan for recently changed skills, and Full Stocktake for a complete review.

## Scope

The command targets the following paths **relative to the directory where it is invoked**:

| Path | Description |
|------|-------------|
| `~/.claude/skills/` | Global skills (all projects) |
| `{cwd}/.claude/skills/` | Project-level skills (if the directory exists) |

**At the start of Phase 1, the command explicitly lists which paths were found and scanned.**

### Extended scope — agents/ and rules/ (project-level periodic audit)

`scan.sh`/`quick-diff.sh` only enumerate `.claude/skills/` — they were never
generalized to other frontmatter shapes. For a periodic (every 3-6 months)
audit of a project's full `.claude/` tooling, also cover these two paths, but
via direct enumeration (Read/Glob) rather than the skills scripts, since the
volume is small enough not to need a caching script and the frontmatter
differs (agents: `name`/`description`/`tools`/`model`; rules: often a
`paths:` list, sometimes no frontmatter at all):

| Path | Description |
|------|-------------|
| `{cwd}/.claude/agents/` | Project-level agent definitions |
| `{cwd}/.claude/rules/**/*.md` | Project-level auto-loaded rules |

Run these two extra paths through the same Phase 2 checklist (below,
including the concrete-dependency check) and fold their verdicts into the
same Phase 3 summary table and Phase 4 consolidation — one report, not a
second parallel audit. Skip this extended scope on a routine Quick Scan;
reserve it for the periodic full pass (see "Periodic full-tooling audit"
below).

### Targeting a specific project

To include project-level skills, run from that project's root directory:

```bash
cd ~/path/to/my-project
/skill-stocktake
```

If the project has no `.claude/skills/` directory, only global skills and commands are evaluated.

## Modes

| Mode | Trigger | Duration |
|------|---------|---------|
| Quick Scan | `results.json` exists (default) | 5–10 min |
| Full Stocktake | `results.json` absent, or `/skill-stocktake full` | 20–30 min |

**Results cache:** `~/.claude/skills/skill-stocktake/results.json`

## Quick Scan Flow

Re-evaluate only skills that have changed since the last run (5–10 min).

1. Read `~/.claude/skills/skill-stocktake/results.json`
2. Run: `bash ~/.claude/skills/skill-stocktake/scripts/quick-diff.sh \
         ~/.claude/skills/skill-stocktake/results.json`
   (Project dir is auto-detected from `$PWD/.claude/skills`; pass it explicitly only if needed)
3. If output is `[]`: report "No changes since last run." and stop
4. Re-evaluate only those changed files using the same Phase 2 criteria
5. Carry forward unchanged skills from previous results
6. Output only the diff
7. Run: `bash ~/.claude/skills/skill-stocktake/scripts/save-results.sh \
         ~/.claude/skills/skill-stocktake/results.json <<< "$EVAL_RESULTS"`

## Full Stocktake Flow

### Phase 1 — Inventory

Check `jq` is available first: `command -v jq`. `scan.sh`, `quick-diff.sh`, and
`save-results.sh` all depend on it (confirmed: `jq: command not found` on a jq-less
Windows/Git-Bash machine breaks Phase 1 outright). If `jq` is missing, skip straight to the
manual fallback below rather than running `scan.sh` and hitting the error.

Run: `bash ~/.claude/skills/skill-stocktake/scripts/scan.sh`

The script enumerates skill files, extracts frontmatter, and collects UTC mtimes.
Project dir is auto-detected from `$PWD/.claude/skills`; pass it explicitly only if needed.
Present the scan summary and inventory table from the script output:

**Manual fallback (no `jq`)**: enumerate `.claude/skills/*/SKILL.md`,
`.claude/commands/*.md`, `.claude/agents/*.md`, and `.claude/rules/**/*.md` directly with
Glob, then Read each file's frontmatter (first ~6 lines) to build the same inventory table by
hand. Confirmed viable — used successfully for a full 37-item stocktake on a jq-less machine.

```
Scanning:
  ✓ ~/.claude/skills/         (17 files)
  ✗ {cwd}/.claude/skills/    (not found — global skills only)
```

| Skill | 7d use | 30d use | Description |
|-------|--------|---------|-------------|

### Phase 2 — Quality Evaluation

Launch an Agent tool subagent (**general-purpose agent**) with the full inventory and checklist:

```text
Agent(
  subagent_type="general-purpose",
  prompt="
Evaluate the following skill inventory against the checklist.

[INVENTORY]

[CHECKLIST]

Return JSON for each skill:
{ \"verdict\": \"Keep\"|\"Improve\"|\"Update\"|\"Retire\"|\"Merge into [X]\", \"reason\": \"...\" }
"
)
```

The subagent reads each skill, applies the checklist, and returns per-skill JSON:

`{ "verdict": "Keep"|"Improve"|"Update"|"Retire"|"Merge into [X]", "reason": "..." }`

**Chunk guidance:** Process ~20 skills per subagent invocation to keep context manageable. Save intermediate results to `results.json` (`status: "in_progress"`) after each chunk.

After all skills are evaluated: set `status: "completed"`, proceed to Phase 3.

**Resume detection:** If `status: "in_progress"` is found on startup, resume from the first unevaluated skill.

Each skill is evaluated against this checklist:

```
- [ ] Content overlap with other skills checked
- [ ] Overlap with MEMORY.md / CLAUDE.md checked
- [ ] Freshness of technical references verified (use WebSearch if tool names / CLI flags / APIs are present)
- [ ] Usage frequency considered
- [ ] Concrete dependency verified present, not just judged on content (see below)
```

**Concrete-dependency check** — a file whose content is relevant on paper can
still be effectively broken. Before scoring on content alone, check whether
the file references any of these, and if so verify it actually exists on
this machine:

| Dependency type | How to check |
|---|---|
| CLI binary (`node`, `jq`, `claude`, etc.) | `which <binary>` |
| A script it shells out to | `find`/`ls` the referenced path |
| A state directory it reads/writes (`~/.claude/homunculus/`, `~/.claude/session-data/`, etc.) | `ls -d <path>` — check it was ever initialized |
| An MCP server | check `.mcp.json` for the server name |

A file whose dependency is missing gets **Retire** or **Improve** (add a
guard that fails loudly instead of silently/confusingly) — never **Keep** on
the strength of its content alone. This is a distinct failure mode from
"off-topic for this project": an off-topic file is free until invoked; a
file with a broken dependency fails in a confusing way *if* invoked, which is
a real (if low-probability) cost, not a zero one.

Verdict criteria:

| Verdict | Meaning |
|---------|---------|
| Keep | Useful and current |
| Improve | Worth keeping, but specific improvements needed |
| Update | Referenced technology is outdated (verify with WebSearch) |
| Retire | Low quality, stale, or cost-asymmetric |
| Merge into [X] | Substantial overlap with another skill; name the merge target |

Evaluation is **holistic AI judgment** — not a numeric rubric. Guiding dimensions:
- **Actionability**: code examples, commands, or steps that let you act immediately
- **Scope fit**: name, trigger, and content are aligned; not too broad or narrow
- **Uniqueness**: value not replaceable by MEMORY.md / CLAUDE.md / another skill
- **Currency**: technical references work in the current environment

**Reason quality requirements** — the `reason` field must be self-contained and decision-enabling:
- Do NOT write "unchanged" alone — always restate the core evidence
- For **Retire**: state (1) what specific defect was found, (2) what covers the same need instead
  - Bad: `"Superseded"`
  - Good: `"disable-model-invocation: true already set; superseded by continuous-learning-v2 which covers all the same patterns plus confidence scoring. No unique content remains."`
- For **Merge**: name the target and describe what content to integrate
  - Bad: `"Overlaps with X"`
  - Good: `"42-line thin content; Step 4 of chatlog-to-article already covers the same workflow. Integrate the 'article angle' tip as a note in that skill."`
- For **Improve**: describe the specific change needed (what section, what action, target size if relevant)
  - Bad: `"Too long"`
  - Good: `"276 lines; Section 'Framework Comparison' (L80–140) duplicates ai-era-architecture-principles; delete it to reach ~150 lines."`
- For **Keep** (mtime-only change in Quick Scan): restate the original verdict rationale, do not write "unchanged"
  - Bad: `"Unchanged"`
  - Good: `"mtime updated but content unchanged. Unique Python reference explicitly imported by rules/python/; no overlap found."`

### Phase 3 — Summary Table

| Skill | 7d use | Verdict | Reason |
|-------|--------|---------|--------|

### Phase 4 — Consolidation

1. **Retire / Merge**: present detailed justification per file before confirming with user:
   - What specific problem was found (overlap, staleness, broken references, etc.)
   - What alternative covers the same functionality (for Retire: which existing skill/rule; for Merge: the target file and what content to integrate)
   - Impact of removal (any dependent skills, MEMORY.md references, or workflows affected)
2. **Improve**: present specific improvement suggestions with rationale:
   - What to change and why (e.g., "trim 430→200 lines because sections X/Y duplicate python-patterns")
   - User decides whether to act
3. **Update**: present updated content with sources checked
4. Check MEMORY.md line count; propose compression if >100 lines

### Phase 5 — Decision log (extended/periodic audit only)

`results.json` is a verdict cache, not a narrative — it answers "what was
decided" but not "why," which is useless to a future audit re-litigating the
same borderline call from scratch. For any verdict that wasn't obvious from
the checklist alone (content looked relevant but a dependency was missing,
two files looked redundant but actually serve different moments of use,
initial read suggested one verdict and a full read reversed it), append a
dated entry to `.claude/ECC-TOOLING-AUDIT.md` at the project root (create it
if absent) — same format as the `reason` quality bar above: what was found,
what was checked, what alternative covers the need if retired. Skip this for
routine Quick Scans and for verdicts the checklist already makes obvious
(e.g. a skill that's a straightforward Keep with no ambiguity).

## Periodic full-tooling audit (every 3-6 months)

For a project accumulating vendored ECC tooling over time, run a **Full
Stocktake with the extended scope** (agents/ + rules/, see above) on this
cadence instead of routine Quick Scans. This is the mode that produces the
decision log — a routine Quick Scan between periodic passes stays scoped to
skills/commands only and skips Phase 5.

## Results File Schema

`~/.claude/skills/skill-stocktake/results.json`:

**`evaluated_at`**: Must be set to the actual UTC time of evaluation completion.
Obtain via Bash: `date -u +%Y-%m-%dT%H:%M:%SZ`. Never use a date-only approximation like `T00:00:00Z`.

```json
{
  "evaluated_at": "2026-02-21T10:00:00Z",
  "mode": "full",
  "batch_progress": {
    "total": 80,
    "evaluated": 80,
    "status": "completed"
  },
  "skills": {
    "skill-name": {
      "path": "~/.claude/skills/skill-name/SKILL.md",
      "verdict": "Keep",
      "reason": "Concrete, actionable, unique value for X workflow",
      "mtime": "2026-01-15T08:30:00Z"
    }
  }
}
```

## Notes

- Evaluation is blind: the same checklist applies to all skills regardless of origin (ECC, self-authored, auto-extracted)
- Archive / delete operations always require explicit user confirmation
- No verdict branching by skill origin
