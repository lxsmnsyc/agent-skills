---
name: docs-site
description: Method for planning, writing and maintaining a documentation site for a library, CLI, framework, API or app. Splits the site by what the reader needs (learn, do a task, understand, look up) into getting started, guides, concepts and reference, plus examples, troubleshooting, migration and a glossary. Gives each page type a fixed template, including the feature page (what it is, why, how it works, usage, options, limits, related) and the API reference entry. Covers navigation, code examples that run, keeping docs in step with the code, versioned docs and pages agents can read. Includes page templates, a checker script for page structure, links, orphan pages and code fences, and a review checklist. Use this skill whenever writing, restructuring, auditing or reviewing documentation, a docs site, a docs page, a README that has grown into docs, API reference, a getting started page, a migration guide or the docs part of the website/ folder, even if the user does not say "docs site". Load plain-writing with it.
---

# Docs site

A docs site fails when the reader cannot tell where to look. It also fails when one page tries to teach, instruct, explain and list options at once. This skill fixes both with one rule: every page has one type, and the type decides what the page holds and how it is shaped.

Load plain-writing along with this skill. plain-writing sets the sentence rules. This skill sets the structure.

## The four reader needs

A reader arrives with one of four needs. Each need gets its own page type and its own part of the site. The split follows the Diátaxis framework.

| Reader need | Page type | Reader's question | Shape |
|---|---|---|---|
| Learn | Tutorial | "Teach me the basics." | One path, steps that always work, a result at the end |
| Do a task | Guide | "How do I do X?" | Numbered steps toward one goal, assumes basics |
| Understand | Concept | "What is X and why does it work this way?" | Explanation, diagrams, trade-offs, no steps |
| Look up | Reference | "What does this option take?" | Complete, dry, the same shape for every entry |

Most bad pages mix two types. Signs of a mix, and the fix:

- A guide stops to explain the theory. Move the explanation to a concept page and link it in one line.
- A reference entry teaches a workflow. Move the workflow to a guide and link it.
- A tutorial offers choices ("you can also..."). Remove them. Choices go in guides.
- A concept page lists every option. Link the reference instead.
- A concept page walks through the implementation, such as compiler passes. Move it to an internals page.

"Understand" has two depths, for two readers:

- **Concepts** give a user the model they need to predict what the product does with their code.
- **Internals** explain how the implementation produces that behavior, for contributors and advanced users. See "Internals".

## Before writing

Collect these facts first. Read the repo, its README, its issues and its existing docs. Ask the user only for what those cannot answer.

- **The reader.** Who uses the product and what they already know. A library for framework authors and an app for end users need different depth.
- **The product's surface.** Public exports, CLI commands, config keys, HTTP endpoints, error codes. This is the full list the reference must cover. Read it from the entry files, the CLI parser or the API schema, not from memory.
- **The core ideas.** The three to seven ideas a reader must understand to use the product well. Examples: "signals", "islands", "the build graph". Each becomes a concept page.
- **The common tasks.** What readers try to do. Take them from issues, discussions, chat questions, Stack Overflow and the examples folder. Each frequent task becomes a guide.
- **The site generator.** What the site is built with (VitePress, Starlight, Docusaurus, brumate, a custom one) and how it builds navigation. In this user's repos, repo-setup puts the docs site in `website/`.
- **What exists.** Run the audit below before writing anything new.

## Site structure

Use this top-level navigation unless the product is too small for it (see "Small projects").

1. **Getting started.** One tutorial from nothing to a first working result in under 10 minutes. Install, the smallest useful program, and how to run it. Ends with links to the next pages.
2. **Guides.** One page per task, named by the task: "Fetch data on the server", "Deploy to Vercel", "Test components". Group them by area when there are more than about ten. See "Page order".
3. **Concepts.** One page per core idea or major feature, in prerequisite order (see "Page order"). Feature pages live here (see "The feature page").
4. **Reference.** Complete and generated from the code where possible.
   - API: one page per module or export group, one entry per export.
   - CLI: one entry per command, with every flag.
   - Configuration: every key, its type, its default and what it does.
   - Errors: every error code or message, its cause and its fix.
