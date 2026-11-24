---
name: landing-page
description: Rules for landing pages, homepages and marketing sites of any product, such as a library, CLI, web app, mobile app, API or physical product. The page shows a demo of the product or its effect, with an animated or interactive hero visual chosen from designs the author reviews. It sells the benefit and the difference from competitors instead of describing features. It keeps text short and lets visuals carry the page. It picks the selling points the visitor cares about, uses playful animation or interaction that shows what the product does, and shows who uses it when that proof is strong enough. Includes steps for each kind of product, a word count script and a review checklist. Use this skill whenever designing, writing, building or reviewing a landing page, product homepage, marketing site, the website/ folder of a repo, or a hero section, even if the user does not say "landing page". Load ui-style with it. This skill overrides only the ui-style rule against idle and first-paint animation. Every other ui-style rule still applies.
---

# Landing page

A landing page has one job: make a visitor want the product and take the first step. A page that describes the product without selling its benefit does not attract users. A section that lists what the product has without showing how it differs from the competition states the obvious.

Every landing page needs these things:

1. A demo of the product or of its effect, and a hero visual that moves.
2. Sections that sell the benefit and the difference from competitors.
3. Playful UI: animation or interaction that shows what the product does.
4. Proof of who uses it, when that proof is strong enough to help.
5. Little text. Visuals carry the page, and every block earns its place by selling something the visitor cares about.

Load ui-style along with this skill. ui-style says not to animate idle elements or content on first paint. On a landing page that rule is lifted for the demo and for animations that show the product. All other ui-style rules hold: motion uses `transform` and `opacity`, `prefers-reduced-motion` is honored, every component state is designed, and hit targets meet the minimum size.

## Before writing

Collect these facts first. Ask the user for any that the repo, the product or its public data cannot answer.

- **Who the visitor is** and the problem they arrive with.
- **The kind of product.** Then follow its steps in [references/product-kinds.md](references/product-kinds.md).
- **The main alternatives** the visitor would otherwise use, including "do it by hand" or "do nothing".
- **The differentiator**: what this product does that those alternatives do not, or do worse. Back it with a number when you can.
- **The first step** the visitor should take: install, sign up, download, book a demo or buy.
- **Available proof**: users, customers, downloads, stars, reviews, press, benchmarks. Note what can be shown with permission and what cannot.

If there is no differentiator, say so to the user before designing. A page cannot sell a difference the product does not have.

## Selling points

Decide what the page sells before writing any section. Every block on the page must serve a selling point.

1. **List candidate selling points** from what the product does: features, numbers, design choices.
2. **Check each one matters to the visitor.** Keep it only if evidence shows the visitor wants it or feels the problem it solves. Evidence includes issues and feature requests, questions in forums and chats, reviews of alternatives, and what competitors lead with. A point that only the builders care about, such as an internal design choice, is not a selling point unless it produces a result the visitor wants. Then sell the result.
3. **Check each one is a difference.** A point that every alternative also has is table stakes. It goes in a short list or the FAQ, not in its own section.
4. **Rank the rest** by how much the visitor cares, times how much better the product is than the alternatives.
5. **Pick one main selling point.** It owns the hero headline and the hero demo. The next two to four become the benefit sections, in rank order.

Then map every planned block to one selling point, or to one of the visitor's questions below. Cut any block that maps to neither.

- What is it?
- Why should I care?
- Does it work?
- Why this over the alternative?
- Can I trust it?
- How do I start?

Content that answers none of these goes to the docs, with a link: API reference, the full feature list, changelog, roadmap, architecture and team history.

Write one page for one visitor. A second audience, such as buyers next to developers, gets its own page.

Show the ranked list and the mapping to the user before building. When the user disagrees with the main selling point, change it before writing copy.

## Section order

Use this order unless the product calls for another one:

1. **Hero**: headline, one line of support, one primary call to action (CTA), and the demo or the start of it.
2. **Proof strip**: logos, user counts or ratings, right below the hero. Leave it out when there is no proof.
3. **Benefit sections**: one per main benefit, three to five in total.
4. **Comparison**: how the product differs from the alternatives.
5. **Objections**: price or license, requirements, support, maturity, often as a FAQ.
6. **Final CTA**: repeat the first step, with the shortest path to it.

## Text budget

A landing page is looked at, not read. Visitors skim headlines and visuals, and leave when they hit walls of text. Keep to these limits:

| Part | Limit |
| --- | --- |
| Hero headline | 10 words |
| Hero support line | 25 words, one sentence |
| Section headline | 8 words |
| Section body | 25 words, one sentence. A card is a title and one line. |
| Visible text in `<main>` | 600 words, without code blocks and the FAQ |

