"use strict";
const state = document.getElementById("state");
const details = document.getElementById("details");

async function refresh() {
  try {
    const result = await browser.runtime.sendMessage({type: "ui-status"});
    if (result.context) {
      state.textContent = "Monitoring: " + result.context;
      details.textContent = "Firefox tabs are saved locally when this context is active.";
    } else if (result.connected) {
      state.textContent = "Monitoring stopped";
      details.textContent = "Run ctx switch <context> to start capture.";
    } else {
      state.textContent = "Bridge disconnected";
      details.textContent = result.error || "Check the native messaging host and ctxd.";
    }
  } catch (error) {
    state.textContent = "Extension unavailable";
    details.textContent = String(error);
  }
}
document.getElementById("refresh").addEventListener("click", async () => {
  await browser.runtime.sendMessage({type: "resync"});
  await refresh();
});
void refresh();