5. **Examples.** Complete, runnable projects or recipes, each with a link to its source. Readers copy these.
6. **Troubleshooting and FAQ.** Symptoms the reader sees, each with its cause and fix. Take entries from repeated issues.
7. **Migration.** One page per major version: what changed, why, and the steps to upgrade, with before and after code.
8. **Changelog.** Link to the generated changelog. Do not copy it by hand.
9. **Glossary.** Every term the docs use with a specific meaning, defined in one sentence and linked to its concept page.
10. **Contributing.** How to build the docs locally and the page rules from this skill, so outside writers follow them.
11. **Internals.** How the implementation works, for contributors and advanced users: stages, data flow, key modules and design decisions. Only when the project has a mechanism worth explaining, such as a compiler, a scheduler or a protocol.

### Navigation rules

- **Order by the reader's path.** Getting started before guides, basic concepts before advanced ones. Do not sort alphabetically, except inside reference.
- **Name pages by what the reader wants.** "Handle form errors", not "FormErrorBoundary". Reference pages are the exception: name them by the identifier.
- **Keep each level short.** At most about seven items per sidebar group. More means the group needs splitting.
- **One page, one type.** The type decides which section a page sits in. A page that fits two sections is two pages.
- **Link across types.** Each guide links the concepts it relies on and the reference entries it uses. Each concept links the guides that apply it. Each reference entry links one guide that uses it.
- **Stable URLs.** Paths follow the section: `/guides/deploy-vercel`, `/concepts/signals`, `/reference/api/create-signal`. When a page moves, add a redirect from the old path.
- **Search works.** The site has search as a command bar (see "Search"). Each page's title and lead sentence contain the words a reader would search for.

### Page order

Order is part of the content. A reader who follows the sidebar from top to bottom should never meet a page that needs one further down. Decide the order inside each section with these rules.

**Concepts, by prerequisite.**

1. For each concept or feature page, list the pages a reader must understand first. Write them in the frontmatter as `requires: [concepts/components.md]`, with paths relative to the page.
2. Sort so every page comes after everything it requires.
3. When two pages have no requirement between them, put first the idea the user meets first in their own code.
4. Link each required page from the page itself, in the lead or a "Before you read" line.

For a UI framework this gives an order such as components, then reactivity, then server rendering, then code splitting. A cycle in `requires:` means two ideas need each other. Merge them into one page, or move the shared part to a page both require.

**Guides, by project stage.** Group guides by when a user meets the task in a project's life:

1. Set up (install, configure, editor setup)
2. Build (the main tasks of using the product)
3. Data and integration (fetching, storage, other libraries)
4. Styling and assets, when they apply
5. Test
6. Deploy
7. Maintain (upgrade, debug, measure performance)

Drop the stages the product does not have. Inside a group, put the most frequent task first, counted from issues and questions.

**The other sections.**

- **Tutorials:** a series is numbered in its titles and paths (`1-create-a-project`), and each step's Next steps link goes to the next page first.
- **Reference:** by module in the order of the entry file, alphabetical inside a module. The lead says which.
- **Troubleshooting:** the most frequent symptom first.
- **Examples:** simplest first, then by the guide stage they match.
- **Migration:** newest version first.
- **Glossary:** alphabetical.
- **Internals:** in the order data flows through the system, so the first page covers the stage that receives the user's input.

**Keeping the order visible.**

- The sidebar is the order. Previous and next links at the bottom of each page follow it. Set them in the generator's config if it does not derive them from the sidebar.
- When the generator reads order from frontmatter, use its field (`order:`, `sidebar_position:`). The checker reads both. When the order lives in a sidebar config file, keep that file in the same order as the rules above.
- Adding a page means placing it by these rules, not appending it to the end of its group.

### Small projects

A small library does not need ten sections. Scale down in this order:

- **Under about 5 exports**: one README with a lead sentence, install, a usage example, an API section and a link to the changelog.
- **Under about 20 exports**: Getting started, one Concepts page or a few, Reference. Guides when issues show repeated tasks.
- **Larger**: the full structure.

