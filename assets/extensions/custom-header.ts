import type { ExtensionAPI, Theme } from "@earendil-works/pi-coding-agent";

const logo = [
	"                          ",
	"________________   ______ ",
	"___  __ \\  _ \\_ | / /  _ \\",
	"__  /_/ /  __/_ |/ //  __/",
	"_  .___/\\___/_____/ \\___/ ",
	"/_/"
];

export default function (pi: ExtensionAPI) {
	pi.on("session_start", async (_event, ctx) => {
		if (ctx.hasUI) {
			ctx.ui.setHeader((_tui, theme) => {
				return {
					render(_width: number): string[] {
						return logo.map(line => theme.fg("accent", line));
					},
					invalidate() {},
				};
			});
		}
	});
}
