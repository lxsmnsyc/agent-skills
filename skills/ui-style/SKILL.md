---
name: ui-style
description: Design rules for this user's interfaces. Let the layout explain and keep out secondary labels. Give every user action instant feedback and a micro-interaction, and make animated transitions reversible mid-way. Use icons instead of text glyphs, cover every component state, and avoid the symptoms of generated design, such as one-side borders on rounded components. Use this skill whenever writing, editing or reviewing UI components, pages, forms, dialogs, transitions or loading and empty states. A repo's own design rules win.
---

# UI style

Design choices that apply to every interface this user builds. A repo's own design system or guidelines win when they disagree.

## Let the layout explain

Avoid unnecessary secondary labels and descriptions. Let the layout do the explaining.

- Group, align and order elements so their relation is visible. Spacing and a shared container show that items belong together, with no heading needed.
- Drop a subtitle that restates the title, helper text that restates the field label, and a section heading over a single obvious group.
- Drop captions such as "Click here to..." on a control whose label and position already say what it does.
- Keep text that adds a fact the layout cannot carry: a unit, an input format, a limit, or the consequence of a destructive action.
- When a screen needs many explanations, fix the layout or the flow first. Text added to rescue a confusing layout makes the screen harder to read.

## Hierarchy

- Build hierarchy from size, weight and color. Do not add boxes, borders or dividers to separate things that spacing already separates.
- Give each view one primary action. Other actions use secondary or quiet styles.
- Use one spacing scale in steps of 4 or 8, and a small set of radius and shadow tokens. Do not write one-off values.
- Nest corners concentrically: an inner element's radius equals the outer radius minus the padding between them.

## Micro-interactions

Give every change the user causes a micro-interaction: press, toggle, check, submit, drag, drop, expand, copy, add and remove.

- Animate only in response to the user or to a state change they caused. Do not animate idle or decorative elements, and do not animate content on first paint.
- Show press feedback within 100ms. Prefer optimistic updates, and roll back with a visible error if the request fails.
- Show a pending state inside the control that started the work, such as a spinner inside the button. Do not block the page with a global spinner.

## Motion

- Animate only `transform` and `opacity`. Animating width, height, top or left causes layout work and jank.
- Keep durations between 150ms and 250ms. Use ease-out for elements entering and ease-in for elements leaving. Exits are faster than entrances.
- Honor `prefers-reduced-motion`. Replace movement with an opacity change, or with no animation.

## Reversible transitions

A transition driven by script must be able to reverse from any point. If the user cancels mid-way, for example by pressing back while a new page slides in, the transition plays backward from where it is.

- Drive the animation from state, with CSS transitions or the Web Animations API. Call `animation.reverse()`, or start a new animation from the current computed value.
- Do not use fire-and-forget keyframes or chained timeouts that must run to the end.
- Do not jump to the end state and then animate back. Read the current value and reverse from there.
- Commit side effects (navigation, data changes) only when the transition finishes, so a reversed transition leaves nothing behind.

## Highlights on rounded components

A common symptom of bad design is an accent border on one side of a rounded component. An example is a left border on a card with rounded corners. The border bends around the corner and looks broken.

- On a rounded component, highlight the whole component: a background tint, a full outline or a ring.
- A one-side border is fine only on a component with square corners on that side.

## Icons

- Use icons from the project's icon set instead of text glyphs such as `×`, `→`, `▾`, `✓`, `…`, `+` or `☰`. Emojis are exempt.
- Use one icon set with one stroke width and one size scale.
- Give every icon-only button an `aria-label` and a tooltip.

## States

Design every interactive component in each of these states: hover, `focus-visible`, active, disabled, loading, empty and error.

- Never remove the focus ring. Style it with `:focus-visible` so it shows for keyboard users.
- Prevent layout shift. Skeletons match the final layout, async content has space reserved, and numbers that change use `tabular-nums`.

## Destructive actions

Run a destructive action right away and offer undo, for example in a toast. Keep a confirm dialog only for actions that cannot be undone.

## Input and access

- Make hit targets at least 44px on touch and at least 24px with a pointer, even when the visible icon is smaller.
- Support the keyboard: Esc closes overlays, dialogs trap focus and return it to the element that opened them, and Enter submits forms.
- Meet WCAG AA contrast. Never carry meaning with color alone. Pair it with an icon, text or shape.
- Use semantic color tokens (such as `surface`, `text-muted`, `danger`) instead of raw colors, so dark mode works.

## Symptoms of generated design

These patterns mark an interface as generated. Remove them when you find them.

- A one-side accent border on a rounded component.
- Purple or indigo gradients, and gradient text.
- A card inside a card.
- Border, shadow and background tint all on one element.
- Every block centered.
- An icon or badge next to every heading.
- Glassmorphism as the default surface.
