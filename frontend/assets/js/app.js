window.showToast = function(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast glass ${type === 'error' ? 'border-red-500 bg-red-500/20' : 'border-indigo-500 bg-indigo-500/20'}`;
  toast.innerHTML = `<span class="text-sm font-medium text-white">${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Global search Ctrl+K
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.key === 'k') {
    e.preventDefault();
    // open search modal
    window.showToast('Search palette opening...', 'info');
  }
});