Grow into sections when the content exists. An empty "Guides" section with one stub page is worse than no section.

## Page types

Every page starts with frontmatter that names its type, so the checker can verify its structure:

```md
---
title: Signals
type: concept
---
```

Types: `tutorial`, `guide`, `concept`, `feature`, `reference`, `troubleshooting`, `migration`, `example`, `glossary`, `internals`, `index`. A `feature` page is a concept page about one feature and sits in the Concepts section.

Every page, of any type, follows these rules:

- **Lead sentence.** The first line under the title says what the page covers, in the reader's words. No heading before it.
- **One type.** See the table above.
- **Short sections.** Headings every few paragraphs, so a reader can scan the left edge.
- **Example early.** Show code before the second heading when the page is about code.
- **Ends with links.** "Related" or "Next steps" with two to five links to other pages.

The templates in [templates/](templates/) give the headings for each type. [references/page-types.md](references/page-types.md) has the rules for each type and how to tell them apart.

## The feature page

A feature page (`type: feature`) is a concept page about one feature: what it is, why it exists and how to use it. Use [templates/feature.md](templates/feature.md). Its sections, in this order:

1. **Lead (no heading).** What the feature is, in one or two sentences. Then the smallest example that shows it working.
2. **Why.** The problem it solves, and when to reach for it. Then when not to use it, and what to use instead. A reader who should not use the feature learns that here, not after an hour of trying.
3. **How it works.** The model a reader needs to predict the feature's behavior: the parts, the order things happen in, what runs where. Use a diagram for anything with more than two steps or parts. Include what the reader can observe, such as the output the product makes from their code. Leave the implementation to an internals page and link it.
4. **Usage.** The basic case first, then the common variations, each as a short heading with an example. Each variation is something readers do, taken from issues and examples.
5. **Options.** A table of the options that matter most, with a link to the full reference entry. Do not repeat every option here.
6. **Limits and caveats.** What the feature does not do, known edge cases, performance costs with numbers, and browser or platform support.
7. **Related.** Links to guides that use the feature, the reference entries, and neighboring concepts.

Add these when they apply:

- **Compared with** a common alternative, when readers ask "why not X?". Facts in a table, not a sales pitch.
- **Migration** from the old way, when the feature replaces one.
- **Since** the version that added it, near the top.

A feature usually has three kinds of page: the feature page in concepts, its entries in reference, and guides for tasks that use it. Write all three, or plan the missing ones in the audit.

## The reference entry

Every entry on a reference page has the same shape, so a reader learns it once. Use [templates/reference.md](templates/reference.md).

- **Signature** in a code block, copied from the source or generated.
- **One-line description** of what it does.
- **Parameters**: name, type, default, required or not, and what it does. A table when there are more than two.
- **Returns**: type and what it holds.
- **Throws or errors**: each error and when it happens.
- **Example**: the shortest complete use.
- **Notes**: only facts a caller could get wrong, such as a default that surprises or a call order that matters.
- **Since** and **Deprecated**, when they apply. A deprecated entry names its replacement.
- **See also**: one guide or concept.

Generate reference from the code where the tooling allows it. Examples: TypeDoc for TypeScript, an OpenAPI schema for HTTP APIs, the CLI's own help output. Generated reference is only as good as the doc comments it reads. [references/doc-comments.md](references/doc-comments.md) maps each part of the entry to a TSDoc tag, and covers OpenAPI, CLI help and JSON Schema. Hand-written reference drifts from the code. When it must be hand-written, `docs_check.py --exports` compares it with the exports.

### Errors that link to their docs

The fastest path from a problem to its fix is a link in the error itself.

- Give each error the library throws a stable code, such as `IDLIP_E012` or `missing-key`.
- The message ends with a URL to that code's entry on the errors reference page: `See https://example.dev/reference/errors#missing-key`.
- Each errors reference entry has the message, the cause, the fix with code, and the version that added it.
- A removed error code keeps its entry with a note, because readers on old versions still see it.
- Check coverage: list the codes in the source (`grep -rhoE "<code pattern>" src | sort -u`) and confirm each has an entry. Add the check to the docs build when the pattern is stable.

