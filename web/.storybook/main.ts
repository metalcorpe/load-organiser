import type { StorybookConfig } from '@storybook/sveltekit';

// Local only (owner decision 2026-11-11): `npm run storybook`, nothing is published.
const config: StorybookConfig = {
	stories: ['../src/**/*.mdx', '../src/**/*.stories.ts'],
	addons: ['@storybook/addon-docs', '@storybook/addon-a11y', '@storybook/addon-themes'],
	framework: { name: '@storybook/sveltekit', options: {} },
	core: { disableTelemetry: true }
};

export default config;
