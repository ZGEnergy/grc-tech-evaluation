# Workaround Classification

When a test requires a workaround to pass, classify its durability using one of
three classes. The classification directly affects grading.

## Durability Classes

### Stable

**Definition:** Uses documented public API in a non-obvious way; unlikely to break
on version upgrade.

**Indicators:**
- Method/function is in the official API documentation
- Uses public attributes (no leading underscore)
- The approach is mentioned in examples, tutorials, or GitHub discussions by maintainers
- Works across multiple recent versions

**Examples:**
- Using a documented callback mechanism for a purpose not shown in examples
- Combining two public API calls in a sequence to achieve a result that has no single-call equivalent
- Using a documented but rarely-used parameter

**Grade impact:** B-level grades. A stable workaround for one sub-question does not
prevent a B+ if everything else is strong.

### Fragile

**Definition:** Depends on undocumented internals or private attributes; could break
on a minor version bump.

**Indicators:**
- Accesses attributes with leading underscore (`_internal_state`)
- Relies on internal data structures not in the API docs
- Found by reading source code, not documentation
- Works on current version but no backward-compatibility guarantee
- Requires specific import paths into internal modules

**Examples:**
- Directly modifying an internal solver state object
- Accessing an undocumented attribute to extract shadow prices
- Monkey-patching an internal method to change behavior
- Relying on a specific internal data structure layout

**Grade impact:** B- to C+ range. Multiple fragile workarounds push toward C.

### Blocking

**Definition:** Requires forking the source, patching, or is simply not achievable
with the tool.

**Indicators:**
- No API path exists (public or private) to achieve the goal
- Would require modifying the tool's source code
- Feature is architecturally impossible without major changes
- Attempted and failed even with internal access

**Examples:**
- Tool has no graph representation and cannot expose one
- Solver interface is hard-coded with no swap mechanism
- Model reconstruction is required per contingency (no in-place modification)

**Grade impact:** C or below. A blocking workaround on a core sub-question likely
results in C for the criterion.

## Classification Decision Tree

```
Can you achieve the test goal?
├── No → BLOCKING
└── Yes
    ├── Using only documented public API?
    │   ├── Yes → Not a workaround (no classification needed)
    │   └── In a non-obvious way → STABLE
    └── Using undocumented internals?
        ├── Yes → FRAGILE
        └── Requires source modification → BLOCKING
```

## Recording in Result Files

In the result file's YAML frontmatter:

```yaml
workaround_class: stable|fragile|blocking|null
```

In the Workarounds section:

```markdown
## Workarounds

- **What:** <description of what was done>
- **Why:** <what limitation necessitated it>
- **Durability:** <class> — <rationale for classification>
- **Grade impact:** <how this affects the criterion grade>
- **Version tested:** <tool version where workaround was verified>
```

## Multiple Workarounds

If a single test requires multiple workarounds, the overall classification is the
**worst** (most fragile) of the individual classifications:
- stable + stable = stable
- stable + fragile = fragile
- anything + blocking = blocking

## Edge Cases

- **Companion package:** If the workaround uses an official companion package (e.g.,
  PowerModelsAnnex.jl), it's **not a workaround** — it's part of the tool ecosystem.
  Note it but don't classify.

- **Third-party package:** If the workaround uses a non-official third-party package,
  classify as **stable** (the API is documented) but note the external dependency.

- **Configuration-only:** If the workaround is a non-obvious solver configuration
  (e.g., specific Ipopt options for convergence), classify as **stable** — solver
  configuration is expected.
