---
name: plain-writing
description: Writing rules for prose that ships with the code or that other agents read. Use when writing or editing code comments and doc blocks, commit messages, pull request titles and descriptions, review comments, issues, changesets, release notes, documentation, ADRs, interface text (labels, captions, hints, empty states), or roadmap briefs and outcomes. Keeps text short, plain, dense with facts, free of metaphors, stock phrases and em-dashes, and easy for both people and agents to scan. Includes a checker script and an optional hook that blocks commits and PRs with violations.
---

# Plain writing

Write text that a person can read in one pass and an agent can act on without guessing. Both readers want the same thing: the fact they need, early, in exact words, with nothing to skip over.

Apply this to any prose that ships with the code or that another agent will read:

- code comments and commit messages
- pull request titles, descriptions and review comments
- issues, changesets and release notes
- documentation and decision records
- roadmap briefs and outcomes

## Rules

### Short and plain

- Cut words that add no information. Prefer the shorter word.
- Keep one idea per sentence. Keep sentences under about 25 words.
- Write direct sentences. Avoid jargon when a plain word works.
- Say what the change does and why. Skip the story of how you got there.

### No figures of speech

- Never use a metaphor. Say what the thing does instead of comparing it to something else. This covers figures of speech, personified code, and imagery borrowed from another field. Literary phrasing goes with them.
- Never use stock or marketing phrases (`seamless`, `robust`, `leverage`, `powerful`, `under the hood`). They take space and say nothing specific.

### Punctuation and lists

- Never use an em-dash. Do not use an en-dash or a double hyphen as a substitute. End the sentence with a period and start a new one.
- Write multiple points as a list. Each item is one plain sentence, or a few short sentences.
- Do not join points with dashes, colons or semicolons.

### Exact facts

- Give a number instead of an adjective. "23% fewer allocations on the `bench:render` suite", not "significantly faster". Say how it was measured.
- Put code identifiers, paths, commands and flags in backticks.
- Use the same term for the same thing every time. Do not switch between synonyms for variety. A reader, and especially an agent, will assume two words mean two things.
- Name the thing instead of using "it", "this" or "that" when the sentence before has more than one candidate.
- Never write `JavaScript`. Leave it out, or name the specific thing instead, such as the file type (`.js`) or the code block language (`js`).

### Shape for scanning

- Lead with the sentence the reader needs most: the result, the decision, or the action.
- Front-load each line. Put the key word at the start of a list item, so a reader scanning the left edge finds it.
- Use a table when you compare items across the same attributes. Use a list for steps or independent points. Use prose only for reasoning that does not split into points.
- Use sentence-case headings. No emoji. No bold for emphasis inside sentences. Bold is fine as a label at the start of a list item.

## Follow the repo first

Before writing, look at how the repo already writes:

- `git log -20 --format=%s` for the commit subject style.
- `.changeset/`, `CHANGELOG.md` or release notes for the changelog style.
- Two or three existing docs or decision records for headings and voice.

Match those conventions. When a convention conflicts with a rule above:

- Follow the convention for format: prefixes, heading levels, templates.
- Follow the rules for wording: no metaphors, no dashes, no stock phrases.

## Writing that agents read

Briefs, outcomes, review comments and PR descriptions are often read by another agent with none of your context. The rules above still apply, with these additions:

- Make each file stand on its own. Never write `as discussed`, `the issue above` or `see conversation`. Restate the fact or link to the file that holds it.
- Use exact paths, names, commands and numbers. An agent cannot ask what "the config file" means.
- State what is done, what is not done, and what is uncertain, in separate lists. Agents act on what they read as settled.
- Completeness beats brevity here, but only for facts. Leave out narration, apologies and summaries of the summary.
- Put the action or decision the reader must take in the first lines.

## Format by artifact

**Code comments.** See "Code comments" below.

**Interface text.** See "Interface text" below.

**Commit messages.** Use the repo's convention, such as `type(scope): summary`. Keep the summary in the imperative and under 72 characters. Put extra detail in the body as a list of sentences.

**Pull request descriptions.** Use these sections, and drop any that do not apply:

```
<One or two sentences: what changes and why.>

## Changes
- <one sentence per change>

## Proof
- Fails on `<base>`: `<command>` (<result>)
- Passes on this branch: `<command>` (<result>)

## Roadmap
- <node id and roadmap path, or "none">

## Cost
- <bundle size, runtime, dependencies, migrations; numbers where measured>

## Risk
- <what could break, and how it is covered>
```

**Review comments.** One problem per comment. State the problem, the evidence (file and line, a failing command, a number), and what would resolve it. Mark nits as nits.

**Issues.** Start with what happens and what should happen. Then the steps to reproduce, as a numbered list with exact commands. Then the environment.

**Changesets and release notes.** Write one or two sentences a user of the package understands. Describe the visible effect, not the internal refactor. The changesets skill has the bump rules.

**Documentation.** Lead with the sentence the reader needs most. Use lists for steps and options. Show a short example instead of describing one.

**Decision records.** Context, decision, consequences, alternatives. Each as short lists. Put the decision in the first sentence of its section.

## Code comments

A comment earns its place by saying something the code cannot. Write it short, write the reason, and stop.

