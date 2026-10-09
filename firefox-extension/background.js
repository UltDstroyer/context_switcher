"use strict";

// Only inspect tabs while a ctx context is active. Nothing leaves this machine.
const HOST_NAME = "org.ctx_switcher.firefox";
const CAPTURE_DELAY_MS = 250;
let nativePort = null;
let connected = false;
let activeContext = null;
let errorText = null;
let reconnectTimer = null;
let captureTimer = null;
let captureRunning = false;
let capturePending = false;

function requestStatus() {
  if (!nativePort) return;
  try {
    nativePort.postMessage({type: "status"});
  } catch (error) {
    errorText = String(error);
  }
}

function connect() {
  if (nativePort) return;
  try {
    const port = browser.runtime.connectNative(HOST_NAME);
    nativePort = port;
    port.onMessage.addListener((message) => {
      if (message.type === "status") {
        const previous = activeContext;
        connected = message.connected === true;
        activeContext = connected ? (message.context || null) : null;
        errorText = connected ? null : "ctxd is not running";
        if (activeContext && previous !== activeContext) {
          scheduleCapture(0);
        }
      } else if (message.type === "ack" && !message.accepted) {
        requestStatus();
      } else if (message.type === "error") {
        errorText = message.message || "Native host error";
      }
    });
    port.onDisconnect.addListener(() => {
      if (nativePort !== port) return;
      const lastError = browser.runtime.lastError;
      errorText = lastError ? lastError.message : "Native host disconnected";
      nativePort = null;
      connected = false;
      activeContext = null;
      if (!reconnectTimer) {
        reconnectTimer = setTimeout(() => {
          reconnectTimer = null;
          connect();
        }, 2000);
      }
    });
    requestStatus();
  } catch (error) {
    errorText = String(error);
    if (!reconnectTimer) {
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connect();
      }, 2000);
    }
  }
}

function scheduleCapture(delay = CAPTURE_DELAY_MS) {
  if (!activeContext || !nativePort) return;
  capturePending = true;
  if (captureTimer) clearTimeout(captureTimer);
  captureTimer = setTimeout(() => {
    captureTimer = null;
    void flushCapture();
  }, delay);
}

async function flushCapture() {
  if (captureRunning) return;
  captureRunning = true;
  try {
    while (capturePending && activeContext && nativePort) {
      capturePending = false;
      const context = activeContext;
      // windowTypes excludes popups; incognito is excluded by manifest and filter.
      const windows = await browser.windows.getAll({
        populate: true,
        windowTypes: ["normal"]
      });
      if (!nativePort || activeContext !== context) continue;
      const snapshot = {
        schema_version: 1,
        adapter: "firefox",
        captured_at: new Date().toISOString(),
        windows: windows
          .filter((win) => !win.incognito)
          .map((win) => ({
            id: win.id,
            focused: Boolean(win.focused),
            tabs: (win.tabs || [])
              .filter((tab) => !tab.incognito)
              .sort((a, b) => a.index - b.index)
              .map((tab) => ({
                id: tab.id,
                index: tab.index,
                url: tab.url || null,
                title: tab.title || "",
                active: Boolean(tab.active),
                pinned: Boolean(tab.pinned),
                highlighted: Boolean(tab.highlighted),
                muted: Boolean(tab.mutedInfo && tab.mutedInfo.muted),
                discarded: Boolean(tab.discarded),
                cookie_store_id: tab.cookieStoreId || null
              }))
          }))
      };
      nativePort.postMessage({type: "snapshot", context, snapshot});
    }
  } catch (error) {
    errorText = "Firefox capture failed: " + String(error);
  } finally {
    captureRunning = false;
    if (capturePending && activeContext) scheduleCapture();
  }
}

const markChanged = () => scheduleCapture();
browser.tabs.onCreated.addListener(markChanged);
browser.tabs.onRemoved.addListener(markChanged);
browser.tabs.onUpdated.addListener(markChanged);
browser.tabs.onMoved.addListener(markChanged);
browser.tabs.onActivated.addListener(markChanged);
browser.tabs.onAttached.addListener(markChanged);
browser.tabs.onDetached.addListener(markChanged);
// Firefox does not support this Chromium-only event on all versions.
if (browser.tabs.onReplaced) browser.tabs.onReplaced.addListener(markChanged);
browser.windows.onCreated.addListener(markChanged);
browser.windows.onRemoved.addListener(markChanged);
browser.windows.onFocusChanged.addListener(markChanged);

browser.runtime.onMessage.addListener((message) => {
  if (message.type === "ui-status") {
    return Promise.resolve({connected, context: activeContext, error: errorText});
  }
  if (message.type === "resync") {
    requestStatus();
    scheduleCapture(0);
    return Promise.resolve({queued: Boolean(activeContext)});
  }
  return false;
});

connect();
