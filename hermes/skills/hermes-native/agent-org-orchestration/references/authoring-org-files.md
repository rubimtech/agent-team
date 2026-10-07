# Writing Org Control Files — corruption traps

Depth for `agent-org-orchestration`, Steps 2-3. The org layer lives in files you author
(goal doc, ORG config, mission protocol), and long prose written in one call has a
specific failure mode.

## Corruption that reports success

A long document written in a single `write_file` call can come back with a duplicated
paragraph, a repeated heading block, a run of identical lines, or a sentence spliced
into its neighbour. The write still returns `bytes_written` and `verified: true`, so
nothing in the normal signal catches it. The first symptom is usually you re-reading the
file and finding the same paragraph twice.

- **Read back head and tail** after every long write — the seams show at the extremes.
- **Count a known heading** to catch duplication faster than re-reading:
  `grep -c "^## " file` returning 3 when you wrote 2 is the tell.
- **Rewrite the whole file** when a block is duplicated. Corruption is rarely local, and
  a second patch applied onto a corrupted file is how the duplication doubles — the same
  rule as editing past a failed write twice.
- **Search for stray artifacts** after any large write: repeated tokens, or a marker
  character from another language, indicate the generator looped.

## Comment syntax must match the extension

The cheapest failure in this class, because the document is already composed when it is
refused:

| Extension | Header comment |
|---|---|
| `.md` | `>` blockquote, or none |
| `.yaml` / `.yml` | `#` |
| `.json` | none — comments do not exist |
| `.py` | `#` |

A markdown blockquote header in a `.yaml` file is a parse error on line 1. `write_file`
validates structured formats, so it is caught before the file exists — but only if you
switch the marker and resubmit the content you already have, instead of recomposing the
document from scratch.

## Prove the config parses and says what you meant

Do not eyeball a hand-written config. Load it with the real parser and print the keys
you expect:

```bash
python -c "import yaml; d=yaml.safe_load(open('ORG.yaml',encoding='utf-8'));
print(list(d)); print(d['limits']['max_cycles'])"
```

This catches a mistyped key, a wrong nesting level, and a scalar where a mapping belongs
— all of which read fine as text and all of which fail at load time in the service. For an
org config, also assert the values that carry the guardrail: the over-limit action, the
cycle cap, and the reviewer autonomy level.

## Label declarative vs enforced

A limits file written before the enforcing code lands is a **plan**. Say so inside the
file ("declarative until task N enforces this") and keep that wording in every report. A
reader who finds `on_limit: stop_and_report` in a config has no way to know whether
anything checks it — and an unenforced guardrail is worse than an absent one, because it
reads as a control that works.