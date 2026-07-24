document.addEventListener('DOMContentLoaded', () => {
    const callModal = document.getElementById('call-modal');
    const callModalContent = document.getElementById('call-modal-content');
    const closeCallModalBtn = document.getElementById('close-call-modal');
    const cancelCallModalBtn = document.getElementById('cancel-call-modal');
    const callLogForm = document.getElementById('call-log-form');
    const uploadSpinner = document.getElementById('upload-spinner');
    const submitCallBtn = document.getElementById('submit-call-btn');

    // Function to show modal
    window.showCallModal = function(leadId) {
        document.getElementById('call-lead-id').value = leadId;
        callModal.classList.remove('hidden');
        // Small delay to allow display:block to apply before animating opacity
        setTimeout(() => {
            callModal.classList.remove('opacity-0');
            callModalContent.classList.remove('scale-95');
        }, 10);
    };

    // Function to hide modal
    function hideCallModal() {
        callModal.classList.add('opacity-0');
        callModalContent.classList.add('scale-95');
        setTimeout(() => {
            callModal.classList.add('hidden');
            callLogForm.reset();
        }, 200);
    }

    closeCallModalBtn.addEventListener('click', hideCallModal);
    cancelCallModalBtn.addEventListener('click', hideCallModal);

    // Quick Notes Logic
    const quickNoteBtns = document.querySelectorAll('.quick-note-btn');
    const callNotesTextarea = document.getElementById('call-notes');
    
    quickNoteBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const currentText = callNotesTextarea.value.trim();
            const noteText = btn.textContent;
            if (currentText) {
                callNotesTextarea.value = currentText + '\n' + noteText;
            } else {
                callNotesTextarea.value = noteText;
            }
            callNotesTextarea.focus();
        });
    });

    // Form submission
    callLogForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const leadId = document.getElementById('call-lead-id').value;
        if (!leadId) {
            window.showToast("No lead selected.", "error");
            return;
        }

        const formData = new FormData(callLogForm);

        // UI state: disable button, show spinner
        submitCallBtn.disabled = true;
        submitCallBtn.classList.add('opacity-70', 'cursor-not-allowed');
        uploadSpinner.classList.remove('hidden');

        try {
            const token = localStorage.getItem('crm_token');
            const response = await fetch(`/api/leads/${leadId}/calls`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData // Fetch API automatically sets Content-Type for FormData
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.msg || "Failed to log call");
            }

            const data = await response.json();
            
            if (data.recording_url && data.recording_url.startsWith('http')) {
                window.showToast("Call logged & recording uploaded to MEGA!", "success");
            } else if (data.recording_url) {
                window.showToast(`Call logged, but upload warning: ${data.recording_url}`, "error");
            } else {
                window.showToast("Call logged successfully.", "success");
            }

            hideCallModal();
            // Refresh data (assuming a loadLeads function exists or reload page)
            if (typeof loadLeads === 'function') {
                loadLeads();
            } else {
                window.location.reload();
            }

        } catch (error) {
            console.error('Call Log Error:', error);
            window.showToast(error.message, "error");
        } finally {
            // Restore UI state
            submitCallBtn.disabled = false;
            submitCallBtn.classList.remove('opacity-70', 'cursor-not-allowed');
            uploadSpinner.classList.add('hidden');
        }
    });

    // Attach to existing 'Log Activity' buttons in leads.html (Hack for static HTML showcase)
    // In a dynamic app, these buttons would call showCallModal(lead.id) when rendering the list
    setTimeout(() => {
        const logActivityBtns = document.querySelectorAll('button:contains("Log Activity"), button:contains("Call Now")');
        // Simple manual attach for the hardcoded leads in leads.html
        const leadCards = document.querySelectorAll('.chart-card');
        leadCards.forEach((card, index) => {
            const buttons = card.querySelectorAll('button');
            buttons.forEach(btn => {
                if(btn.textContent.includes('Log Activity') || btn.textContent.includes('Call Now')) {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        // Mock ID 1, 2, 3 based on index
                        showCallModal(index + 1);
                    });
                }
            });
        });
    }, 1000);
});