## Internals

Internals pages explain the mechanism: how the implementation turns the user's input into the behavior the concept pages describe. Use [templates/internals.md](templates/internals.md).

### Concept or internals

The line is what the user can observe.

- **Concept material**: anything the user sees or must reason about. Examples: compiled output from their code, what runs on the server or the client, when a chunk loads, generated files, network requests, error messages. For a compiler, the concept page shows input code next to output code and the rules that map one to the other.
- **Internals material**: how the implementation gets there. Compiler stages, AST transforms, intermediate formats, internal data structures, module layout, and why the code is built that way.

A user must never need an internals page to use the product. When a concept page only makes sense after reading internals, the concept page is missing part of the model.

### The internals page

1. **Lead (no heading).** What the subsystem does, in one or two sentences, and who the page is for.
2. **Notice.** The page describes the current implementation, is not public API, and may change in any release.
3. **Overview.** The whole mechanism in one diagram and a short paragraph: inputs, stages, outputs.
4. **Stages or components.** One heading per stage or component, in the order data flows. Each says what it takes, what it produces, and where it lives in the code (`packages/compiler/src/split.ts`). Show the intermediate result for a small input when it helps.
5. **Data flow.** What moves between stages and in what form, and what runs at build time, on the server and in the client.
6. **Design decisions.** Each choice that a reader would question, with the alternative and why it lost. Link the decision record when one exists.
7. **Where to start in the code.** The entry function and the tests to read first. How to debug the subsystem, such as a flag that prints the intermediate output.
8. **Related.** The concept pages for the same behavior, and neighboring internals pages.

### Keeping internals accurate

Internals pages drift fastest, because they describe code that changes without a public API change.

- **`covers:` in the frontmatter** lists the source paths the page describes, such as `covers: [packages/compiler/src]`. `docs_check.py --repo .` reports covered paths that no longer exist.
- **Same pull request.** A change under a covered path that changes a stage, a data format or a decision updates the page.
- **Code paths, not line numbers.** Name files and functions. Line numbers are stale after the next commit.
- **Write from the code.** Read the source and run the subsystem on a small input before writing. Do not describe the design from memory or from old decision records.

## Writing one page

Follow these steps for every page. They work for a writer who finds docs hard, because each step is a small decision.

1. **Name the reader and their question.** Write one sentence, such as "A user who has installed the library wants to fetch data on the server." If you cannot write it, you do not know what page you are writing.
2. **Pick the type** from the question. "How do I" is a guide. "What is" or "why" is a concept. "What does this take" is reference.
3. **Copy the template** for that type.
4. **Write the example first.** Write and run the code the page is about. The prose explains the example, not the other way around.
5. **Write the lead sentence.** It answers the reader's question in short. A reader who stops here should know whether the page is for them.
6. **Fill each section** with lists and short paragraphs. Put each fact in the section the template gives it. A fact with no section belongs on another page.
7. **Cut.** Delete what the reader of this type does not need: history in a guide, steps in a concept, opinions in reference. Delete any sentence that only introduces the next one.
8. **Link.** Add the Related or Next steps links, and link the first use of each glossary term.
9. **Check.** Run plain-writing's `check_prose.py` and this skill's `docs_check.py` on the page.
10. **Test it as the reader.** Follow the page from a clean project. Or give a fresh agent only the page, with no access to the source. Every step it gets stuck on is a fix.

## Code examples

