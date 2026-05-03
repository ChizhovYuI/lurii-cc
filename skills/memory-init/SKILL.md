---
name: memory-init
description: First-time interactive setup of the `memory/` folder for a new clone or blank install. Picks an investor archetype, asks structured questions with template-driven option lists, and writes five memory files with YAML frontmatter per the schema in `memory/README.md`. Use when `memory/` is missing, empty, or the user invokes /memory-init or asks to "initialize memory", "set up memory", "bootstrap memory".
---

# Memory Init

Interactive onboarding. Mechanism only — option lists come from `templates/<archetype>.yaml`. The skill asks one question per turn, collects answers, then writes five frontmatter-keyed memory files plus the CHANGELOG seed.

## Guard

Read the state of `memory/` first.

- Missing or only `README.md` / `CHANGELOG.md` → proceed.
- Any of `profile.md`, `targets.md`, `platforms.md`, `patterns.md`, `on-horizon.md` already has non-trivial content → halt and confirm with `AskUserQuestion`. Options: `overwrite`, `extend`, `abort`. Default recommendation: **abort** — route to `memory-curator` for incremental updates.

## Tool rules

- One question per turn via `AskUserQuestion`. 2–4 options each. The tool auto-provides "Other" (free text).
- Numeric answers: surface 3 plausible ranges from the template; "Other" lets the user enter exact values.
- Never invent. Skipped fields land as `null` in frontmatter so skills can detect missing config.
- Question wording: terse and structural. Translate option labels to the chosen `output_language` after Block D.

## Step 0 — Pick archetype

Single `AskUserQuestion`. Options are the three archetype files in `templates/`:

- `equity-heavy` — index/ETF investor; equities-first; modest crypto
- `crypto-native` — crypto-first; BTC/ETH core; stablecoin yield
- `mixed` — balanced multi-asset; ETFs + stocks + crypto + yield

Read the chosen `templates/<archetype>.yaml`. All subsequent option lists come from this file.

## Steps 1-5 — Blocks A–E

Iterate the field tables in `references/block-fields.md`, one block per step, one `AskUserQuestion` per field. The reference covers Block A (`profile.md`), Block B (`targets.md`), Block C (`platforms.md`), Block D (`patterns.md`), Block E (`on-horizon.md`) — each row maps a frontmatter field to its option source under `templates/<archetype>.yaml`.

For Block D's `clarification_triggers`, offer the catalog in `references/clarification-triggers.md` as a multiSelect.

After Block D, switch all subsequent option labels and confirmation prompts to the chosen `output_language`.

## Step 6 — Review and confirm

1. Show captured answers compactly: one line per top-level field group.
2. `AskUserQuestion` with options: **Write all files / Edit a section / Abort**.
3. On "Edit a section" → re-ask only that section.
4. On "Write all files" → proceed.

## Step 7 — Write

Render YAML frontmatter per the schema in `memory/README.md`, then a markdown body with section headings reflecting the captured fields. Write in this order:

1. `memory/profile.md`
2. `memory/targets.md`
3. `memory/platforms.md`
4. `memory/patterns.md`
5. `memory/on-horizon.md`
6. `memory/README.md` — only if missing
7. `memory/CHANGELOG.md` — seed entry: `## YYYY-MM-DD\n\n- **Initial scaffold:** memory/ created via memory-init using <archetype> archetype.`

## Step 8 — Closeout

Return to chat in the user's chosen `output_language`:

- Confirmation that `memory/` is populated.
- Path list of files written.
- Suggested next step: run `portfolio-advisor` for the first report, or use `memory-curator` to refine.

## Failure modes to avoid

- **Don't skip the guard.** Overwriting non-empty memory destroys curated context.
- **Don't batch questions.** One question per `AskUserQuestion` call.
- **Don't fabricate.** Skipped fields land as `null`.
- **Don't translate user free text.** Preserve exact wording.
- **Don't commit to git.** That is the user's call.
- **Don't bake new archetype-specific values into this file.** New archetypes get a new `templates/<name>.yaml`, not a SKILL.md edit.
