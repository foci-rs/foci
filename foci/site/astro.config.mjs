import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://foci.rs',
  integrations: [
    starlight({
      title: 'FOCI',
      description:
        'Field Oriented Control Interface — Klipper-compatible MCU firmware for TMC4671 FOC servo controllers.',
      sidebar: [],
    }),
  ],
});