- **Runnable.** Every example runs as written. Include imports and the setup a reader would need. Mark omitted parts with a comment, such as `// ...rest of the component`, never by silently cutting them.
- **Tested.** Examples are extracted and run in CI, or they live as files in `examples/` and the page includes them. An example nobody runs breaks within a few releases.
- **Minimal.** Only the code that shows the point. No unrelated features, no styling.
- **Realistic.** Real-looking names (`user`, `cart`), not `foo` and `bar`.
- **Fenced with a language.** Every code block names its language, such as `ts`, `sh` or `json`.
- **Commands copy cleanly.** No `$` prompt in shell blocks the reader will copy. Show output in a separate block.
- **Show the result.** After code that produces output, show the output. Prefer text output to a screenshot.
- **Placeholders, never secrets.** Write `<YOUR_API_KEY>` or read from an environment variable (`process.env.API_KEY`). Never put a value that looks like a real key, token or password in an example.
- **Pinned where it matters.** Install commands use the package name without a version, so they stay current. Examples that depend on another tool's version say which version.

## Screenshots and media

Screenshots go stale with every interface change, and they cannot be searched, copied or translated.

- Prefer code output, a diagram or a short text description.
- When a screenshot is needed, generate it with a script, such as a Playwright test that opens the page and saves the image. Rerun the script when the interface changes.
- Name each screenshot after what it shows and the version it was taken on, or record the version in the page.
- Every image has alt text that states what the reader should notice.
- Crop to the part that matters, and use the same width and theme across the site.

## Diagrams

Use a diagram when a page describes more than two parts that interact, or more than two steps over time. Keep its source as text in the repo, in Mermaid or as SVG generated from source. Show one idea per diagram, and give each shape the same meaning across the site. [references/diagrams.md](references/diagrams.md) has the rules, which diagram fits which content, and alt text.

## Variants with tabs

Readers differ in package manager, language (TS or JS), framework, or operating system. Show the variants in tabs on one page, never as a separate page per variant.

- **One default.** The first tab is the most common choice, such as `npm` or TS.
- **Synced and remembered.** Choosing a tab switches every tab group of the same kind on the site, and the choice is kept between visits.
- **Only the differing part.** Tabs wrap the lines that differ. The shared prose stays outside.
- **Same content in each tab.** Each tab shows the same steps, so a reader never misses one by picking a tab.
- **Searchable.** Every tab's text is in the HTML and in the search index, not only the default tab's.

## Shared content

A fact that several pages need, such as supported versions, install steps or a limits table, lives in one included file. Pages include it instead of copying it. Copies drift apart within a few releases.

- Keep included files in a folder the generator does not turn into pages, such as `website/docs/_shared/`.
- An included file holds one fact or one block, never a whole section with its own headings.
- Code examples are included from `examples/` or a tested snippets folder, so the code that runs in CI is the code on the page.

## Callouts

Callouts (note, tip, warning, danger boxes) pull the eye away from the text. Each one has to earn that.

- **Warning or danger**: only for a mistake that loses data, breaks production, opens a security hole or cannot be undone.
- **Note**: a fact the reader must not miss that does not fit the flow, such as a version requirement.
- **Tip**: rarely. A tip that matters belongs in the text or a guide.
- **At most about one per screen.** A page full of callouts means the design or the page needs fixing. Fix the cause and drop the box.
- **The title says the point**, such as "Deleting a project cannot be undone", not "Warning".
- Never use a callout for marketing, links to unrelated pages, or "new in" notices that outlive the release.

## Voice

plain-writing sets the sentence rules. Docs add these:

- **Address the reader as "you".** "You can pass a key", not "the user can pass a key" or "we pass a key".
- **Present tense.** "The function returns", not "will return".
- **Imperative for steps.** "Run the build", not "you should run the build".
- **Never "simply", "just", "easy", "obviously" or "of course".** A reader who is stuck feels worse, and the words add nothing.
- **Docs are not a blog.** Docs describe how the product works now. Announcements, stories and "we are excited" go in the blog or release notes, which link to the docs.

## README and the site

The README is the entry point on GitHub and npm. It is not a second copy of the docs.

- **Holds**: one sentence on what the package is, install, one short example, and links to the docs site, the changelog and the license.
- **Does not hold**: guides, full API reference or concept explanations. They drift from the site when copied.
- **Small projects** (see "Small projects") are the exception: their README is the docs.
- A package in a monorepo has its own README that links its section of the site.

## Auditing an existing site

Before restructuring or adding pages, take stock.

