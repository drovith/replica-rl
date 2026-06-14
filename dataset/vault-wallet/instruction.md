# Replicate this website's design in HTML and CSS

You are given full-page screenshots of an existing multi-page website. Your goal
is **exact replication**: reproduce the target design as precisely as you can as
a static **HTML + CSS** site — the same layout, spacing, typography, colour, and
components. Functionality is out of scope and is not evaluated; design fidelity
is everything.

## What you're given
- `design/` — one full-page screenshot per page, captured in a desktop browser at
  **1440px** wide. These are your target.
- `assets/` — the image files the site uses. Use these for any imagery and
  reference them with relative paths like `assets/<filename>`.

## What to produce
Create exactly these pages in the current directory (`/app`), matching the
screenshots, and share a single stylesheet across them for consistency:

- `index.html` — Product  (target: `design/index.png`)
- `security.html` — Security  (target: `design/security.png`)
- `chains.html` — Chains & Features  (target: `design/chains.png`)
- `pricing.html` — Pricing  (target: `design/pricing.png`)
- `download.html` — Download  (target: `design/download.png`)

Match every page closely: the same header/navigation and footer, the same colour
palette and type scale, the same section layouts and components. The result will
be viewed at 1440px wide.
