export function loadLeads(filters = {}) {
  // Mock function
  console.log('Loading leads with filters:', filters);
}

export function openCallLogModal(leadId) {
  const modal = document.getElementById('call-modal');
  if (modal) modal.classList.remove('hidden');
}

export function submitCallLog(formData) {
  console.log('Submitting call log:', formData);
  const modal = document.getElementById('call-modal');
  if (modal) modal.classList.add('hidden');
  window.showToast && window.showToast('Call logged successfully', 'success');
}

document.addEventListener('DOMContentLoaded', () => {
  // Set overdue check every 60s
  setInterval(() => {
    // console.log('Checking for overdue leads...');
  }, 60000);
});
