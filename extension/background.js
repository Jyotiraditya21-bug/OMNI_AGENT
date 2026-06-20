chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "send-to-omniagent",
    title: "Send to OmniAgent",
    contexts: ["selection"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "send-to-omniagent" && info.selectionText) {
    // Write selected content to active session storage
    await chrome.storage.session.set({ selectedText: info.selectionText });
    
    // Trigger opening of SidePanel
    if (chrome.sidePanel && typeof chrome.sidePanel.open === 'function') {
      await chrome.sidePanel.open({ windowId: tab.windowId });
    }
  }
});

// Handle clicking action icon
chrome.action.onClicked.addListener(async (tab) => {
  if (chrome.sidePanel && typeof chrome.sidePanel.open === 'function') {
    await chrome.sidePanel.open({ windowId: tab.windowId });
  }
});