- Every section has a visual: a demo, a screenshot, a chart, a snippet or a diagram. It takes at least half of the section's area.
- **Skim test**: reading only the headlines and looking at the visuals tells the whole story. If it does not, fix the headline or the visual, not the body text.
- **Conditions and caveats** go in a footnote, a chart foot or a linked page, never in the hero or a headline. The number stays next to the claim. Its run conditions, ranges and method go out of the way.
- **Facts as a row, not prose.** License, version, runtime and price read faster as a row of short label and value pairs.
- **Reduced-motion and no-JS versions show one still frame**, the end state. Do not write out every step of an animation as text panels. That repeats the content and can make up most of the page's words.
- **Diagrams carry short labels**, not sentences. A step label is a few words.
- Measure the text on the built page with `scripts/word_count.py`. Exclude the FAQ and any reduced-motion panels. Add a test that fails over the budget, so later edits do not grow the text back.

```
python3 skills/landing-page/scripts/word_count.py dist/index.html --budget 600 --exclude "#faq"
```

## Hero

- The headline states the result the visitor gets, not the category of the product. "Ship forms in five lines" beats "A form library for React". "Your inbox, sorted before you wake up" beats "An AI email client".
- The support line says what the product is and who it is for, in one sentence.
- Give the hero one primary CTA. A second action, such as "View on GitHub" or "See pricing", uses a quiet style.
- Show the demo in the hero, or start it there and continue right below. A visitor should see the product working without scrolling far.
- The hero visual is animated or interactive. A static snippet, screenshot or illustration alone is not enough. It can be the first frame of the animation. See "Hero visual".

## Hero visual

The hero visual shows the main selling point in motion. Pick from this order, and move down only when the option above cannot show that point well:

1. **The product at work**: the real product, or a faithful model of it, doing its main task. Code that types itself and renders its output, a UI that runs its main flow, a request and its response arriving, a before and after that loops.
2. **Something the visitor can use**: a small input, slider or toggle in the hero that changes the product's real output.
3. **A concept in motion**: an animated diagram of what the product does, such as data flowing through it, requests fanning out to a cache, a build graph collapsing to one step, or files syncing between devices. Use this when the product has no visible surface (a library internal, a protocol, an infrastructure service), or when its effect is clearer as a model than as a screen.

Rules for every hero visual:

- It shows what the product does or the effect it has. A concept animation is faithful to how the product works: no steps, speeds or parts it does not have. Decoration, such as floating shapes or particles, does not count.
- One idea, readable in about five seconds. It loops, or ends on a frame that states the result.
- It follows the motion rules under "Playful UI": it pauses off screen, does not delay the largest contentful paint, and shows a still end state with `prefers-reduced-motion`.

Examples by product kind:

| Kind | Product at work | Concept in motion |
| --- | --- | --- |
| Library | The code types itself and the rendered output or result appears next to it | Data flowing through the library's pipeline, or the bundle shrinking against an alternative |
| CLI | An animated terminal runs the command and prints the real output | The manual steps collapsing into one command |
| Web app | The UI runs its main task with real-looking data | Inputs from several tools merging into the product's one result |
| API | A request goes out and the real response streams back | Calls routing through the platform to the services behind it |
| App | The app in a device frame runs its main flow | Data syncing between devices |
| Hardware | Video of the product in use | An exploded view that assembles |

### Propose designs before building

The hero visual is the most expensive part of the page and the hardest to judge from a description, so the author picks it:

1. Propose two or three designs. List product-at-work designs first, and add a concept design when one would show the selling point better. For each, write what moves, the selling point it shows, the still frame for reduced motion, and the build cost (CSS and SVG, a canvas, a recorded video, a live embed).
2. When the user wants to compare them on screen, build the top two as rough prototypes on one review page, or behind a query parameter such as `?hero=b`. Keep them rough until one is picked.
3. Build the rest of the page while the author decides. The hero visual has a fixed slot, so the choice does not change the layout.
4. Remove the designs that were not picked before the page ships.

## Demo

Show the product or its effect in one of three ways:

- **Animation** of the product doing its work, such as a before and after, a recorded flow or a live render.
- **A sample UI** of the product that the visitor can see or use.
- **A snippet** of code, a command or a config, with its output.

Rules for every demo:

- Use the real product, or a faithful model of it. Do not show features that do not exist.
- A snippet must run as shown. Give it a copy button, and show its output next to it.
- Prefer a demo the visitor can use, such as a playground, an editable input or a toggle, over a static picture.
- Show the effect the visitor cares about, not only the interface. For a speed claim, race the product against a baseline. For a design tool, show the result it produced.
- The demo works on mobile and with the keyboard. When an interactive demo cannot fit a small screen, show a recorded version there.

## Selling the benefit

Each benefit section follows the same shape:

1. **A benefit headline**: what the visitor gains or no longer has to do.
2. **Proof**: a demo, a number, a comparison or a quote.
3. **The feature behind it**: one or two lines on how the product does it.

Rules:

- Write from the visitor's side. "You" and the result they get, not "we" and what was built.
- Replace adjectives with facts. Ban empty claims such as "blazing fast", "seamless", "powerful", "revolutionary", "next-generation" and "best-in-class". Write "renders 10,000 rows at 60 fps" instead of "blazing fast".
- Every number links to how it was measured, or has its conditions in a footnote or chart foot. For code, the perf-pass skill produces these numbers.
- Do not spend a section on what every competitor also has. A table-stakes feature goes in a short list or the FAQ, not in its own section.
- The comparison is fair and dated. Name the version compared, and include where an alternative wins if a visitor would find out anyway.

