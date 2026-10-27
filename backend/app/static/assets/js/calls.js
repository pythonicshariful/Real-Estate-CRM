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
        if (window.prefillDateTime) window.prefillDateTime(document.getElementById('next-action-deadline'));
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

    // Toggle Outcome & Duration fields when Call Connected is checked/unchecked
    const callConnectedCheckbox = document.getElementById('call-connected');
    const connectedFieldsContainer = document.getElementById('connected-fields');
    if (callConnectedCheckbox && connectedFieldsContainer) {
        callConnectedCheckbox.addEventListener('change', () => {
            if (callConnectedCheckbox.checked) {
                connectedFieldsContainer.classList.remove('hidden');
            } else {
                connectedFieldsContainer.classList.add('hidden');
            }
        });
    }

    // Quick Notes Logic
    const callNotesTextarea = document.getElementById('call-notes');
    const quickNotesContainer = document.getElementById('quick-notes-container');

    async function loadQuickNotes() {
        if (!quickNotesContainer) return;
        try {
            const res = await fetch('/api/settings/quick_notes', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('crm_token')}` }
            });
            if (!res.ok) throw new Error('Failed to fetch quick notes');
            const data = await res.json();
            if (data && data.quick_notes) {
                quickNotesContainer.innerHTML = '';
                const notes = data.quick_notes.split(',').map(n => n.trim()).filter(n => n.length > 0);
                
                // Color cycling classes for buttons
                const colorClasses = [
                    'hover:bg-indigo-500/20 hover:text-indigo-400 hover:border-indigo-500/50',
                    'hover:bg-emerald-500/20 hover:text-emerald-400 hover:border-emerald-500/50',
                    'hover:bg-amber-500/20 hover:text-amber-400 hover:border-amber-500/50',
                    'hover:bg-rose-500/20 hover:text-rose-400 hover:border-rose-500/50',
                    'hover:bg-cyan-500/20 hover:text-cyan-400 hover:border-cyan-500/50'
                ];

                notes.forEach((noteText, idx) => {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = `quick-note-btn px-3 py-1.5 rounded-full bg-slate-800 border border-slate-700 text-xs font-medium text-slate-300 transition-colors ${colorClasses[idx % colorClasses.length]}`;
                    btn.textContent = noteText;
                    
                    btn.addEventListener('click', () => {
                        const currentText = callNotesTextarea.value.trim();
                        if (currentText) {
                            callNotesTextarea.value = currentText + '\n' + noteText;
                        } else {
                            callNotesTextarea.value = noteText;
                        }
                        callNotesTextarea.focus();
                    });
                    
                    quickNotesContainer.appendChild(btn);
                });
            }
        } catch (e) {
            console.error("Failed to load quick notes:", e);
        }
    }
    
    // Call loadQuickNotes to populate the buttons
    loadQuickNotes();

    // Activity Labels Logic
    async function loadActivityLabels() {
        const labelSelect = document.getElementById('call-activity-label');
        if (!labelSelect) return;
        try {
            const res = await fetch('/api/settings/activity-labels', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('crm_token')}` }
            });
            if (res.ok) {
                const labels = await res.json();
                labelSelect.innerHTML = '<option value="">-- No Label --</option>';
                labels.forEach(lbl => {
                    const opt = document.createElement('option');
                    opt.value = lbl.name;
                    opt.textContent = lbl.name;
                    labelSelect.appendChild(opt);
                });
            }
        } catch (e) {
            console.error("Failed to load activity labels:", e);
        }
    }
    loadActivityLabels();

    // ── Disposition popup (client requirement 3) ─────────────────────────
    // Picking an activity label/status in the Log Call modal immediately
    // opens this popup. Submitting it posts the CallLog (label + notes +
    // follow-up date + activity type) to /api/leads/<id>/calls; the backend
    // creates the persistent lead-linked Event in the same transaction.
    const dispositionModal = document.getElementById('disposition-modal');
    const dispositionModalContent = document.getElementById('disposition-modal-content');
    const dispositionForm = document.getElementById('disposition-form');
    let pendingDispositionLabel = '';
    const showDispositionModal = (label) => {
        if (!dispositionModal || !label) return;
        pendingDispositionLabel = label;
        const labelText = document.getElementById('disposition-label-text');
        if (labelText) labelText.textContent = label;
        if (dispositionForm) dispositionForm.reset();
        if (window.prefillDateTime) window.prefillDateTime(document.getElementById('disposition-next-date'));
        const activityType = document.getElementById('disposition-activity-type');
        if (activityType) activityType.value = 'Follow-up';
        dispositionModal.classList.remove('hidden');
        setTimeout(() => {
            dispositionModal.classList.remove('opacity-0');
            if (dispositionModalContent) dispositionModalContent.classList.remove('scale-95');
        }, 10);
    };
    const hideDispositionModal = () => {
        if (!dispositionModal) return;
        dispositionModal.classList.add('opacity-0');
        if (dispositionModalContent) dispositionModalContent.classList.add('scale-95');
        setTimeout(() => dispositionModal.classList.add('hidden'), 200);
    };
    const closeDispositionBtn = document.getElementById('close-disposition-modal');
    if (closeDispositionBtn) closeDispositionBtn.addEventListener('click', hideDispositionModal);
    const cancelDispositionBtn = document.getElementById('cancel-disposition-modal');
    if (cancelDispositionBtn) cancelDispositionBtn.addEventListener('click', hideDispositionModal);
    const labelSelect = document.getElementById('call-activity-label');
    if (labelSelect) {
        labelSelect.addEventListener('change', () => {
            if (labelSelect.value) showDispositionModal(labelSelect.value);
        });
    }
    if (dispositionForm) {
        dispositionForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const leadId = document.getElementById('call-lead-id') ? document.getElementById('call-lead-id').value : '';
            const notes = document.getElementById('disposition-notes').value.trim();
            const nextDateInput = document.getElementById('disposition-next-date');
            const activityType = document.getElementById('disposition-activity-type').value;
            if (!leadId) { window.showToast("No lead selected.", "error"); return; }
            if (window.requireDateTime && !window.requireDateTime(nextDateInput)) return;
            const nextDate = nextDateInput.value;
            try {
                const token = localStorage.getItem('crm_token');
                const res = await fetch(`/api/leads/${leadId}/calls`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        notes: notes || 'Disposition logged',
                        activity_label: pendingDispositionLabel,
                        next_action_deadline: nextDate,
                        next_action_type: activityType,
                        disposition_activity_type: activityType,
                        connected: true,
                    })
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) throw new Error(data.error || data.msg || "Failed to save disposition");
                window.showToast(data.event_id ? "Disposition saved & follow-up event created." : "Disposition saved.", "success");
                hideDispositionModal();
                hideCallModal();
                if (typeof loadLeads === 'function') loadLeads();
                else if (window.loadLeads) window.loadLeads();
            } catch (err) {
                window.showToast(err.message, "error");
            }
        });
    }

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

        const uploadProgressContainer = document.getElementById('upload-progress-container');
        const uploadProgressBar = document.getElementById('upload-progress-bar');
        const uploadProgressText = document.getElementById('upload-progress-text');
        
        if (uploadProgressContainer && document.getElementById('recording-file').files.length > 0) {
            uploadProgressContainer.classList.remove('hidden');
            uploadProgressBar.style.width = '0%';
            uploadProgressText.textContent = '0%';
        }

        try {
            const token = localStorage.getItem('crm_token');
            
            const data = await new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                xhr.open('POST', `/api/leads/${leadId}/calls`, true);
                xhr.setRequestHeader('Authorization', `Bearer ${token}`);
                
                xhr.upload.onprogress = (event) => {
                    if (event.lengthComputable && uploadProgressContainer) {
                        const percentComplete = Math.round((event.loaded / event.total) * 100);
                        uploadProgressBar.style.width = percentComplete + '%';
                        uploadProgressText.textContent = percentComplete + '%';
                    }
                };
                
                xhr.onload = () => {
                    try {
                        const responseData = JSON.parse(xhr.responseText);
                        if (xhr.status >= 200 && xhr.status < 300) {
                            resolve(responseData);
                        } else {
                            reject(new Error(responseData.msg || responseData.error || "Failed to log call"));
                        }
                    } catch (err) {
                        reject(new Error("Invalid server response"));
                    }
                };
                
                xhr.onerror = () => reject(new Error("Network Error"));
                xhr.send(formData);
            });
            
            if (data.upload_error) {
                window.showToast(`Call logged, but Cloud Storage upload failed: ${data.upload_error}`, "error");
            } else if (data.recording_url && data.recording_url.startsWith('http')) {
                window.showToast("Uploaded successfully", "success");
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
            window.showToast(error.message, "error");
        } finally {
            submitCallBtn.disabled = false;
            submitCallBtn.classList.remove('opacity-70', 'cursor-not-allowed');
            uploadSpinner.classList.add('hidden');
            
            const uploadProgressContainer = document.getElementById('upload-progress-container');
            if (uploadProgressContainer) {
                uploadProgressContainer.classList.add('hidden');
            }
        }
    });

    // Attach to existing 'Log Activity' buttons in leads.html (Hack for static HTML showcase)
    // In a dynamic app, these buttons would call showCallModal(lead.id) when rendering the list
    setTimeout(() => {
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
