import type { Meta, StoryObj } from "@storybook/sveltekit";
import DropzoneLocation from "./DropzoneLocation.svelte";

const meta = {
	title: "Directory/Dropzone location",
	component: DropzoneLocation,
	tags: ["autodocs"],
	parameters: {
		docs: {
			description: {
				component:
					'Where a dropzone is, in the order a visitor uses it: the place, a "View on map" link (a plain link to OpenStreetMap; nothing loads on the page), then the raw coordinates folded away with a Copy button where a clipboard is available. The point is the listed location, never called an entrance or landing area.',
			},
		},
	},
	args: { place: "Empuriabrava, Spain", latitude: 42.25857, longitude: 3.137 },
} satisfies Meta<typeof DropzoneLocation>;

export default meta;
type Story = StoryObj<typeof meta>;

export const WithMapPoint: Story = { name: "With a map point" };

export const NoMapPoint: Story = {
	name: "No map point",
	args: { place: "Spain", latitude: null, longitude: null },
};