The plain-writing rules still apply to the page copy: short sentences, exact words, no metaphors, no em-dashes. Persuasion comes from facts and proof, not from tone.

## Playful UI

Add animation or interaction that is relevant to the product:

- Every animation shows something the product does, or the effect it has. Decoration with no meaning, such as floating blobs or particles, does not count.
- Interactions let the visitor try the product's idea in a few seconds. Examples: drag a slider to see the result change, type into a box to see the output, toggle between "without" and "with".
- Reward interaction with a micro-interaction, as ui-style asks for every control.
- Start an animation when it scrolls into view, and pause it when it leaves the screen.
- Load heavy demos (video, WebGL, a bundled playground) after the first paint. Hold their place with a still frame or a skeleton of the same size. The demo must not delay the largest contentful paint or shift the layout.
- With `prefers-reduced-motion`, show the still end state or a short fade, and keep interactive demos working.

## Proof and trust

Show who uses the product, when that proof exists and is strong enough to help:

- **Logos** of companies or projects that use it, with their permission.
- **Testimonials** with a name, role and photo, from people who agreed to be quoted.
- **Numbers**: users, downloads, GitHub stars, ratings, uptime. Prefer live numbers fetched from the source over numbers typed into the page.
- **Public use**: dependents on npm or GitHub, apps built with it, case studies, press.

Rules:

- Never invent proof. No placeholder logos, made-up testimonials, rounded-up counts or stock photos posing as customers.
- When there is no proof, leave the section out. A small honest project page beats one with fake trust. A young project can show other proof: who built it, what it powers, its test coverage or its license.
- Put the strongest proof near the hero and near the final CTA, where the visitor decides.

### When proof is strong enough

Weak proof hurts. "40 downloads a week" tells the visitor nobody uses the product. Show a piece of proof only when it would impress the target visitor.

- **Judge numbers against the main alternative**, not as absolutes. When the product's count is far below the competitor's, for example under a tenth, do not show the count. Show a better signal: growth rate, named dependents, test coverage or the author's track record.
- **Starting floors** when no competitor data exists. The user can change them.

  | Proof | Show it at |
  | --- | --- |
  | npm weekly downloads | 1,000 or more |
  | GitHub stars | 500 or more |
  | Store or review site rating | 4.0 or more, from 100 reviews or more |
  | Users or customers | a count the visitor's peers would respect, judged per market |

- **Logos must be known to the visitor's audience.** Show three or more, or one that every visitor knows. Brands from the visitor's own industry beat famous brands from an unrelated one. One unknown logo is weaker than none.
- **Rank proof by strength** and lead with the strongest you have:
  1. known brand logos
  2. named testimonials with a result
  3. case studies with numbers
  4. usage numbers
  5. stars and ratings
- When nothing clears the bar, leave the proof section out and use the space for the demo or the comparison.

## Objections and the final CTA

- Answer the questions that stop a visitor from starting: price, license, requirements (browsers, platforms, runtimes), size, data privacy, support, and how mature the project is.
- Put a short answer next to the CTA when one question blocks most visitors, such as "Free and MIT licensed" or "No credit card".
- Repeat the primary CTA at the end of the page.
- The path from the CTA to the first result takes three steps or fewer. When it takes more, fix the onboarding or say so to the user.

## Page basics

- Set a title, a meta description and an Open Graph image that shows the product, not only the logo.
- Make the page fast. A landing page that loads slowly loses the visitor before the demo plays.
- Support dark mode when the product does.

## Review checklist

Run this on a finished page. Every line passes, or the user has accepted the gap.

- [ ] One main selling point owns the hero. It matters to the visitor, with evidence, and differs from the alternatives.
- [ ] Every block maps to a selling point or a visitor question. Nothing is there only because the product has it.
- [ ] Visible text is within the budget, measured on the built page, with a test that holds it there.
- [ ] Every section has a visual. The skim test passes.
- [ ] Conditions and caveats sit in footnotes, not in the hero.
- [ ] The hero headline states a result, not a category.
- [ ] The hero has one primary CTA.
- [ ] A demo of the product or its effect is visible in or right below the hero.
- [ ] The hero visual is animated or interactive and shows the main selling point. It is the product at work, unless a concept animation shows the point better and stays faithful to how the product works.
- [ ] The author picked the hero visual from the proposed designs, and the others are gone from the page.
- [ ] Snippets run as shown and have a copy button.
- [ ] Each benefit section has a benefit headline, proof and the feature behind it.
- [ ] At least one section shows the difference from named alternatives.
- [ ] No empty claims. Every number states its source or conditions.
- [ ] Every animation or interaction shows something the product does.
- [ ] Animations pause off screen and respect `prefers-reduced-motion`.
- [ ] Heavy demos load after the first paint with no layout shift.
- [ ] All proof is real, shown with permission, and clears the strength bar. Weak or no proof means no proof section.
- [ ] The main objections are answered.
- [ ] The CTA repeats at the end, and the first result takes three steps or fewer.
- [ ] The steps for the product kind in references/product-kinds.md are covered.
