document.addEventListener('DOMContentLoaded', () => {
    const leadsContainer = document.getElementById('leads-container');
    const drawer = document.getElementById('lead-drawer');
    const drawerContent = document.getElementById('lead-drawer-content');
    const closeDrawerBtn = document.getElementById('close-drawer-btn');
    const logCallBtn = document.getElementById('drawer-call-btn');
    const IS_ADMIN = localStorage.getItem('crm_role') === 'ADMIN';

    let currentLeadId = null;
    let allLeadsData = [];
    let filteredLeadsData = [];
    let currentPage = 1;
    let itemsPerPage = 20;

    // Helper: format dates
    const formatDate = (isoString) => {
        if (!isoString) return '--';
        const d = new Date(isoString);
        return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    };

    // Helper: Badge color for pipeline stage
    const getBadgeClass = (stage) => {
        if (!stage) return 'badge-new';
        if (['NEW'].includes(stage)) return 'badge-new';
        if (['NEGOTIATION', 'PROPOSAL_PRESENTED'].includes(stage)) return 'badge-active';
        if (['SOLD', 'RESERVATION_RECEIVED'].includes(stage)) return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
        if (['CLOSED_LOST', 'INVALID', 'DISQUALIFIED'].includes(stage)) return 'badge-overdue';
        return 'bg-slate-800 text-slate-300 border border-slate-700'; // Default
    };

    const toggleStar = async (id, isStarred) => {
        try {
            const token = localStorage.getItem('crm_token');
            const res = await fetch(`/api/leads/${id}/star`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_starred: isStarred })
            });
            if (res.ok) window.loadLeads();
        } catch (e) {
            console.error("Failed to toggle star", e);
        }
    };

    const toggleTemperature = async (id, currentTemp) => {
        const temps = ['COLD', 'WARM', 'HOT'];
        const nextTemp = temps[(temps.indexOf(currentTemp) + 1) % temps.length] || 'COLD';
        
        try {
            const token = localStorage.getItem('crm_token');
            const res = await fetch(`/api/leads/${id}/temperature`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ temperature: nextTemp })
            });
            if (res.ok) window.loadLeads();
        } catch (e) {
            console.error("Failed to toggle temperature", e);
        }
    };

    // Load leads
    window.loadLeads = async function() {
        try {
            const token = localStorage.getItem('crm_token');
            const res = await fetch('/api/leads/', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.status === 401) {
                if (window.showToast) window.showToast("Session expired. Please log in again.", "error");
                setTimeout(() => window.location.href = '/index.html', 2000);
                return;
            }
            if (!res.ok) throw new Error("Failed to fetch leads");
            // Check for owner filter from URL param
            const urlParams = new URLSearchParams(window.location.search);
            const ownerParam = urlParams.get('owner');
            
            let leads = await res.json();
            allLeadsData = leads;
            updateKPIs();
            
            // Apply URL owner filter if present
            if (ownerParam && IS_ADMIN) {
                allLeadsData = leads.filter(l => String(l.assigned_to_id) === ownerParam);
            }
            
            applyFilters();
        } catch (error) {
            console.error(error);
            if(window.showToast) window.showToast(error.message, 'error');
        }
    };

    function applyFilters() {
        const stageEl = document.getElementById('filter-stage');
        const tempEl = document.getElementById('filter-temp');
        const starredEl = document.getElementById('filter-starred');

        const stage = stageEl ? stageEl.value : '';
        const temp = tempEl ? tempEl.value : '';
        const starred = starredEl ? starredEl.checked : false;

        filteredLeadsData = allLeadsData.filter(lead => {
            if (stage && lead.pipeline_stage !== stage) return false;
            if (temp && lead.lead_temperature !== temp) return false;
            if (starred && !lead.is_starred) return false;
            return true;
        });

        currentPage = 1;
        renderPaginatedLeads();
    }

    function updateKPIs() {
        const todayStr = new Date().toISOString().split('T')[0];
        
        let newLeadsToday = 0;
        let slaOverdue = 0;
        let closedWon = 0;

        allLeadsData.forEach(lead => {
            if (lead.is_overdue) slaOverdue++;
            if (lead.pipeline_stage === 'WON') closedWon++;
            
            if (lead.created_at) {
                const leadDateStr = lead.created_at.split('T')[0];
                if (leadDateStr === todayStr && lead.pipeline_stage === 'NEW') {
                    newLeadsToday++;
                }
            }
        });

        const totalLeads = allLeadsData.length;

        // Update DOM
        const elNewLeads = document.getElementById('kpi-new-leads');
        const elSlaOverdue = document.getElementById('kpi-sla-overdue');
        const elTotalLeads = document.getElementById('kpi-total-leads');
        const elClosedWon = document.getElementById('kpi-closed-won');
        
        if (elNewLeads) elNewLeads.textContent = newLeadsToday;
        if (elSlaOverdue) elSlaOverdue.textContent = slaOverdue;
        if (elTotalLeads) elTotalLeads.textContent = totalLeads;
        if (elClosedWon) elClosedWon.textContent = closedWon;

        // Update SLA Banner
        const slaBanner = document.getElementById('sla-banner');
        const slaBannerText = document.getElementById('sla-banner-text');
        
        if (slaBanner && slaBannerText) {
            if (slaOverdue > 0) {
                slaBanner.classList.remove('hidden');
                slaBannerText.textContent = `${slaOverdue} lead${slaOverdue > 1 ? 's' : ''} breached the 5-minute Speed-to-Lead SLA — Immediate action required`;
            } else {
                slaBanner.classList.add('hidden');
            }
        }
    }

    function renderPaginatedLeads() {
        const start = (currentPage - 1) * itemsPerPage;
        const end = start + itemsPerPage;
        const pageData = filteredLeadsData.slice(start, end);
        
        renderLeads(pageData);
        updatePaginationControls();
    }

    function updatePaginationControls() {
        const infoEl = document.getElementById('pagination-info');
        const prevBtn = document.getElementById('page-prev-btn');
        const nextBtn = document.getElementById('page-next-btn');
        
        if (!infoEl || !prevBtn || !nextBtn) return;
        
        const total = filteredLeadsData.length;
        const totalPages = Math.ceil(total / itemsPerPage);
        const start = total === 0 ? 0 : (currentPage - 1) * itemsPerPage + 1;
        const end = Math.min(currentPage * itemsPerPage, total);
        
        infoEl.textContent = `Showing ${start} to ${end} of ${total}`;
        
        prevBtn.disabled = currentPage === 1;
        nextBtn.disabled = currentPage >= totalPages || total === 0;
    }

    // Pagination Listeners
    const itemsSelect = document.getElementById('items-per-page-select');
    if (itemsSelect) {
        itemsSelect.addEventListener('change', (e) => {
            itemsPerPage = parseInt(e.target.value, 10);
            currentPage = 1;
            renderPaginatedLeads();
        });
    }

    const prevBtn = document.getElementById('page-prev-btn');
    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                renderPaginatedLeads();
            }
        });
    }

    const nextBtn = document.getElementById('page-next-btn');
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            const totalPages = Math.ceil(filteredLeadsData.length / itemsPerPage);
            if (currentPage < totalPages) {
                currentPage++;
                renderPaginatedLeads();
            }
        });
    }
    
    // Filter Modal Listeners
    const filterBtn = document.getElementById('filter-btn');
    const filterModal = document.getElementById('filter-modal');
    const filterModalContent = document.getElementById('filter-modal-content');
    const closeFilterModal = document.getElementById('close-filter-modal');
    const filterForm = document.getElementById('filter-form');
    const clearFilterBtn = document.getElementById('clear-filter-btn');

    if (filterBtn && filterModal) {
        filterBtn.addEventListener('click', () => {
            filterModal.classList.remove('hidden');
            setTimeout(() => {
                filterModal.classList.remove('opacity-0');
                filterModalContent.classList.remove('scale-95');
            }, 10);
        });

        const hideFilterModal = () => {
            filterModal.classList.add('opacity-0');
            filterModalContent.classList.add('scale-95');
            setTimeout(() => filterModal.classList.add('hidden'), 200);
        };

        closeFilterModal.addEventListener('click', hideFilterModal);
        
        filterModal.addEventListener('click', (e) => {
            if (e.target === filterModal) hideFilterModal();
        });

        clearFilterBtn.addEventListener('click', () => {
            document.getElementById('filter-stage').value = '';
            document.getElementById('filter-temp').value = '';
            document.getElementById('filter-starred').checked = false;
        });

        filterForm.addEventListener('submit', (e) => {
            e.preventDefault();
            applyFilters();
            hideFilterModal();
        });
    }

    // Export functionality
    const exportBtn = document.getElementById('export-excel-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            if (filteredLeadsData.length === 0) {
                if (window.showToast) window.showToast("No data to export", "info");
                return;
            }
            
            // Build CSV
            const headers = ['ID', 'Name', 'Phone', 'Email', 'Source', 'Project', 'Stage', 'Temperature', 'Starred', 'Overdue', 'Created At'];
            const rows = filteredLeadsData.map(lead => {
                const c = lead.contact || {};
                return [
                    lead.id,
                    `"${c.full_name || ''}"`,
                    `"${c.phone || ''}"`,
                    `"${c.email || ''}"`,
                    `"${c.source || ''}"`,
                    `"${lead.project_name || ''}"`,
                    `"${lead.pipeline_stage || ''}"`,
                    `"${lead.lead_temperature || ''}"`,
                    lead.is_starred ? 'Yes' : 'No',
                    lead.is_overdue ? 'Yes' : 'No',
                    `"${lead.created_at || ''}"`
                ].join(',');
            });
            
            const csvContent = [headers.join(','), ...rows].join('\n');
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            
            const link = document.createElement("a");
            link.setAttribute("href", url);
            link.setAttribute("download", `Leads_Export_${new Date().toISOString().split('T')[0]}.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    }

    function renderLeads(leads) {
        if (!leadsContainer) return;
        leadsContainer.innerHTML = '';
        
        if (leads.length === 0) {
            leadsContainer.innerHTML = `<div class="text-center text-slate-500 py-10">No active leads found.</div>`;
            return;
        }

        leads.forEach(lead => {
            // Determine border color based on temperature or stage
            let borderClass = 'border-l-indigo-500';
            if (lead.lead_temperature === 'HOT') borderClass = 'border-l-rose-500';
            else if (lead.lead_temperature === 'WARM') borderClass = 'border-l-amber-500';
            
            // Name initials
            const contactName = lead.contact?.full_name || `Lead #${lead.id}`;
            const initials = contactName.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || 'L';

            const card = document.createElement('div');
            card.className = `chart-card border-l-4 ${borderClass} hover:bg-white/[0.03] cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 transition-colors`;
            
            card.innerHTML = `
                <div class="flex items-center gap-4">
                  <div class="w-12 h-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 font-bold text-sm shrink-0">
                    ${initials}
                  </div>
                  <div>
                    <div class="font-bold text-white text-sm flex items-center gap-2">
                        ${contactName}
                        <button class="star-btn hover:scale-110 transition-transform" data-id="${lead.id}" data-starred="${lead.is_starred}">
                            <svg class="w-4 h-4 ${lead.is_starred ? 'text-yellow-400 fill-current' : 'text-slate-500'}" viewBox="0 0 24 24" stroke="currentColor" fill="none"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/></svg>
                        </button>
                        <span class="badge ${getBadgeClass(lead.pipeline_stage)}">${lead.pipeline_stage || 'NEW'}</span>
                        <button class="temp-btn badge ${lead.lead_temperature === 'HOT' ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' : lead.lead_temperature === 'WARM' ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' : 'bg-blue-500/20 text-blue-400 border-blue-500/30'} hover:opacity-80 transition-opacity" data-id="${lead.id}" data-temp="${lead.lead_temperature}">
                            ${lead.lead_temperature || 'COLD'}
                        </button>
                        ${lead.is_overdue ? '<span class="badge badge-overdue">Overdue</span>' : ''}
                    </div>
                    <div class="text-[11px] text-slate-400 mt-1 flex flex-wrap gap-x-4 gap-y-1">
                      <span class="flex items-center gap-1" title="Phone">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>
                        ${lead.contact?.phone || '--'}
                      </span>
                      <span class="flex items-center gap-1" title="Email">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
                        ${lead.contact?.email || '--'}
                      </span>
                      ${lead.project_name ? `
                      <span class="flex items-center gap-1" title="Project">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
                        ${lead.project_name}
                      </span>` : ''}
                      <span class="flex items-center gap-1 text-slate-500" title="Added">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> 
                        ${formatDate(lead.created_at)}
                      </span>
                    </div>
                  </div>
                </div>
                <div class="flex flex-col md:flex-row gap-2 md:items-center">
                  ${IS_ADMIN && lead.assigned_to_name ? `
                    <div class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-semibold" style="background: ${lead.assigned_to_color || '#6366f1'}22; color: ${lead.assigned_to_color || '#6366f1'}; border: 1px solid ${lead.assigned_to_color || '#6366f1'}44">
                      <span class="w-2 h-2 rounded-full" style="background: ${lead.assigned_to_color || '#6366f1'}"></span>
                      ${lead.assigned_to_name}
                    </div>
                  ` : ''}
                  <button class="log-activity-btn btn-ghost px-3 py-2 rounded-lg text-xs font-medium border border-slate-700 hover:border-indigo-500 transition-colors" data-id="${lead.id}">
                    Log Activity
                  </button>
                  <button class="view-profile-btn btn-gradient px-4 py-2 rounded-lg text-xs font-semibold shadow-lg" data-id="${lead.id}">
                    View Profile
                  </button>
                </div>
            `;

            // Click entire card to open profile
            card.addEventListener('click', (e) => {
                const starBtn = e.target.closest('.star-btn');
                const tempBtn = e.target.closest('.temp-btn');
                
                if (starBtn) {
                    toggleStar(lead.id, starBtn.dataset.starred !== 'true');
                } else if (tempBtn) {
                    toggleTemperature(lead.id, tempBtn.dataset.temp);
                } else if (e.target.closest('.log-activity-btn')) {
                    if (window.showCallModal) window.showCallModal(lead.id);
                } else {
                    openDrawer(lead.id);
                }
            });

            leadsContainer.appendChild(card);
        });
    }

    // Drawer Logic
    const openDrawer = async (id) => {
        currentLeadId = id;
        drawer.classList.remove('hidden');
        // Wait a frame for transition
        requestAnimationFrame(() => {
            drawer.classList.remove('opacity-0');
            drawerContent.classList.remove('translate-x-full');
        });

        // Set Loading state
        document.getElementById('drawer-lead-name').textContent = "Loading Profile...";
        document.getElementById('drawer-timeline').innerHTML = '<div class="text-sm text-slate-500 ml-4">Loading timeline...</div>';
        
        try {
            const token = localStorage.getItem('crm_token');
            const res = await fetch(`/api/leads/${id}/profile`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.error || errData.msg || "Failed to fetch profile");
            }
            const data = await res.json();
            
            populateDrawer(data);
        } catch (err) {
            console.error(err);
            if (window.showToast) window.showToast(err.message, "error");
            closeDrawer();
        }
    };

    const closeDrawer = () => {
        drawer.classList.add('opacity-0');
        drawerContent.classList.add('translate-x-full');
        setTimeout(() => {
            drawer.classList.add('hidden');
            currentLeadId = null;
        }, 300);
    };

    if (closeDrawerBtn) closeDrawerBtn.addEventListener('click', closeDrawer);
    
    // Clicking outside drawer content closes it
    if (drawer) {
        drawer.addEventListener('click', (e) => {
            if (e.target === drawer) closeDrawer();
        });
    }

    if (logCallBtn) {
        logCallBtn.addEventListener('click', () => {
            if (currentLeadId && window.showCallModal) {
                window.showCallModal(currentLeadId);
            }
        });
    }

    const apptBtn = document.getElementById('drawer-appt-btn');
    const apptModal = document.getElementById('appt-modal');
    const apptModalContent = document.getElementById('appt-modal-content');
    
    const openApptModal = () => {
        if (!currentLeadId) return;
        document.getElementById('appt-form').reset();
        apptModal.classList.remove('hidden');
        requestAnimationFrame(() => {
            apptModal.classList.remove('opacity-0');
            apptModalContent.classList.remove('scale-95');
        });
    };
    
    const closeApptModal = () => {
        apptModal.classList.add('opacity-0');
        apptModalContent.classList.add('scale-95');
        setTimeout(() => {
            apptModal.classList.add('hidden');
        }, 200);
    };

    if (apptBtn) apptBtn.addEventListener('click', openApptModal);
    document.getElementById('close-appt-modal')?.addEventListener('click', closeApptModal);
    document.getElementById('cancel-appt-modal')?.addEventListener('click', closeApptModal);

    document.getElementById('appt-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!currentLeadId) return;
        
        const saveBtn = document.getElementById('save-appt-btn');
        const dt = document.getElementById('appt-datetime').value;
        const loc = document.getElementById('appt-location').value;
        const startIso = new Date(dt).toISOString();
        
        saveBtn.disabled = true;
        saveBtn.innerHTML = 'Scheduling...';
        
        try {
            const token = localStorage.getItem('crm_token');
            const res = await fetch(`/api/leads/${currentLeadId}/appointment`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ appointment_datetime: startIso, location: loc })
            });
            if (!res.ok) throw new Error("Failed to book appointment");
            if (window.showToast) window.showToast("Appointment Booked!", "success");
            closeApptModal();
            // Refresh drawer
            document.getElementById('drawer-timeline').innerHTML = '<div class="text-sm text-slate-500 ml-4">Loading timeline...</div>';
            const refreshRes = await fetch(`/api/leads/${currentLeadId}/profile`, { headers: { 'Authorization': `Bearer ${token}` } });
            populateDrawer(await refreshRes.json());
        } catch (err) {
            console.error(err);
            if (window.showToast) window.showToast("Error booking appointment", "error");
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerHTML = 'Schedule';
        }
    });

    // Tab Logic
    const tabs = document.querySelectorAll('.drawer-tab');
    const panes = document.querySelectorAll('.drawer-content-pane');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // reset all tabs
            tabs.forEach(t => {
                t.classList.remove('text-indigo-400', 'border-indigo-500');
                t.classList.add('text-slate-500', 'border-transparent');
            });
            // hide all panes
            panes.forEach(p => p.classList.add('hidden'));
            
            // set active tab
            tab.classList.remove('text-slate-500', 'border-transparent');
            tab.classList.add('text-indigo-400', 'border-indigo-500');
            // show target pane
            const target = tab.getAttribute('data-target');
            document.getElementById(target).classList.remove('hidden');
        });
    });

    // Add Note Logic
    const addNoteForm = document.getElementById('add-note-form');
    if (addNoteForm) {
        addNoteForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!currentLeadId) return;
            
            const content = document.getElementById('new-note-content').value;
            if (!content.trim()) return;
            
            const btn = document.getElementById('save-note-btn');
            btn.disabled = true;
            btn.textContent = 'Saving...';
            
            try {
                const token = localStorage.getItem('crm_token');
                const res = await fetch('/api/notes/', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: content, opportunity_id: currentLeadId })
                });
                
                if (!res.ok) throw new Error("Failed to save note");
                if (window.showToast) window.showToast("Note saved!", "success");
                addNoteForm.reset();
                
                // Refresh drawer to update notes
                const refreshRes = await fetch(`/api/leads/${currentLeadId}/profile`, { headers: { 'Authorization': `Bearer ${token}` } });
                populateDrawer(await refreshRes.json());
            } catch (err) {
                console.error(err);
                if (window.showToast) window.showToast("Error saving note", "error");
            } finally {
                btn.disabled = false;
                btn.textContent = 'Save Note';
            }
        });
    }

    function populateDrawer(data) {
        const c = data.contact || {};
        document.getElementById('drawer-lead-name').textContent = c.full_name || `Lead #${data.id}`;
        
        const starBtn = document.getElementById('drawer-star-btn');
        if (starBtn) {
            starBtn.dataset.starred = data.is_starred;
            const svg = starBtn.querySelector('svg');
            if (data.is_starred) {
                svg.classList.add('text-yellow-400', 'fill-current');
                svg.classList.remove('text-slate-500');
            } else {
                svg.classList.remove('text-yellow-400', 'fill-current');
                svg.classList.add('text-slate-500');
            }
            starBtn.onclick = () => {
                toggleStar(data.id, starBtn.dataset.starred !== 'true');
                const newStarred = starBtn.dataset.starred !== 'true';
                starBtn.dataset.starred = newStarred;
                if (newStarred) {
                    svg.classList.add('text-yellow-400', 'fill-current');
                    svg.classList.remove('text-slate-500');
                } else {
                    svg.classList.remove('text-yellow-400', 'fill-current');
                    svg.classList.add('text-slate-500');
                }
            };
        }
        
        const stageEl = document.getElementById('drawer-lead-stage');
        stageEl.textContent = data.pipeline_stage || 'NEW';
        stageEl.className = `badge ${getBadgeClass(data.pipeline_stage)}`;

        const tempEl = document.getElementById('drawer-lead-temp');
        if (tempEl) {
            tempEl.textContent = data.lead_temperature || 'COLD';
            tempEl.className = `px-2 py-0.5 rounded badge font-bold hover:opacity-80 transition-opacity ${data.lead_temperature === 'HOT' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : data.lead_temperature === 'WARM' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'}`;
            tempEl.onclick = async () => {
                await toggleTemperature(data.id, data.lead_temperature || 'COLD');
                openDrawer(data.id);
            };
        }

        document.getElementById('drawer-phone').textContent = c.phone || '--';
        document.getElementById('drawer-email').textContent = c.email || '--';
        document.getElementById('drawer-project').textContent = data.project_name || '--';
        document.getElementById('drawer-source').textContent = c.source || '--';

        // Render Timeline
        const tlContainer = document.getElementById('drawer-timeline');
        const notesContainer = document.getElementById('drawer-notes-list');
        const filesContainer = document.getElementById('drawer-files-list');
        tlContainer.innerHTML = '';
        notesContainer.innerHTML = '';
        filesContainer.innerHTML = '';
        
        if (!data.timeline || data.timeline.length === 0) {
            tlContainer.innerHTML = '<div class="text-sm text-slate-500 ml-4">No activity history.</div>';
            notesContainer.innerHTML = '<div class="text-sm text-slate-500">No notes yet.</div>';
            filesContainer.innerHTML = '<div class="text-sm text-slate-500">No files or recordings.</div>';
            return;
        }

        let noteCount = 0;
        let fileCount = 0;

        data.timeline.forEach(item => {
            // 1. Populate Timeline Tab
            const tlItem = document.createElement('div');
            tlItem.className = 'relative pl-6';
            
            // Dot
            const dot = document.createElement('div');
            dot.className = 'absolute -left-[5px] top-1.5 w-2.5 h-2.5 rounded-full border-2 border-[#0a0a14]';
            
            let contentHtml = '';
            
            if (item.type === 'CALL') {
                dot.classList.add(item.connected ? 'bg-emerald-500' : 'bg-rose-500');
                contentHtml = `
                    <div class="text-xs font-semibold text-white mb-0.5">Call Logged <span class="text-slate-500 font-normal ml-2">${formatDate(item.date)}</span></div>
                    <div class="text-xs text-slate-400 mb-1">Status: <span class="${item.connected ? 'text-emerald-400' : 'text-rose-400'}">${item.connected ? 'Connected' : 'Not Connected'}</span></div>
                    ${item.notes ? `<div class="text-xs text-slate-300 bg-slate-800/50 p-2 rounded border border-slate-700/50 mt-1">${item.notes}</div>` : ''}
                    ${item.recording_url ? `<a href="${item.recording_url}" target="_blank" class="inline-flex items-center gap-1 text-[10px] text-indigo-400 hover:text-indigo-300 mt-2 bg-indigo-500/10 px-2 py-1 rounded-full"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/></svg> Play Recording</a>` : ''}
                `;
                
                // 2. Populate Files Tab
                if (item.recording_url) {
                    fileCount++;
                    filesContainer.innerHTML += `
                        <div class="bg-slate-900/50 border border-slate-800 rounded-xl p-3 flex justify-between items-center hover:border-slate-700 transition-colors">
                            <div class="flex items-center gap-3">
                                <div class="w-8 h-8 rounded bg-indigo-500/20 flex items-center justify-center text-indigo-400">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/></svg>
                                </div>
                                <div>
                                    <div class="text-xs font-semibold text-slate-200">Call Recording</div>
                                    <div class="text-[10px] text-slate-500">${formatDate(item.date)}</div>
                                </div>
                            </div>
                            <a href="${item.recording_url}" target="_blank" class="text-[10px] font-semibold bg-indigo-500/10 text-indigo-400 px-3 py-1.5 rounded-lg hover:bg-indigo-500/20 transition-colors">Listen / Download</a>
                        </div>
                    `;
                }

            } else if (item.type === 'NOTE') {
                dot.classList.add('bg-amber-400');
                contentHtml = `
                    <div class="text-xs font-semibold text-white mb-0.5">Note Added <span class="text-slate-500 font-normal ml-2">${formatDate(item.date)}</span></div>
                    <div class="text-xs text-slate-300 bg-slate-800/50 p-2 rounded border border-slate-700/50 mt-1">${item.content}</div>
                `;
                
                // 3. Populate Notes Tab
                noteCount++;
                notesContainer.innerHTML += `
                    <div class="bg-slate-900/50 border border-slate-800 rounded-xl p-3.5 relative hover:border-slate-700 transition-colors">
                        <div class="flex items-center gap-2 mb-2">
                            <div class="w-5 h-5 rounded-full bg-amber-500/20 flex items-center justify-center text-amber-500"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg></div>
                            <div class="text-[10px] text-slate-400 font-medium">${formatDate(item.date)}</div>
                        </div>
                        <div class="text-xs text-slate-300 whitespace-pre-wrap">${item.content}</div>
                    </div>
                `;

            } else if (item.type === 'STAGE_CHANGE') {
                dot.classList.add('bg-indigo-500');
                contentHtml = `
                    <div class="text-xs font-semibold text-white mb-0.5">Stage Changed <span class="text-slate-500 font-normal ml-2">${formatDate(item.date)}</span></div>
                    <div class="text-xs text-slate-400">From <span class="text-slate-300">${item.from_stage}</span> to <span class="text-indigo-400">${item.to_stage}</span></div>
                    ${item.notes ? `<div class="text-xs text-slate-500 mt-1">${item.notes}</div>` : ''}
                `;
            } else if (item.type === 'APPOINTMENT') {
                dot.classList.add('bg-violet-500');
                contentHtml = `
                    <div class="text-xs font-semibold text-white mb-0.5">Appointment <span class="text-slate-500 font-normal ml-2">${formatDate(item.date)}</span></div>
                    <div class="text-xs text-slate-400">Scheduled for <span class="text-violet-400">${formatDate(item.appointment_datetime)}</span></div>
                    <div class="text-xs text-slate-500">Status: ${item.status} ${item.location ? `| Loc: ${item.location}` : ''}</div>
                `;
            }

            tlItem.appendChild(dot);
            
            const contentDiv = document.createElement('div');
            contentDiv.innerHTML = contentHtml;
            tlItem.appendChild(contentDiv);
            
            tlContainer.appendChild(tlItem);
        });
        
        if (noteCount === 0) notesContainer.innerHTML = '<div class="text-sm text-slate-500">No notes yet.</div>';
        if (fileCount === 0) filesContainer.innerHTML = '<div class="text-sm text-slate-500">No files or recordings.</div>';
    }

    // Add Lead Modal Logic
    const addLeadBtn = document.getElementById('add-lead-btn');
    const addLeadModal = document.getElementById('add-lead-modal');
    const addLeadModalContent = document.getElementById('add-lead-modal-content');
    const closeAddLeadBtn = document.getElementById('close-add-lead-btn');
    const cancelAddLeadBtn = document.getElementById('cancel-add-lead-btn');
    const addLeadForm = document.getElementById('add-lead-form');

    const openAddLeadModal = () => {
        addLeadForm.reset();
        addLeadModal.classList.remove('hidden');
        requestAnimationFrame(() => {
            addLeadModal.classList.remove('opacity-0');
            addLeadModalContent.classList.remove('scale-95');
        });
    };

    const closeAddLeadModal = () => {
        addLeadModal.classList.add('opacity-0');
        addLeadModalContent.classList.add('scale-95');
        setTimeout(() => {
            addLeadModal.classList.add('hidden');
        }, 200);
    };

    if (addLeadBtn) addLeadBtn.addEventListener('click', openAddLeadModal);
    if (closeAddLeadBtn) closeAddLeadBtn.addEventListener('click', closeAddLeadModal);
    if (cancelAddLeadBtn) cancelAddLeadBtn.addEventListener('click', closeAddLeadModal);
    
    if (addLeadForm) {
        addLeadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(addLeadForm);
            const data = Object.fromEntries(formData.entries());
            
            const submitBtn = document.getElementById('save-add-lead-btn');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<svg class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Saving...';
            submitBtn.disabled = true;

            try {
                const token = localStorage.getItem('crm_token');
                const res = await fetch('/api/leads/', {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });
                
                if (res.status === 401) {
                    throw new Error("Session expired. Please log in again.");
                }
                if (!res.ok) {
                    const errData = await res.json();
                    throw new Error(errData.error || errData.msg || "Failed to create lead");
                }
                
                if (window.showToast) window.showToast("Lead created successfully!", "success");
                closeAddLeadModal();
                loadLeads();
            } catch (err) {
                console.error(err);
                if (window.showToast) window.showToast(err.message, "error");
                if (err.message.includes("Session expired")) {
                    setTimeout(() => window.location.href = '/index.html', 2000);
                }
            } finally {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        });
    }

    // Initial Load
    loadLeads();
});
