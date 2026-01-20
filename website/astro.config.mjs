// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import preact from '@astrojs/preact';
import tailwindcss from '@tailwindcss/vite';
import node from '@astrojs/node';
import clerk from '@clerk/astro';
import rehypeCallouts from 'rehype-callouts';

// https://astro.build/config
// Note: In Astro 5.x, hybrid rendering is default behavior with `output: 'static'`
// Pages use SSG by default; add `export const prerender = false` for SSR pages
// Server Islands are now a stable feature (no longer experimental)
export default defineConfig({
  site: 'https://sps-security.com', // Placeholder domain for production build
  adapter: node({
    mode: 'standalone'
  }),
  integrations: [
    sitemap(),
    preact(),
    clerk({
      afterSignInUrl: '/dashboard',
      afterSignUpUrl: '/dashboard',
    }),
  ],
  markdown: {
    rehypePlugins: [rehypeCallouts],
  },
  vite: {
    plugins: [tailwindcss()]
  },
});