1. **Inventory.** List every page with its current path, its type (or "mixed"), its last change date (`git log -1 --format=%cs -- <file>`) and whether its examples still run.
2. **Split mixed pages.** For each "mixed" page, list the pages it should become.
3. **Find gaps.**
   - Exports, commands, config keys and errors with no reference entry.
   - Core ideas with no concept page.
   - Frequent issue topics with no guide or troubleshooting entry.
   - Major versions with no migration page.
   - Subsystems contributors ask about in issues or pull requests with no internals page.
   - Reader signals, when the site has them: searches that return nothing, docs 404s, pages with poor "was this helpful" votes, and questions that repeat in issues and chats.
4. **Find stale pages.** Pages that mention removed APIs, old versions or options that no longer exist. pr-review's `surface.py` finds mentions of a removed name.
5. **Plan the sitemap.** Write the target navigation tree with each page's type and source (existing, split from, or new).
6. **Show the plan to the user** before moving pages. Moves break links, so the plan includes the redirects.

Write in this order when building a site from scratch, because each step unblocks the next:

1. Reference, generated where possible. It is the list of everything that exists.
2. Getting started.
3. Concept pages for the core ideas, and feature pages for the major features.
4. Guides for the most frequent tasks, ranked by how often they come up in issues.
5. Troubleshooting, migration and glossary.
6. Internals pages, when the project takes outside contributors or users ask how it works.

## Keeping docs current

- **Same pull request.** A change to the public surface changes its docs in the same pull request. That covers the reference entry, the feature page, examples, and the migration page for breaking changes. pr-review checks this.
- **Deprecations.** A deprecated API keeps its reference entry with a deprecation notice that names the replacement and the version that removes it. Its examples elsewhere move to the replacement.
- **Removals.** A removed API leaves the reference and appears in the migration page for that version.
- **Versioned docs.** When users stay on old major versions, publish docs per major version. Old versions show a banner that links the current one. One version of docs is enough while only one major version is maintained.
- **Checks in CI.** Run the link check, example tests and `docs_check.py` in the docs build. On a private repo, run them locally instead.
- **Review by date.** A page untouched for a year while its code changed is a candidate for review. The audit's inventory shows these.

## Search

Every docs site has search, opened as a command bar: a Search button in the header, `/` and Cmd or Ctrl+K. It is a modal dialog that searches page titles, headings and text from an index built at build time. Its code and index load on first open, and a result jumps to the matching heading. Commands such as switching the theme, version or language sit in the same list. [references/search.md](references/search.md) has the full design, ranking and tests. If one of the user's repos already has a command bar, such as idlip's `website/src/search/`, copy its design.

## Translations

Plan for translation from the first page, even when no translation is planned. A few choices cost little at the start and touch every page later:

- source pages in a locale folder, such as `website/docs/en/`
- an explicit id on each heading, so anchors survive translation
- interface strings in one file per language, as whole sentences with placeholders
- no text in images, and diagrams kept as text source
- CSS logical properties, so right-to-left languages work
- a search index per language

[references/translations.md](references/translations.md) has these rules and the process once translations start. That covers the source language as the truth, fallback pages, stale banners and the language switch. `docs_check.py --translation` finds missing and stale translations.

## Accessibility

- Heading levels never skip: an `h2` is followed by `h3`, not `h4`.
- Link text says where it goes. Never "here" or "this page".
- Every image and diagram has alt text that states its point.
- Meaning never rests on color alone, in diagrams, callouts or code highlighting.
- Code blocks have a copy button with a label, and syntax colors meet contrast in both themes.
- The site works with a keyboard alone: the sidebar, tabs, the search bar and the theme switch.

## Pages agents read

Agents read docs too, often as raw text.

- **Serve Markdown.** Offer each page as Markdown at a predictable path, such as the page URL with `.md`, when the generator supports it.
- **Publish `llms.txt`** at the site root: the site's title, a one-paragraph summary, and a list of links to the pages, grouped by section. Optionally `llms-full.txt` with all pages joined.
- **Self-contained pages.** Each page states its imports and context, so a page fetched alone still works. This is the same rule plain-writing gives for writing that agents read.

