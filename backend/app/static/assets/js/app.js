// ── Datetime-local helpers ──────────────────────────────────────────
// Browsers require EVERY segment of a datetime-local input (date + hour +
// minute + AM/PM). A half-filled field reports an empty value and native
// validation blocks submit with a cryptic bubble, so: (a) prefill a valid
// default, and (b) validate in JS with a friendly toast instead.
function defaultDateTimeLocal(now) {
  const d = new Date(now == null ? Date.now() : now);
  d.setDate(d.getDate() + 1);
  d.setHours(10, 0, 0, 0);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
window.defaultDateTimeLocal = defaultDateTimeLocal;

// Fill a datetime-local input with tomorrow 10:00 AM, only when empty.
window.prefillDateTime = function (input) {
  if (input && !input.value) input.value = defaultDateTimeLocal();
};

// Friendly validation for a datetime-local input: toast + focus when the
// date/time is missing or incomplete. Returns true when it holds a value.
window.requireDateTime = function (input) {
  if (!input || !input.value || Number.isNaN(new Date(input.value).getTime())) {
    if (window.showToast) window.showToast('Please pick a date and a time — the time was left blank.', 'error');
    if (input) input.focus();
    return false;
  }
  return true;
};

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
