---
name: use-astro-skill
enabled: true
event: file
pattern: \.astro$|astro\.config\.(mjs|ts)$|content\.config\.ts$|src/content/
action: warn
---

**ASTRO FILE DETECTED - USE ASTRO-DEV SKILL**

You are working with an Astro file. You MUST apply the `astro-dev` skill patterns:

1. **Islands Architecture**: Ship zero JS by default. Only use client directives for interactive components.
2. **Client Directives**: Use appropriate directive (client:visible, client:idle) - NOT client:load by default.
3. **Content Collections**: Use Zod schemas in content.config.ts for type safety.
4. **Layouts**: Keep layouts as .astro files, not framework components.
5. **Images**: Use astro:assets for optimization, not raw <img> tags.

If you haven't already, invoke the full skill with: `Skill tool → astro-dev`

Key anti-patterns to avoid:
- Using client:load on everything (use client:visible/idle instead)
- Mapping arrays to spawn N framework islands (use single wrapper)
- Wrapping layouts in React/Vue/Svelte components