- **Length.** Most blocks are one to four lines. A block over about eight lines needs a real reason: a formula, a protocol, a subtle invariant, a module header.
- **Say the why.** The non-obvious reason, the constraint, the trap. Never restate the signature or the next line in prose.
- **No history.** Cut "it used to", "this replaced", "that is what was wrong with". The old design is in git; the comment describes what is here now.
- **No build-up.** State the point once. Cut the second example that makes the same case as the first.
- **One idea per block.** A doc block with three paragraphs about three things means the code does too much, or two of them belong next to the code they are about.
- **Keep verbatim**: lint directives, external links, formulas, and any warning that prevents a bug or data loss.
- **Doc blocks** on exported functions, types and constants say what the thing is and the one thing a caller could get wrong, not how it works inside. Interface fields get one line each, unless the field carries a rule (a default, a stored-empty convention, a value that must never be trusted).
- **Inline comments** explain a line that looks wrong but is right. If the code is plainly readable, delete the comment instead of writing one.
- **Light is not cryptic.** Full sentences, no shorthand, no references nobody can resolve ("the fix", a bare ticket number).

```ts
// Avoid: says what the line says
// Loop over every unit on the field and add it to the list
for (const unit of battle.units()) { ... }

// Prefer: says what a reader would get wrong
// Copied first: the effect adds units mid-iteration, and a live
// view would visit whatever it added
for (const unit of [...battle.units()]) { ... }
```

## Interface text

One label per thing. The layout says the rest. Where a control sits, what it sits beside and how it is grouped already tell the user what it is for. A second line that repeats that in words is one more thing to read before the screen can be used.

- **No subtitle under a title** that restates it.
- **No caption on a self-evident control.** A `Bid` button beside a price needs no "Place a bid on this item" under it.
- **No section heading over a single group.** A heading earns its place only when there are several groups to tell apart.
- **No hint that names the obvious gesture**, such as "Click to select" on something that highlights on hover.
- **Group, align and order instead of explaining.** Related things sit together, the way out and the main action keep fixed places, and the most important value is the largest. If a screen only reads with a paragraph of help, fix the layout instead of writing the paragraph.

What still gets words:

- A label the control cannot carry itself: an icon-only button keeps its tooltip and its `aria-label`.
- A consequence the user cannot see from the layout: an action that cannot be undone, a cost, a cooldown.
- An empty state, which has no layout to read.

## Check before you send

Run the checker on what you wrote:

```bash
python3 <skill>/scripts/check_prose.py FILE...            # Markdown and text
python3 <skill>/scripts/check_prose.py --comments FILE... # comments in source files
python3 <skill>/scripts/check_prose.py --commit origin/main..HEAD
echo "text" | python3 <skill>/scripts/check_prose.py -
python3 <skill>/scripts/check_prose.py --list            # all rules and phrases
```

Errors (dashes, stock phrases, metaphors from the list, wordy phrases, long commit subjects) must be fixed. Warnings (long sentences, filler, hedges, size claims without numbers, semicolons) are worth a look. The checker skips code blocks and inline code.

The checker cannot find every metaphor. After it passes, reread once and ask of each sentence: does it say what the thing does, or what it is like?

Then a last pass:

- Delete the first sentence if it only introduces the second.
- Delete the last sentence if it only repeats the first.
- Check that each list item holds one point.

## The hook

`scripts/hook.py` is a Claude Code `PreToolUse` hook. It checks the text of `git commit -m/-F` and of `gh pr` and `gh issue` titles and bodies before the command runs. Set `PLAIN_WRITING_HOOK=block` to stop commands whose text has errors, or `warn` to only log them. It does nothing when the variable is unset. The plugin registers the hook. With a manual install, add it to `settings.json` yourself.

## Examples

Avoid:

```
// This helper walks the module graph — collecting every reachable binding —
// so that later passes can decide what is safe to drop.
```

Prefer:

```
// Walks the module graph and collects every reachable binding.
// Later passes use this to decide what is safe to drop.
```

Avoid a changeset like:

```
Refactored the optimize pipeline internals to introduce a new reachability
pass — this unlocks better tree-shaking across all targets.
```

Prefer:

```
Dead code is now removed from compiled output.
Unused imports and unreferenced locals are dropped.
```

Avoid a metaphor, however small:

```
// The cache is the gatekeeper: nothing reaches the network without its
// blessing.
```

```
The scheduler now breathes between batches, so the queue never drowns.
```

Prefer plain terms:

```
// Every network request is served from the cache first, and only a miss
// reaches the network.
```

```
The scheduler waits 50ms between batches, so the queue has time to drain.
```

Avoid vague size claims:

```
This makes rendering significantly faster and the bundle much smaller.
```

Prefer numbers with their source:

```
Rendering 1,000 rows takes 41ms instead of 63ms (`pnpm bench render`).
The client bundle shrinks from 14.2kB to 12.9kB gzipped.
```

Avoid text that needs the conversation to make sense:

```
Fixed the issue we talked about. Also did the other thing from before.
```

Prefer text that stands alone:

```
Fix session tokens expiring one hour early in UTC+1 and later.
Also remove the unused `legacyAuth` flag from `config.ts`.
```
