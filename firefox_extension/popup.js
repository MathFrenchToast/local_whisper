// popup.js
const btnRecord = document.getElementById('btn-record');
const btnShortcuts = document.getElementById('btn-shortcuts');
const statusDiv = document.getElementById('status');

// Gestion du bouton d'enregistrement (délégué à la page active)
btnRecord.addEventListener('click', async () => {
    try {
        const tabs = await browser.tabs.query({active: true, currentWindow: true});
        
        if (tabs.length > 0) {
            await browser.tabs.sendMessage(tabs[0].id, {action: "toggle_recording"});
            window.close();
        } else {
            statusDiv.textContent = "Aucun onglet actif trouvé.";
        }
    } catch (error) {
        console.error("Erreur:", error);
        statusDiv.textContent = "Erreur : Impossible de contacter la page.\nEssayez de rafraîchir la page (F5).";
        statusDiv.style.color = "red";
    }
});

// Gestion du bouton de raccourcis
btnShortcuts.addEventListener('click', () => {
    // Ouvrir un nouvel onglet vers la gestion des extensions
    // Note: Firefox ne permet pas d'ouvrir directement le modal des raccourcis via URL,
    // mais on peut ouvrir la page des addons.
    browser.tabs.create({url: "about:addons"});
    statusDiv.textContent = "1. Cliquez sur la roue crantée ⚙️\n2. 'Gérer les raccourcis'";
});

