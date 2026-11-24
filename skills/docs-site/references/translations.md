# Translations

Most sites start in one language and add others later. Adding them later is cheap only when a few choices were made at the start. Make the choices in "From the first page" even when no translation is planned. Follow "When translations start" once one is.

## From the first page

These cost little now and a lot to retrofit.

- **Locale folders.** Keep the source pages in a folder named for their language, such as `website/docs/en/`. A translation is a sibling folder with the same tree (`website/docs/ja/`). The source language keeps URLs without a prefix (`/guides/deploy`), and other languages get one (`/ja/guides/deploy`). Moving every file into a locale folder later touches every page and every relative link.
- **Explicit heading ids.** Give each heading a fixed id, such as `## Why {#why}`, when the generator supports it. Generated ids change with the heading text, so a translated page breaks every link to its anchors. The search index and cross-page links use these ids.
- **Interface strings in one file.** Sidebar group names, "On this page", "Previous" and "Next", callout titles, search text, the empty state and the banner text live in one strings file per language. Never hard-code them in layout components.
- **Whole sentences in strings.** A string is a full sentence with placeholders (`"No results for {query}"`), never pieces joined in code. Word order differs between languages.
- **No text in images.** Diagrams are text source (Mermaid or SVG from source) so their labels can be translated. Screenshots with interface text are regenerated per language or replaced with code output.
- **Plain writing.** plain-writing's rules already make text easier to translate: short sentences, no idioms or metaphors, and the same term for the same thing. The glossary doubles as the translation glossary.
- **Formatting through `Intl`.** Dates, numbers and lists in the interface use `Intl.DateTimeFormat`, `Intl.NumberFormat` and `Intl.ListFormat`, never hand-built strings.
- **Layout that flips.** CSS uses logical properties (`margin-inline-start`, `padding-block`, `inset-inline-end`) so a right-to-left language works without a second stylesheet. Set `lang` and `dir` on `<html>`.
- **Search per language.** The search index is built per locale folder, and the ranking does not assume English word endings or spaces. See [search.md](search.md).

## When translations start

- **The source language is the truth.** A change lands in the source first. Translations follow and never add content the source lacks.
- **What to translate, in order:** getting started, then concepts and feature pages, then guides, then troubleshooting. Decide with the user whether reference is translated. Generated reference usually stays in the source language, because it comes from code comments.
- **Code stays as is.** Identifiers, commands and output are not translated. Comments inside examples may be.
- **Fallback.** A page with no translation shows the source page with a notice in the reader's language, instead of a 404.
- **Stale banner.** A translated page whose source changed since the translation shows a banner that links the source page. `docs_check.py --translation` finds these pages from git history.
- **Language switch.** A control in the header and a command in the search bar. Switching keeps the reader on the same page, at the same anchor.
- **SEO.** Each page lists its other languages with `<link rel="alternate" hreflang="...">`, including `x-default` for the source.
- **Who translates.** Machine translation needs a reviewer who reads the language before it ships. Record the reviewer in the pull request.

## Checking translations

```bash
python3 <skill>/scripts/docs_check.py website/docs/en --translation website/docs/ja
```

Reports, for each translation folder:

- a source page with no translated page (warning)
- a translated page with no source page (error)
- a translated page whose source has a later commit than the translation (warning, with both dates)
- heading ids in the source that the translation lacks (warning), since links to those anchors would break
