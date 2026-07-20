export function initKanban(leads) {
  console.log('Initializing Kanban board', leads);
}

export function handleDrop(cardId, targetColumn) {
  console.log(`Moved ${cardId} to ${targetColumn}`);
  window.showToast && window.showToast(`Lead moved successfully`, 'success');
}

export function showManagerLabels(show) {
  // Add class logic
}

document.addEventListener('DOMContentLoaded', () => {
  // auto refresh every 2 mins
  setInterval(() => {
    // console.log('Refreshing kanban...');
  }, 120000);
});
