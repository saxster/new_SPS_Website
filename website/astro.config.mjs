// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import preact from '@astrojs/preact';
import tailwindcss from '@tailwindcss/vite';
import node from '@astrojs/node';
import clerk from '@clerk/astro';
import rehypeCallouts from 'rehype-callouts';

// https://astro.build/config
// Hybrid rendering (Astro 5.x): Default is static, but pages with `prerender = false` are SSR
// Static pages: homepage, about, services, blog, tools, sectors
// Dynamic pages: /news, /intelligence (breaking news appears instantly without rebuild)
export default defineConfig({
  site: process.env.PUBLIC_SITE_URL || 'https://sukhi.in',
  // Note: Astro 5.x defaults to static with hybrid capability built-in
  // Use `export const prerender = false` in individual pages for SSR
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