# Page types

Rules for each `type:` value. The template for each type is in `../templates/`.

## Telling the types apart

Ask what the reader wants at the moment they open the page.

| The reader says | Type |
|---|---|
| "I am new. Show me how this works." | `tutorial` |
| "I know the basics. How do I do X?" | `guide` |
| "What is X? Why does it behave this way?" | `concept` |
| "What is feature X, when do I use it, how?" | `feature` |
| "What exactly does X take and return?" | `reference` |
| "I see this error. What do I do?" | `troubleshooting` |
| "I am on the old version. What do I change?" | `migration` |
| "Give me a complete project to copy." | `example` |
| "What does this word mean here?" | `glossary` |
| "How is this built inside? I want to change it." | `internals` |

Two pairs are easy to confuse:

- **Tutorial or guide.** A tutorial is for learning: the writer picks every choice, and the reader cannot fail. A guide is for working: the reader brings their own project and goal. The getting started page is a tutorial. "Deploy to Vercel" is a guide.
- **Concept or internals.** A concept explains what the user observes, such as which code the compiler moves to the client. Internals explain how the implementation does it, such as the compiler's stages. A user never needs internals to use the product.
- **Concept or feature.** A concept explains an idea that spans several features, such as "reactivity". A feature page covers one thing the reader can use, such as `createResource`, from why to usage. Both sit in the Concepts section.

## tutorial

- One path. No options, no "alternatively". The writer makes every choice.
- Every step produces a visible result, so the reader knows it worked.
- Steps never fail on a clean machine that meets "Before you start". Test this on a clean machine or container.
- Explain only enough to keep going. Link the concept pages for depth at the end, not mid-step.
- Under 10 minutes for getting started. Longer tutorials say their length in the lead.

Required sections: `Before you start`, `Next steps`.

## guide

- Named by the task, as a verb phrase.
- Assumes the reader finished getting started. Links what it assumes in "Before you start".
- Numbered steps, one action each. A step with two actions is two steps.
- Handles the real-world cases readers hit, such as an existing config file, unlike a tutorial.
- Ends with a way to check it worked.
- No theory. One line and a link to the concept page when the reader needs the why.

Required: numbered steps (an ordered list or numbered headings) and `Related`.

## concept

- Explains, does not instruct. No numbered steps.
- Answers the questions a reader has, in the order they have them. Use those questions as headings.
- Uses diagrams for anything with parts that interact or steps over time.
- States trade-offs and the alternatives the design rejected, with reasons.
- Small code examples are fine when they make the idea clearer.
- Lists the pages a reader must understand first in `requires:`, and links them.

Required section: `Related`.

## feature

The feature page from SKILL.md. Sits in the Concepts section.

Required sections: `Why`, `How it works`, `Usage`, `Related`. Recommended: `Options`, `Limits and caveats`.

## reference

- Complete. Every export, command, flag, config key or error code in scope has an entry.
- Every entry has the same shape (see SKILL.md, "The reference entry").
- Dry. No opinions, no tutorials. Facts a caller needs, and one example per entry.
- Sorted by module in the order of the entry file, alphabetical inside a module, and says so in the lead.
- Generated from the code when the tooling allows it.

No required sections. Each entry is a heading with the identifier.

## troubleshooting

- Each heading is the symptom as the reader sees it: the exact error message, or what they observe. Readers search for these words.
- Each entry has a cause and a fix, with the exact command or code.
- Entries come from repeated issues and chat questions. Link the issue when it has more context.

No required sections.

## migration

- One page per major version, from the previous major.
- Lead says the effort for a typical project.
- Each breaking change has before and after code and the reason for the change.
- Lists deprecations with their replacement and the version that removes them.
- Ends with ordered upgrade steps, including a codemod when one exists.

Required section: `Breaking changes`.

## example

- A complete project or a self-contained recipe that runs as written.
- Links its source, such as a folder in `examples/`, so the reader can clone it.
- Lead says what the example shows and which features it uses, with links to their pages.

No required sections.

## glossary

- One entry per term, sorted alphabetically.
- Each definition is one sentence, followed by a link to the concept or feature page.
- Only terms with a meaning specific to the product, or common words the product uses in a narrow sense.

No required sections.

## internals

The internals page from SKILL.md. Sits in the Internals section, after Contributing.

- For contributors and advanced users. Says so in the lead.
- Carries a notice that it describes the current implementation, is not public API, and may change in any release.
- Follows the data: one heading per stage or component, in the order data flows through them.
- Names files and functions for each stage, never line numbers.
- Lists the source paths it describes in `covers:` in the frontmatter.
- Explains design decisions with the rejected alternative.

Required section: `Overview`. Recommended: `Design decisions`, `Where to start in the code`, `Related`.

## index

Landing pages of a section. A short lead, then links to each page in the section with one line each. Excluded from the orphan check.

No required sections.
