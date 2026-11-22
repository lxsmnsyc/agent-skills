---
name: landing-page
description: Rules for landing pages, homepages and marketing sites of any product, such as a library, CLI, web app, mobile app, API or physical product. The page shows a demo of the product or its effect. It sells the benefit and the difference from competitors instead of describing features. It uses playful animation or interaction that shows what the product does, and shows who uses it when that proof exists. Includes steps for each kind of product and a review checklist. Use this skill whenever designing, writing, building or reviewing a landing page, product homepage, marketing site, the website/ folder of a repo, or a hero section, even if the user does not say "landing page". Load ui-style with it. This skill overrides only the ui-style rule against idle and first-paint animation. Every other ui-style rule still applies.
---

# Landing page

A landing page has one job: make a visitor want the product and take the first step. A page that describes the product without selling its benefit does not attract users. A section that lists what the product has without showing how it differs from the competition states the obvious.

Every landing page needs four things:

1. A demo of the product or of its effect.
2. Sections that sell the benefit and the difference from competitors.
3. Playful UI: animation or interaction that shows what the product does.
4. Proof of who uses it, when that proof exists.

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

## Section order

Use this order unless the product calls for another one:

1. **Hero**: headline, one line of support, one primary call to action (CTA), and the demo or the start of it.
2. **Proof strip**: logos, user counts or ratings, right below the hero. Leave it out when there is no proof.
3. **Benefit sections**: one per main benefit, three to five in total.
4. **Comparison**: how the product differs from the alternatives.
5. **Objections**: price or license, requirements, support, maturity, often as a FAQ.
6. **Final CTA**: repeat the first step, with the shortest path to it.

## Hero

- The headline states the result the visitor gets, not the category of the product. "Ship forms in five lines" beats "A form library for React". "Your inbox, sorted before you wake up" beats "An AI email client".
- The support line says what the product is and who it is for, in one sentence.
- Give the hero one primary CTA. A second action, such as "View on GitHub" or "See pricing", uses a quiet style.
- Show the demo in the hero, or start it there and continue right below. A visitor should see the product working without scrolling far.

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
- Every number links to how it was measured, or states the conditions next to it. For code, the perf-pass skill produces these numbers.
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

Show who uses the product, when that proof exists:

- **Logos** of companies or projects that use it, with their permission.
- **Testimonials** with a name, role and photo, from people who agreed to be quoted.
- **Numbers**: users, downloads, GitHub stars, ratings, uptime. Prefer live numbers fetched from the source over numbers typed into the page.
- **Public use**: dependents on npm or GitHub, apps built with it, case studies, press.

Rules:

- Never invent proof. No placeholder logos, made-up testimonials, rounded-up counts or stock photos posing as customers.
- When there is no proof, leave the section out. A small honest project page beats one with fake trust. A young project can show other proof: who built it, what it powers, its test coverage or its license.
- Put the strongest proof near the hero and near the final CTA, where the visitor decides.

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

- [ ] The hero headline states a result, not a category.
- [ ] The hero has one primary CTA.
- [ ] A demo of the product or its effect is visible in or right below the hero.
- [ ] Snippets run as shown and have a copy button.
- [ ] Each benefit section has a benefit headline, proof and the feature behind it.
- [ ] At least one section shows the difference from named alternatives.
- [ ] No empty claims. Every number states its source or conditions.
- [ ] Every animation or interaction shows something the product does.
- [ ] Animations pause off screen and respect `prefers-reduced-motion`.
- [ ] Heavy demos load after the first paint with no layout shift.
- [ ] All proof is real and shown with permission. No proof means no proof section.
- [ ] The main objections are answered.
- [ ] The CTA repeats at the end, and the first result takes three steps or fewer.
- [ ] The steps for the product kind in references/product-kinds.md are covered.
