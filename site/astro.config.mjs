import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://foci.rs',
  integrations: [
    starlight({
      title: 'FOCI',
      description:
        'Field Oriented Control Interface — Klipper-compatible MCU firmware for TMC4671 FOC servo controllers.',
      logo: {
        light: './src/assets/foci-icon-light.svg',
        dark: './src/assets/foci-icon-dark.svg',
      },
      favicon: '/favicon.svg',
      head: [
        {
          tag: 'link',
          attrs: {
            rel: 'icon',
            type: 'image/png',
            sizes: '32x32',
            href: '/favicon-32.png',
          },
        },
        {
          tag: 'link',
          attrs: {
            rel: 'icon',
            type: 'image/png',
            sizes: '16x16',
            href: '/favicon-16.png',
          },
        },
      ],
      customCss: ['./src/styles/custom.css'],
      sidebar: [
        { label: 'Home', link: '/' },
        {
          label: 'Getting Started',
          items: [
            { label: 'Installation', slug: 'getting-started/installation' },
            { label: 'Bring-up', slug: 'getting-started/bring-up' },
          ],
        },
        { label: 'Config Reference', slug: 'config-reference' },
        { label: 'Troubleshooting', slug: 'troubleshooting' },
      ],
    }),
  ],
});
