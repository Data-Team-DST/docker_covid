---
name: skill-comply
description: Visualize whether skills, rules, and agent definitions are actually followed — auto-generates scenarios at 3 prompt strictness levels, runs agents, classifies behavioral sequences, and reports compliance rates with full tool call timelines
origin: ECC
tools: Read, Bash
---

# skill-comply: Automated Compliance Measurement

Measures whether coding agents actually follow skills, rules, or agent definitions by:
1. Auto-generating expected behavioral sequences (specs) from any .md file
2. Auto-generating scenarios with decreasing prompt strictness (supportive → neutral → competing)
3. Running `claude -p` and capturing tool call traces via stream-json
4. Classifying tool calls against spec steps using LLM (not regex)
5. Checking temporal ordering deterministically
6. Generating self-contained reports with spec, prompts, and timelines

## Supported Targets

- **Skills** (`skills/*/SKILL.md`): Workflow skills like search-first, TDD guides
- **Rules** (`rules/common/*.md`): Mandatory rules like testing.md, security.md, git-workflow.md
- **Agent definitions** (`agents/*.md`): Whether an agent gets invoked when expected (internal workflow verification not yet supported)

## When to Activate

- User runs `/skill-comply <path>`
- User asks "is this rule actually being followed?"
- After adding new rules/skills, to verify agent compliance
- Periodically as part of quality maintenance

## Environment Detection

This skill shells out to a separate `claude -p` CLI binary to run scenarios
and capture tool-call traces. That binary may not be installed/reachable in
every sandbox — check availability before invoking:

```bash
command -v claude >/dev/null 2>&1 && echo "claude CLI available" || echo "claude CLI not found — this skill cannot run in this environment"
```

If `claude -p` is unavailable, do not attempt the run — report that this
skill's core mechanism is unavailable in the current environment rather than
producing a partial or fabricated compliance report. `--dry-run` mode does
**not** avoid the dependency: `scripts/spec_generator.py` and
`scripts/scenario_generator.py` both shell out to `claude -p` via
`subprocess.run` even for spec/scenario generation alone (verified by
reading both files). If `claude` is missing, `--dry-run` fails the same way
a full run would — there is no partial-functionality fallback.

## Usage

```bash
# Full run
uv run python -m scripts.run ~/.claude/rules/common/testing.md

# Dry run (no cost, spec + scenarios only)
uv run python -m scripts.run --dry-run ~/.claude/skills/search-first/SKILL.md

# Custom models
uv run python -m scripts.run --gen-model haiku --model sonnet <path>
```

## Key Concept: Prompt Independence

Measures whether a skill/rule is followed even when the prompt doesn't explicitly support it.

## Report Contents

Reports are self-contained and include:
1. Expected behavioral sequence (auto-generated spec)
2. Scenario prompts (what was asked at each strictness level)
3. Compliance scores per scenario
4. Tool call timelines with LLM classification labels

### Advanced (optional)

For users familiar with hooks, reports also include hook promotion recommendations for steps with low compliance. This is informational — the main value is the compliance visibility itself.
