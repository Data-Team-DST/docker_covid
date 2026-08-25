# Coding Style

## Immutability (CRITICAL)

ALWAYS create new objects, NEVER mutate existing ones:

```
// Pseudocode
WRONG:  modify(original, field, value) → changes original in-place
CORRECT: update(original, field, value) → returns new copy with change
```

Rationale: Immutable data prevents hidden side effects, makes debugging easier, and enables safe concurrency.

## Core Principles

### KISS (Keep It Simple)

- Prefer the simplest solution that actually works
- Avoid premature optimization
- Optimize for clarity over cleverness

### DRY (Don't Repeat Yourself)

- Extract repeated logic into shared functions or utilities
- Avoid copy-paste implementation drift
- Introduce abstractions when repetition is real, not speculative

### YAGNI (You Aren't Gonna Need It)

- Do not build features or abstractions before they are needed
- Avoid speculative generality
- Start simple, then refactor when the pressure is real

## File Organization

MANY SMALL FILES > FEW LARGE FILES:
- High cohesion, low coupling
- Organize by feature/domain, not by type
- Extract utilities from large modules

### Python — limites par type de fichier

The filename encodes the file's role; the role determines the acceptable line limit.
A file that exceeds its limit is a signal to split, not to raise the limit.

| Suffix / pattern | Role | Max lines | Max lines/function |
|---|---|---|---|
| `*_router.py` | FastAPI endpoints only (no business logic) | 300 | 30 |
| `*_service.py` | Business logic | 200 | 50 |
| `*_utils.py` / `*_helpers.py` | Utility functions | 200 | 40 |
| `*_constants.py` / `*_config.py` | Constants and configuration | unlimited | — |
| `test_*.py` | Tests | 500 | 60 |
| `main.py` | Entry point only | 50 | — |

**Enforcement rule**: when creating a new `.py` file, choose the suffix that matches its content.
A `router.py` that contains `_compute_similarity()` is misnamed — extract that function to `*_service.py`.

**10% margin, if justified**: a file up to 10% over its limit (router ≤330, service/utils ≤220, main ≤55)
does not force a split by itself. "Justified" means the file stays a single, coherent responsibility, and
splitting it would either fragment it artificially or force an awkward workaround of the edge=1 DI rule
(`.claude/rules/python/import_cascade.md` R12) just to shave a few lines. It is not a blank check — a file
inside the margin that mixes multiple responsibilities is still a split candidate, and a file beyond the
margin (e.g. +40L) gets a real split, not a bigger margin. Compute the margin precisely (`limit × 1.10`,
rounded down) before calling a file "justified" — eyeballing it ("223L, close enough") is how a genuinely
over-limit file gets waved through by mistake.

## Error Handling

ALWAYS handle errors comprehensively:
- Handle errors explicitly at every level
- Provide user-friendly error messages in UI-facing code
- Log detailed error context on the server side
- Never silently swallow errors

## Input Validation

ALWAYS validate at system boundaries:
- Validate all user input before processing
- Use schema-based validation where available
- Fail fast with clear error messages
- Never trust external data (API responses, user input, file content)

## Naming Conventions

- Variables and functions: `camelCase` with descriptive names
- Booleans: prefer `is`, `has`, `should`, or `can` prefixes
- Interfaces, types, and components: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Custom hooks: `camelCase` with a `use` prefix

## Code Smells to Avoid

### Deep Nesting

Prefer early returns over nested conditionals once the logic starts stacking.

### Magic Numbers

Use named constants for meaningful thresholds, delays, and limits.

### Long Functions

Split large functions into focused pieces with clear responsibilities.

## Code Quality Checklist

Before marking work complete:
- [ ] Code is readable and well-named
- [ ] Functions are small (see limit by file type above)
- [ ] File respects its type limit (router ≤300, service ≤200, test ≤500…)
- [ ] Filename suffix matches actual content (`_router` = endpoints only, `_service` = logic…)
- [ ] No deep nesting (>4 levels)
- [ ] Proper error handling
- [ ] No hardcoded values (use constants or config)
- [ ] No mutation (immutable patterns used)
