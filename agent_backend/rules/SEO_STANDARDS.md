# SEO & Accessibility Standards (SPS)

## 1. Meta Tags (Astro Frontmatter)
All pages MUST include:
- `title`: Descriptive, unique, includes "SPS Security".
- `description`: 150-160 characters, summarising content.
- `og:image`: Default to `/images/sps_social_card.jpg` if no specific image.
- `canonical`: Self-referencing URL.

## 2. Heading Hierarchy
- `<h1>`: ONE and ONLY ONE per page. Must match the Title.
- `<h2> - <h6>`: Properly nested. Never skip levels (e.g., h2 to h4).

## 3. Images
- `alt`: MANDATORY for all `<img>` tags.
- `width` & `height`: Must be specified to prevent layout shift (CLS).
- Format: Use `.webp` where possible.

## 4. Accessibility (A11y)
- **Contrast**: Text must meet WCAG AA (4.5:1).
- **Focus**: Interactive elements must have visible focus states (`focus:ring`).
- **Labels**: `aria-label` required for icon-only buttons (e.g., Hamburger, Social Links).

## 5. Performance
- **Scripts**: Use `defer` or `type="module"`.
- **Fonts**: Preconnect to Google Fonts.
