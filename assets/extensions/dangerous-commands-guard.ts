import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { isToolCallEventType } from "@earendil-works/pi-coding-agent";

/**
 * Extension to protect against dangerous bash commands by asking for confirmation.
 */
export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    if (isToolCallEventType("bash", event)) {
      const command = event.input.command;

      const isRmRf = command.includes("rm -rf");
      const isGitPushForce = command.includes("git push") && (command.includes("--force") || command.includes("-f ")); // "-f " to avoid matching words like "file"

      if (isRmRf || isGitPushForce) {
        const type = isRmRf ? "rm -rf" : "git push --force";
        
        // Use ctx.ui.confirm to ask the user
        const ok = await ctx.ui.confirm(
          "Dangerous Command Detected",
          `The agent wants to run a dangerous command: \n\n${command}\n\nDo you want to allow this ${type} operation?`
        );

        if (!ok) {
          return { block: true, reason: `User blocked ${type} command.` };
        }
      }
    }
  });

  pi.on("session_start", async (_event, ctx) => {
    ctx.ui.notify("Dangerous command protection enabled (rm -rf, git push --force)", "info");
  });
}