## Checker script

```bash
python3 <skill>/scripts/docs_check.py website/docs                 # all checks
python3 <skill>/scripts/docs_check.py website/docs --exports src/index.ts --reference website/docs/reference
python3 <skill>/scripts/docs_check.py website/docs --repo .          # also check covers: paths
python3 <skill>/scripts/docs_check.py website/docs/en --translation website/docs/ja
python3 <skill>/scripts/docs_check.py website/docs --json
```

It reads every `.md` and `.mdx` file under the folder and reports:

- **Type.** Missing or unknown `type:` in the frontmatter.
- **Structure.** Sections the type's template requires, such as `Why`, `How it works` and `Usage` on a feature page.
- **Lead.** A page whose first content is a heading instead of a lead sentence.
- **Fences.** Code blocks with no language.
- **Links.** Relative links to files that do not exist.
- **Orphans.** Pages no other page links to, except `index` pages and pages listed with `--entry`.
- **Exports.** With `--exports` and `--reference`, names exported from the entry file that no reference page mentions, and exports declared there with no doc comment above them.
- **Translations.** With `--translation DIR` (repeatable), source pages with no translation, translated pages with no source (error), translations older than their source in git, and heading ids the translation lacks.
- **Covered paths.** With `--repo`, paths in a page's `covers:` list that do not exist under the repo root.
- **Prerequisites.** Problems in `requires:` lists:
  - a required page that does not exist (error)
  - a cycle (error)
  - a required page in the same folder whose `order:` or `sidebar_position:` is not lower (error)
  - a required page the page does not link (warning)

Errors (unknown type, missing required section, broken link, missing covered path, broken prerequisite order, translation with no source) exit 1. Warnings (no lead, no fence language, orphans, undocumented exports) are worth fixing. Navigation defined in the generator's config, such as a sidebar file, is not read: an orphan by links may still be in the sidebar. Check the sidebar by hand for those.

## Review checklist

For a page:

- [ ] The frontmatter names one type, and the page holds only that type.
- [ ] The lead sentence answers the reader's question.
- [ ] The headings follow the type's template.
- [ ] Every example runs as written, with imports, and its block names a language.
- [ ] Each term with a specific meaning links its glossary or concept page on first use.
- [ ] The page ends with Related or Next steps links.
- [ ] `check_prose.py` and `docs_check.py` pass.
- [ ] A reader with only this page, or a fresh agent, completes it from a clean project.
- [ ] Callouts are rare and each title states its point. Variants use synced tabs.
- [ ] Diagrams have text source and alt text. Screenshots are generated by a script.
- [ ] Examples use placeholders, never values that look like real secrets.
- [ ] The voice uses "you", present tense, and no "simply", "just" or "easy".
- [ ] Headings do not skip levels, and no link text says "here".

For the site:

- [ ] The top level follows the reader's path: getting started, guides, concepts, reference.
- [ ] Getting started reaches a working result in under 10 minutes.
- [ ] Every export, command, config key and error code has a reference entry.
- [ ] Every core idea and major feature has a concept page.
- [ ] The most frequent tasks from issues have guides.
- [ ] Each maintained major version has a migration page from the one before.
- [ ] Moved pages have redirects, and the link check passes.
- [ ] Each section follows "Page order": concepts after their `requires:`, guides by project stage, and previous and next links in sidebar order.
- [ ] Search finds each page by the words a reader would use.
- [ ] `llms.txt` lists the pages, if the site serves agents.
- [ ] The command bar opens from the header, `/` and Cmd or Ctrl+K, and loads its code and index only on first open.
- [ ] Every public export has a doc comment, and every error code links to its entry.
- [ ] Facts used on several pages come from one included file.
- [ ] The README holds what the package is, install, one example and links, not a copy of the docs.
- [ ] Translation-ready: locale folder, explicit heading ids, interface strings in one file, no text in images.
- [ ] Concept pages explain what the user observes. Internals pages, if any, carry the not-public-API notice and a `covers:` list that exists.
