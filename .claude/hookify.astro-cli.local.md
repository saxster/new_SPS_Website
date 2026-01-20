---
name: astro-cli
enabled: true
event: bash
pattern: astro\s+(add|build|dev|preview|check)|npx\s+astro
action: warn
---

**ASTRO CLI DETECTED - USE ASTRO-DEV SKILL**

You are running Astro CLI commands. Apply `astro-dev` skill guidance:

- **astro add**: Use official integrations (react, tailwind, mdx, sitemap)
- **astro build**: Verify output mode matches deployment target (static/server/hybrid)
- **astro check**: Run before commits to catch TypeScript errors
- **astro dev/preview**: Test client directives and View Transitions behavior

Deployment checklist:
- Correct adapter installed for target (vercel, cloudflare, netlify, node)
- Environment variables configured (PUBLIC_ prefix for client-side)
- Image domains configured in astro.config.mjs if using remote images
