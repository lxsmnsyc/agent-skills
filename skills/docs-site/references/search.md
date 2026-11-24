# Search as a command bar

Every docs site has search, opened as a command bar. A reader who knows the word they want reaches the right heading in two keystrokes and a few letters, without reading the sidebar.

Load ui-style when building it. If one of the user's repos already has a command bar, copy its design instead of starting over. idlip's `website/src/search/` is one: a build step for the index, `rank.ts` for ranking, `palette.ts` for the bar, and a small eager file that binds the keys.

## Opening and closing

- A **Search button in the header**, showing the shortcut (`/` or `⌘K`). At narrow widths it shrinks to an icon with an `aria-label`.
- **Keys**: `/` when focus is not in a text field, and Cmd+K or Ctrl+K anywhere.
- The bar is a **native modal `<dialog>`** with a label. The browser traps focus in it, makes the page behind it inert and closes it on Escape.
- On close, **focus returns** to the element that opened it.

## The index

- **Built at build time** from the rendered pages, written as a static JSON file. No search service, and no network call besides the index file.
- **One entry per heading**, plus one per page for the text before the first heading. Each entry holds the page path, page title, heading, anchor id and the section text with markup removed.
- Index inline code. Leave code blocks out, except signatures on reference pages, which readers search by name.
- Keep the entries in sidebar order, so ties fall back to the reading order.
- One index per docs version and per language. The bar loads the one for the page it is on.

## Loading

- Only the code that binds the button and the keys loads with the page.
- The bar's code and the index load the first time the bar opens. Starting the load when the pointer hovers the button or the button gets focus is fine.
- Measure and report the sizes of the index and the bar's code, raw and gzip. Check that no request for either happens before the first open.

## Ranking

- A match in the page title beats a match in a heading, and a heading beats the text.
- Every word of the query must match.
- Inside a field, a word that starts with the term beats a word with the same stem ("resume" finds "Resuming"), which beats a match inside a word.
- In text, a term that appears more often breaks a tie.
- At most three results from one page, so one long page does not fill the list.
- Stemming is per language. Languages without spaces between words (Chinese, Japanese, Thai) split words with `Intl.Segmenter`.

## Results

- Each result shows the page title, the heading, and a snippet around the match, with the matched words highlighted.
- Enter opens the page at the heading's anchor. Clicking does the same.
- Arrow keys move the active result. The pointer moves it too.
- With an empty query, list a few start pages (getting started and the most visited guides), not nothing.
- **Commands** sit in the same list, told apart by an icon: switch the theme, open the playground or REPL, switch the docs version, switch the language. A command that matches the query comes before pages.
- **Empty state**: "No results for “query”" with a link to getting started or the guides index.
- A live region announces "N results for query" to screen readers, and nothing for an empty query.

## Tests

- The index has one entry for every heading of every page, and no leftover markup.
- Each of a few real queries, taken from issues or the docs' own key terms, lists the expected page first.
- No more than three results per page.
- The empty state shows for a query with no match.
- In a browser test: no request for the index before the first open, focus stays in the dialog, and Escape returns focus to the button. Light and dark, and a 390 px wide viewport.

## Feeding the audit

When the site has analytics, log queries that return no results, without anything that identifies the reader. Each repeated query is a missing page, a missing heading, or a term the docs call something else. Add it to the audit's gap list, or add the reader's term to the page's lead and the glossary.
