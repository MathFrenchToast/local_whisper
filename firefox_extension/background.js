// background.js
browser.commands.onCommand.addListener((command) => {
    if (command === "toggle-recording") {
        browser.tabs.query({active: true, currentWindow: true}).then((tabs) => {
            if (tabs.length > 0) {
                browser.tabs.sendMessage(tabs[0].id, {action: "toggle_recording"});
            }
        });
    }
});
