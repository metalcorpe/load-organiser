import '@fontsource/figtree/latin-400.css';
import '@fontsource/figtree/latin-ext-400.css';
import '@fontsource/figtree/latin-600.css';
import '@fontsource/figtree/latin-ext-600.css';
import '@fontsource/outfit/latin-600.css';
import '@fontsource/outfit/latin-ext-600.css';
import '@fontsource/outfit/latin-700.css';
import '@fontsource/outfit/latin-ext-700.css';
import '../src/lib/design/tokens-light.css';
import '../src/lib/design/tokens-dark.css';
// Storybook's theme switch sets data-theme; these win over the system setting.
import '../src/lib/design/tokens-dark-forced.css';
import '../src/lib/design/tokens-light-forced.css';
import '../src/app.css';
import { withThemeByDataAttribute } from '@storybook/addon-themes';
import type { Preview } from '@storybook/sveltekit';

const preview: Preview = {
	decorators: [
		withThemeByDataAttribute({
			themes: { light: 'light', dark: 'dark' },
			defaultTheme: 'light',
			attributeName: 'data-theme'
		})
	],
	parameters: {
		layout: 'padded',
		backgrounds: { disable: true },
		a11y: { test: 'error' }
	}
};

export default preview;
