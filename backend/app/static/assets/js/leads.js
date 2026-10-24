document.addEventListener('DOMContentLoaded', () => {
    const leadsContainer = document.getElementById('leads-container');
    const drawer = document.getElementById('lead-drawer');
    const drawerContent = document.getElementById('lead-drawer-content');
    const closeDrawerBtn = document.getElementById('close-drawer-btn');
    const logCallBtn = document.getElementById('drawer-call-btn');
    const IS_ADMIN = localStorage.getItem('crm_role') === 'ADMIN';

    let currentLeadId = null;
    let currentLeadData = null;
    let allLeadsData = [];
    let filteredLeadsData = [];
    let currentPage = 1;
    let itemsPerPage = 20;

    // Helper: jump to a field — smooth-scroll it into view, focus it and
    // flash a highlight ring, so every button lands the user on its field.
    const jumpToField = (el) => {
        if (!el) return;
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        try { el.focus({ preventScroll: true }); } catch (e) { el.focus(); }
        el.classList.add('ring-2', 'ring-indigo-500');
        setTimeout(() => el.classList.remove('ring-2', 'ring-indigo-500'), 1800);
    };
    const focusFirstField = (container) => {
        if (!container) return;
        const el = container.querySelector('input:not([type=hidden]):not([disabled]), select:not([disabled]), textarea:not([disabled])');
        jumpToField(el);
    };

    // Helper: format dates in Bangladesh Standard Time (Asia/Dhaka)
    const formatDate = (isoString) => {
        if (!isoString) return '--';
        // Normalize UTC date string if missing tz offset
        let cleanStr = isoString;
        if (typeof cleanStr === 'string' && !cleanStr.endsWith('Z') && !cleanStr.includes('+')) {
            cleanStr += 'Z';
        }
        const d = new Date(cleanStr);
        return d.toLocaleString('en-US', {
            timeZone: 'Asia/Dhaka',
            day: 'numeric',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
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
            const leadIdParam = urlParams.get('lead_id');
            
            let leads = await res.json();
            allLeadsData = leads;
            updateKPIs();
            
            // Set initial filter dropdown value if URL param is present
            if (ownerParam) {
                const ownerFilter = document.getElementById('filter-owner');
                if (ownerFilter) ownerFilter.value = ownerParam;
            }
            
            applyFilters();

            if (leadIdParam) {
                const leadId = parseInt(leadIdParam, 10);
                if (!isNaN(leadId)) {
                    openDrawer(leadId);
                }
            }
        } catch (error) {
            console.error(error);
            if(window.showToast) window.showToast(error.message, 'error');
        }
    };

    function applyFilters() {
        const stageEl = document.getElementById('filter-stage');
        const tempEl = document.getElementById('filter-temp');
        const starredEl = document.getElementById('filter-starred');
        const ownerEl = document.getElementById('filter-owner');

        const stage = stageEl ? stageEl.value : '';
        const temp = tempEl ? tempEl.value : '';
        const starred = starredEl ? starredEl.checked : false;
        const owner = ownerEl ? ownerEl.value : '';

        filteredLeadsData = allLeadsData.filter(lead => {
            if (stage && lead.pipeline_stage !== stage) return false;
            if (temp && lead.lead_temperature !== temp) return false;
            if (starred && !lead.is_starred) return false;
            if (owner === 'none') {
                if (lead.assigned_to_id !== null) return false;
            } else if (owner && String(lead.assigned_to_id) !== owner) {
                return false;
            }
            return true;
        });

        currentPage = 1;
        renderPaginatedLeads();
    }

    function updateKPIs() {
        // "Today" in Bangladesh time, not UTC (UTC date flips 6h early)
        const todayStr = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Dhaka' });
        
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
            setTimeout(() => jumpToField(document.getElementById('filter-stage')), 250);
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
            const ownerFilter = document.getElementById('filter-owner');
            if (ownerFilter) ownerFilter.value = '';
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
            const headers = ['ID', 'Name', 'Phone', 'Email', 'Source', 'Project', 'Stage', 'Temperature', 'Lead Owner', 'Starred', 'Overdue', 'Created At'];
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
                    `"${lead.assigned_to_name || 'Unassigned'}"`,
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
            // Colour-code every lead by the Lead Owner it belongs to
            const ownerColor = lead.assigned_to_color || '#14B8A6';
            const ownerName = lead.assigned_to_name || 'Unassigned';
            
            // Name initials
            const contactName = lead.contact?.full_name || `Lead #${lead.id}`;
            const initials = contactName.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || 'L';

            // Calculate lead age (M-04)
            let leadAgeText = '';
            if (lead.created_at) {
                const diffMs = Date.now() - new Date(lead.created_at).getTime();
                const diffHrs = Math.max(0, Math.floor(diffMs / (1000 * 60 * 60)));
                const diffDays = Math.floor(diffHrs / 24);
                leadAgeText = diffDays > 0 ? `${diffDays}d ${diffHrs % 24}h` : `${diffHrs}h`;
            }

            // Priority badge (M-04)
            const prio = (lead.priority || 'MEDIUM').toUpperCase();
            let prioClass = 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30';
            if (prio === 'URGENT') prioClass = 'bg-rose-500/20 text-rose-300 border-rose-500/40';
            else if (prio === 'HIGH') prioClass = 'bg-amber-500/20 text-amber-300 border-amber-500/40';
            else if (prio === 'LOW') prioClass = 'bg-slate-800 text-slate-400 border-slate-700';

            const card = document.createElement('div');
            card.className = 'chart-card hover:bg-white/[0.03] cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 transition-colors';
            card.style.borderLeft = `4px solid ${ownerColor}`;
            
            card.innerHTML = `
                <div class="flex items-center gap-4">
                  ${IS_ADMIN ? `<input type="checkbox" class="lead-checkbox w-4 h-4 rounded bg-slate-800 border-slate-700 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-slate-900 cursor-pointer" value="${lead.id}" onclick="event.stopPropagation()">` : ''}
                  <div class="w-12 h-12 rounded-full flex items-center justify-center font-bold text-sm shrink-0"
                       style="background:${ownerColor}1f;border:2px solid ${ownerColor}66;color:${ownerColor}">
                    ${initials}
                  </div>
                  <div>
                    <div class="font-bold text-white text-sm flex items-center gap-2 flex-wrap">
                        <a href="/lead-details.html?id=${lead.id}" class="hover:text-indigo-400 hover:underline transition-colors" onclick="event.stopPropagation()">${contactName}</a>
                        <button class="star-btn hover:scale-110 transition-transform" data-id="${lead.id}" data-starred="${lead.is_starred}">
                            <svg class="w-4 h-4 ${lead.is_starred ? 'text-yellow-400 fill-current' : 'text-slate-500'}" viewBox="0 0 24 24" stroke="currentColor" fill="none"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/></svg>
                        </button>
                        <span class="badge ${getBadgeClass(lead.pipeline_stage)}">${lead.pipeline_stage || 'NEW'}</span>
                        <button class="temp-btn badge ${lead.lead_temperature === 'HOT' ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' : lead.lead_temperature === 'WARM' ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' : 'bg-blue-500/20 text-blue-400 border-blue-500/30'} hover:opacity-80 transition-opacity" data-id="${lead.id}" data-temp="${lead.lead_temperature}">
                            ${lead.lead_temperature || 'COLD'}
                        </button>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${prioClass}">${prio}</span>
                        ${lead.is_overdue ? '<span class="badge badge-overdue">SLA Overdue</span>' : ''}
                        ${leadAgeText ? `<span class="text-[10px] text-slate-500 font-mono bg-slate-900/80 px-2 py-0.5 rounded border border-slate-800" title="Lead Age">${leadAgeText}</span>` : ''}
                    </div>
                    <div class="text-[11px] text-slate-400 mt-1 flex flex-wrap gap-x-4 gap-y-1">
                      <span class="flex items-center gap-1" title="Phone">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>
                        ${lead.contact?.phone || '--'}
                      </span>
                      ${(lead.contact?.profession || lead.profession) ? `
                      <span class="flex items-center gap-1 text-slate-300 font-medium" title="Profession / Job Title">
                        <svg class="w-3 h-3 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
                        ${lead.contact?.profession || lead.profession}
                      </span>` : ''}
                      ${(lead.contact?.source || lead.source) ? `
                      <span class="flex items-center gap-1 text-slate-400" title="Source">
                        <svg class="w-3 h-3 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/></svg>
                        ${lead.contact?.source || lead.source}
                      </span>` : ''}
                      ${lead.project_name ? `
                      <span class="flex items-center gap-1" title="Project">
                        <svg class="w-3 h-3 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
                        ${lead.project_name}
                      </span>` : ''}
                      <span class="flex items-center gap-1 text-slate-500" title="Added">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> 
                        ${formatDate(lead.created_at)}
                      </span>
                    </div>
                  </div>
                </div>
                <div class="flex flex-col sm:flex-row gap-2 sm:items-center flex-wrap">
                  ${lead.assigned_to_name ? `
                    <div class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-semibold" style="background: ${ownerColor}22; color: ${ownerColor}; border: 1px solid ${ownerColor}44">
                      <span class="w-2 h-2 rounded-full" style="background: ${ownerColor}"></span>
                      ${lead.assigned_to_name}
                    </div>
                  ` : ''}
                  <a href="tel:${lead.contact?.phone || ''}" class="call-action-btn btn-ghost px-3 py-1.5 rounded-lg text-xs font-medium border border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/10 transition-colors inline-flex items-center gap-1" onclick="event.stopPropagation()">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>
                    Call
                  </a>
                  <button class="log-activity-btn btn-ghost px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700 hover:border-indigo-500 transition-colors" data-id="${lead.id}">
                    Log Activity
                  </button>
                  <button class="exit-lead-btn btn-ghost px-2.5 py-1.5 rounded-lg text-xs font-medium border border-rose-500/30 text-rose-300 hover:bg-rose-500/10 transition-colors" data-id="${lead.id}">
                    Exit Lead
                  </button>
                  <a href="/lead-details.html?id=${lead.id}" class="view-profile-btn btn-gradient px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-lg inline-flex items-center gap-1" onclick="event.stopPropagation()">
                    Profile →
                  </a>
                </div>
            `;

            // Click entire card to open profile
            card.addEventListener('click', (e) => {
                const starBtn = e.target.closest('.star-btn');
                const tempBtn = e.target.closest('.temp-btn');
                const exitBtn = e.target.closest('.exit-lead-btn');
                
                if (starBtn) {
                    toggleStar(lead.id, starBtn.dataset.starred !== 'true');
                } else if (tempBtn) {
                    toggleTemperature(lead.id, tempBtn.dataset.temp);
                } else if (exitBtn) {
                    openExitModal(lead.id);
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
        window.currentLeadId = id;
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
                setTimeout(() => jumpToField(document.getElementById('call-outcome')), 250);
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
        setTimeout(() => jumpToField(document.getElementById('appt-datetime')), 250);
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
            // show target pane, scroll to it and focus its first field
            const target = tab.getAttribute('data-target');
            const pane = document.getElementById(target);
            pane.classList.remove('hidden');
            if (drawerContent) drawerContent.scrollTo({ top: 0, behavior: 'smooth' });
            setTimeout(() => focusFirstField(pane), 100);
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
        currentLeadData = data;
        window.currentLeadData = data;
        window.currentLeadId = data.id;
        window.populateDrawer = populateDrawer;
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
        const profEl = document.getElementById('drawer-profession');
        if (profEl) profEl.textContent = c.profession || data.profession || '--';
        const srvEl = document.getElementById('drawer-service-type');
        if (srvEl) srvEl.textContent = c.service_type || data.service_type || '--';

        const mgrLabelEl = document.getElementById('drawer-manager-label');
        if (mgrLabelEl) {
            const rawLabel = data.manager_label || data.manager_assessment || 'STANDARD';
            mgrLabelEl.textContent = rawLabel.replace(/_/g, ' ');
            if (rawLabel === 'INTERVENTION_REQUIRED') {
                mgrLabelEl.className = 'text-sm font-black text-rose-400 truncate';
            } else if (rawLabel === 'HIGH_INTENT') {
                mgrLabelEl.className = 'text-sm font-black text-amber-400 truncate';
            } else {
                mgrLabelEl.className = 'text-sm font-bold text-indigo-400 truncate';
            }
        }
        const finResultEl = document.getElementById('drawer-final-result');
        if (finResultEl) finResultEl.textContent = data.final_result ? data.final_result.replace(/_/g, ' ') : '--';

        // Render Custom Questions
        const customQContainer = document.getElementById('drawer-custom-questions-container');
        const customQGrid = document.getElementById('drawer-custom-questions');
        customQGrid.innerHTML = '';
        if (data.custom_fields && data.custom_fields.length > 0) {
            customQContainer.classList.remove('hidden');
            data.custom_fields.forEach(field => {
                customQGrid.innerHTML += `
                    <div class="bg-slate-900/50 rounded-xl p-3 border border-slate-800/60">
                        <div class="text-[10px] text-slate-500 uppercase font-semibold mb-1">${field.name.replace(/_/g, ' ')}</div>
                        <div class="text-sm font-medium text-slate-200">${field.value || '--'}</div>
                    </div>
                `;
            });
        } else {
            customQContainer.classList.add('hidden');
        }

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
                    <div class="flex items-center justify-between mb-0.5">
                        <div class="text-xs font-semibold text-white">Call Logged <span class="text-slate-500 font-normal ml-2">${formatDate(item.date)}</span></div>
                        ${item.activity_label ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">${item.activity_label}</span>` : ''}
                    </div>
                    <div class="text-xs text-slate-400 mb-1">Status: <span class="${item.connected ? 'text-emerald-400' : 'text-rose-400'}">${item.connected ? 'Connected' : 'Not Connected'}</span></div>
                    ${item.notes ? `<div class="text-xs text-slate-300 bg-slate-800/50 p-2 rounded border border-slate-700/50 mt-1">${item.notes}</div>` : ''}
                    ${item.recording_url ? `<a href="${item.recording_url}" target="_blank" class="inline-flex items-center gap-1 text-[10px] text-indigo-400 hover:text-indigo-300 mt-2 bg-indigo-500/10 px-2 py-1 rounded-full"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/></svg> Play Recording</a>` : ''}
                `;
                
                // 2. Populate Files Tab
                if (item.recording_url) {
                    fileCount++;
                    const isAdmin = localStorage.getItem('crm_role') === 'ADMIN';
                    const checkboxHtml = isAdmin ? `<input type="checkbox" class="call-record-checkbox rounded bg-slate-800 border-slate-700 text-rose-500 focus:ring-rose-500 w-4 h-4 mr-2" value="${item.id}">` : '';

                    filesContainer.innerHTML += `
                        <div class="bg-slate-900/50 border border-slate-800 rounded-xl p-3 flex justify-between items-center hover:border-slate-700 transition-colors">
                            <div class="flex items-center gap-3">
                                ${checkboxHtml}
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

        const bulkDeleteBtn = document.getElementById('bulk-delete-calls-btn');
        if (bulkDeleteBtn) {
            const isAdmin = localStorage.getItem('crm_role') === 'ADMIN';
            if (isAdmin && fileCount > 0) {
                bulkDeleteBtn.classList.remove('hidden');
            } else {
                bulkDeleteBtn.classList.add('hidden');
            }
        }

        // M-08 Objections & M-05/M-09 Coaching
        loadDrawerObjections(data.id);
        loadDrawerCoaching(data.id);

        const debriefBtn = document.getElementById('drawer-debrief-btn');
        if (debriefBtn) {
            debriefBtn.onclick = () => openDebriefModalForLead(data.id);
        }
        const objBtn = document.getElementById('drawer-objection-btn');
        if (objBtn) {
            objBtn.onclick = () => openObjectionModal(data.id);
        }
        const exitBtn = document.getElementById('drawer-exit-btn');
        if (exitBtn) {
            exitBtn.onclick = () => openExitModal(data.id);
        }
    }

    // Add Bulk Delete function to window object so inline onclick can access it
    window.bulkDeleteCalls = async () => {
        if (!currentLeadId) return;
        const checkboxes = document.querySelectorAll('.call-record-checkbox:checked');
        if (checkboxes.length === 0) {
            if (window.showToast) window.showToast("No recordings selected", "error");
            return;
        }

        if (!confirm(`Are you sure you want to permanently delete ${checkboxes.length} call recording(s)?`)) return;

        const callIds = Array.from(checkboxes).map(cb => parseInt(cb.value));
        const btn = document.getElementById('bulk-delete-calls-btn');
        btn.disabled = true;
        btn.textContent = 'Deleting...';

        try {
            const token = localStorage.getItem('crm_token');
            const res = await fetch(`/api/leads/${currentLeadId}/calls/bulk-delete`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ call_ids: callIds })
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.error || "Failed to delete recordings");
            }
            if (window.showToast) window.showToast("Recordings deleted successfully", "success");
            
            // Refresh drawer
            document.getElementById('drawer-timeline').innerHTML = '<div class="text-sm text-slate-500 ml-4">Loading timeline...</div>';
            const refreshRes = await fetch(`/api/leads/${currentLeadId}/profile`, { headers: { 'Authorization': `Bearer ${token}` } });
            populateDrawer(await refreshRes.json());
        } catch (err) {
            console.error(err);
            if (window.showToast) window.showToast(err.message, "error");
        } finally {
            btn.disabled = false;
            btn.textContent = 'Delete Selected';
        }
    };

    // Add Lead Modal Logic
    const addLeadBtn = document.getElementById('add-lead-btn');
    const addLeadModal = document.getElementById('add-lead-modal');
    const addLeadModalContent = document.getElementById('add-lead-modal-content');
    const closeAddLeadBtn = document.getElementById('close-add-lead-btn');
    const cancelAddLeadBtn = document.getElementById('cancel-add-lead-btn');
    const addLeadForm = document.getElementById('add-lead-form');

    const loadProjectsIntoDropdown = async () => {
        try {
            const select = document.getElementById('add-lead-project-select');
            if (!select) return;
            
            const token = localStorage.getItem('crm_token');
            const res = await fetch('/api/projects/', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const projects = await res.json();
                select.innerHTML = '<option value="">-- None --</option>';
                projects.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.id;
                    opt.textContent = p.name;
                    select.appendChild(opt);
                });
            }
        } catch (err) {
            console.error("Failed to load projects for dropdown", err);
        }
    };

    const renderDynamicCustomFields = async (containerEl, initialValues = {}) => {
        if (!containerEl) return;
        try {
            const token = localStorage.getItem('crm_token');
            const res = await fetch('/api/settings/questionnaire', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) return;
            const questions = await res.json();
            const activeQuestions = questions.filter(q => q.is_active);
            const sectionEl = containerEl.closest('[id$="-custom-fields-section"]');
            if (!activeQuestions.length) {
                if (sectionEl) sectionEl.classList.add('hidden');
                containerEl.innerHTML = '';
                return;
            }
            if (sectionEl) sectionEl.classList.remove('hidden');
            containerEl.innerHTML = '';
            activeQuestions.forEach(q => {
                const val = initialValues[q.question_key] || '';
                const fieldDiv = document.createElement('div');
                fieldDiv.className = 'space-y-1';
                let inputHtml = '';
                if (q.question_type === 'select' && q.options) {
                    const opts = q.options.split(',').map(o => o.trim()).filter(Boolean);
                    inputHtml = `
                        <select data-custom-key="${q.question_key}" class="custom-field-input w-full bg-[#161825] border border-slate-700 rounded-xl px-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500">
                            <option value="">-- Select ${q.question_text} --</option>
                            ${opts.map(o => `<option value="${o}" ${val === o ? 'selected' : ''}>${o}</option>`).join('')}
                        </select>
                    `;
                } else if (q.question_type === 'number') {
                    inputHtml = `
                        <input type="number" data-custom-key="${q.question_key}" value="${val}" class="custom-field-input w-full bg-[#161825] border border-slate-700 rounded-xl px-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 placeholder-slate-600" placeholder="e.g. 5000000">
                    `;
                } else {
                    inputHtml = `
                        <input type="text" data-custom-key="${q.question_key}" value="${val}" class="custom-field-input w-full bg-[#161825] border border-slate-700 rounded-xl px-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 placeholder-slate-600" placeholder="Enter answer...">
                    `;
                }
                fieldDiv.innerHTML = `
                    <label class="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider">${q.question_text} ${q.is_required ? '<span class="text-rose-400">*</span>' : ''}</label>
                    ${inputHtml}
                `;
                containerEl.appendChild(fieldDiv);
            });
        } catch (err) {
            console.error("Failed to render custom fields:", err);
        }
    };

    const collectCustomFieldValues = (containerEl) => {
        const answers = {};
        if (!containerEl) return answers;
        const inputs = containerEl.querySelectorAll('.custom-field-input');
        inputs.forEach(input => {
            const key = input.getAttribute('data-custom-key');
            const val = input.value.trim();
            if (key && val) {
                answers[key] = val;
            }
        });
        return answers;
    };

    const openAddLeadModal = async () => {
        addLeadForm.reset();
        addLeadModal.classList.remove('hidden');
        requestAnimationFrame(() => {
            addLeadModal.classList.remove('opacity-0');
            addLeadModalContent.classList.remove('scale-95');
        });
        setTimeout(() => jumpToField(addLeadForm.querySelector('input[name="full_name"]')), 250);
        await loadProjectsIntoDropdown();
        await renderDynamicCustomFields(document.getElementById('add-lead-custom-fields-container'));
    };

    const closeAddLeadModal = () => {
        addLeadModal.classList.add('opacity-0');
        addLeadModalContent.classList.add('scale-95');
        setTimeout(() => {
            addLeadModal.classList.add('hidden');
        }, 200);
    };

    const addLeadPhoneInput = document.getElementById('add-lead-phone-input');
    const duplicateWarningEl = document.getElementById('add-lead-duplicate-warning');
    const duplicateMsgEl = document.getElementById('add-lead-duplicate-msg');

    let duplicateCheckTimeout = null;
    if (addLeadPhoneInput) {
        addLeadPhoneInput.addEventListener('input', (e) => {
            const phone = e.target.value.trim();
            if (duplicateWarningEl) duplicateWarningEl.classList.add('hidden');
            if (phone.length < 6) return;

            clearTimeout(duplicateCheckTimeout);
            duplicateCheckTimeout = setTimeout(async () => {
                try {
                    const token = localStorage.getItem('crm_token');
                    const res = await fetch(`/api/leads/check-duplicate?phone=${encodeURIComponent(phone)}`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (!res.ok) return;
                    const result = await res.json();
                    if (result.is_duplicate && duplicateWarningEl && duplicateMsgEl) {
                        let msg = result.message || `Lead already exists (${result.contact_name})`;
                        if (result.opportunity_id) {
                            duplicateMsgEl.innerHTML = `${msg} — <a href="/lead-details.html?id=${result.opportunity_id}" target="_blank" class="underline font-bold text-amber-200 hover:text-white inline-flex items-center gap-1">View Lead <svg class="w-3.5 h-3.5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg></a>`;
                        } else {
                            duplicateMsgEl.textContent = msg;
                        }
                        duplicateWarningEl.classList.remove('hidden');
                    } else if (duplicateWarningEl) {
                        duplicateWarningEl.classList.add('hidden');
                    }
                } catch (err) {
                    console.error("Duplicate check error:", err);
                }
            }, 350);
        });
    }

    if (addLeadBtn) addLeadBtn.addEventListener('click', openAddLeadModal);
    if (closeAddLeadBtn) closeAddLeadBtn.addEventListener('click', closeAddLeadModal);
    if (cancelAddLeadBtn) cancelAddLeadBtn.addEventListener('click', closeAddLeadModal);
    
    if (addLeadForm) {
        addLeadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(addLeadForm);
            const data = Object.fromEntries(formData.entries());
            // Drop blank optional inputs — sending "" made the API reject the
            // request ("Not a valid email address") whenever email was left empty.
            Object.keys(data).forEach(k => {
                if (typeof data[k] === 'string' && data[k].trim() === '') delete data[k];
            });
            if (!data.project_id) delete data.project_id;

            const customAnswers = collectCustomFieldValues(document.getElementById('add-lead-custom-fields-container'));
            if (Object.keys(customAnswers).length > 0) {
                data.questionnaire_answers = customAnswers;
            }
            
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

                if (res.status === 409) {
                    const errData = await res.json();
                    const oppId = errData.details?.opportunity_id;
                    const confirmMsg = `${errData.message || "A lead already exists for this contact."}\n\nDo you want to FORCE create a duplicate lead anyway? (Click Cancel to view existing lead instead)`;
                    if (confirm(confirmMsg)) {
                        data.force_create = true;
                        const forceRes = await fetch('/api/leads/', {
                            method: 'POST',
                            headers: { 
                                'Authorization': `Bearer ${token}`,
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(data)
                        });
                        if (!forceRes.ok) {
                            const forceErr = await forceRes.json();
                            throw new Error(forceErr.message || forceErr.error || "Failed to force create lead");
                        }
                        if (window.showToast) window.showToast("Duplicate lead created per your confirmation.", "warning");
                        closeAddLeadModal();
                        loadLeads();
                        return;
                    } else {
                        if (oppId) {
                            window.open(`/lead-details.html?id=${oppId}`, '_blank');
                        }
                        return;
                    }
                }

                if (!res.ok) {
                    const errData = await res.json();
                    throw new Error(errData.error || errData.msg || errData.message || "Failed to create lead");
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

    // Setup and Populate Lead Owner Filter dropdown and Bulk Assign (Admin only)
    if (IS_ADMIN) {
        const bulkAssignBtn = document.getElementById('bulk-assign-btn');
        if (bulkAssignBtn) bulkAssignBtn.classList.remove('hidden');

        const cleanDuplicatesBtn = document.getElementById('clean-duplicates-btn');
        if (cleanDuplicatesBtn) {
            cleanDuplicatesBtn.classList.remove('hidden');
            cleanDuplicatesBtn.addEventListener('click', async () => {
                const token = localStorage.getItem('crm_token');
                try {
                    const countRes = await fetch('/api/leads/duplicate-count', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (!countRes.ok) throw new Error("Failed to check duplicate count");
                    const countData = await countRes.json();

                    if (countData.duplicate_leads === 0) {
                        if (window.showToast) window.showToast("No duplicate leads found! All leads are already unique.", "info");
                        return;
                    }

                    const sample = countData.details?.slice(0, 3).map(d => `• ${d.name} (${d.phone || 'N/A'}): ${d.duplicate_count} duplicate(s)`).join('\n') || '';
                    const extra = countData.details?.length > 3 ? `\n...and ${countData.details.length - 3} more` : '';

                    const confirmMsg = `Found ${countData.duplicate_leads} duplicate lead(s) across ${countData.duplicate_groups} contact(s):\n\n${sample}${extra}\n\nThis will merge all call logs, activities, and notes into the primary lead and remove the duplicate cards.\n\nDo you want to proceed with Auto-Clean?`;

                    if (!confirm(confirmMsg)) return;

                    const originalHtml = cleanDuplicatesBtn.innerHTML;
                    cleanDuplicatesBtn.innerHTML = '<svg class="animate-spin h-4 w-4 text-amber-400 inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Cleaning...';
                    cleanDuplicatesBtn.disabled = true;

                    const res = await fetch('/api/leads/cleanup-duplicates', {
                        method: 'POST',
                        headers: { 
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        }
                    });

                    cleanDuplicatesBtn.innerHTML = originalHtml;
                    cleanDuplicatesBtn.disabled = false;

                    if (!res.ok) {
                        const err = await res.json();
                        throw new Error(err.message || err.error || "Failed to cleanup duplicates");
                    }

                    const result = await res.json();
                    if (window.showToast) window.showToast(result.message || "Duplicates cleaned and merged successfully!", "success");
                    loadLeads();
                } catch (err) {
                    console.error("Clean duplicates error:", err);
                    if (cleanDuplicatesBtn) cleanDuplicatesBtn.disabled = false;
                    if (window.showToast) window.showToast(err.message, "error");
                }
            });
        }

        const editBtn = document.getElementById('drawer-edit-btn');
        const deleteBtn = document.getElementById('drawer-delete-btn');
        const editModal = document.getElementById('edit-lead-modal');
        const editForm = document.getElementById('edit-lead-form');
        const closeEditModalBtn = document.getElementById('close-edit-modal');
        const cancelEditModalBtn = document.getElementById('cancel-edit-modal');

        if (editBtn) {
            editBtn.classList.remove('hidden');
            editBtn.addEventListener('click', async () => {
                if (!currentLeadData) return;
                const c = currentLeadData.contact || {};
                document.getElementById('edit-lead-name').value = c.full_name || '';
                document.getElementById('edit-lead-phone').value = c.phone_raw || '';
                document.getElementById('edit-lead-email').value = c.email || '';
                const editProf = document.getElementById('edit-lead-profession');
                if (editProf) editProf.value = c.profession || currentLeadData.profession || '';
                const editSrv = document.getElementById('edit-lead-service-type');
                if (editSrv) editSrv.value = c.service_type || currentLeadData.service_type || '';
                
                editModal.classList.remove('hidden');
                requestAnimationFrame(() => {
                    editModal.classList.remove('opacity-0');
                    document.getElementById('edit-lead-modal-content').classList.remove('scale-95');
                });

                const existingAnswers = currentLeadData.questionnaire_answers || {};
                await renderDynamicCustomFields(document.getElementById('edit-lead-custom-fields-container'), existingAnswers);
            });
        }

        const closeEditModal = () => {
            editModal.classList.add('opacity-0');
            document.getElementById('edit-lead-modal-content').classList.add('scale-95');
            setTimeout(() => editModal.classList.add('hidden'), 200);
        };

        if (closeEditModalBtn) closeEditModalBtn.addEventListener('click', closeEditModal);
        if (cancelEditModalBtn) cancelEditModalBtn.addEventListener('click', closeEditModal);

        if (editForm) {
            editForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const saveBtn = document.getElementById('save-edit-btn');
                const originalText = saveBtn.innerHTML;
                saveBtn.innerHTML = 'Saving...';
                saveBtn.disabled = true;

                try {
                    const token = localStorage.getItem('crm_token');
                    const data = {
                        full_name: document.getElementById('edit-lead-name').value.trim(),
                        phone: document.getElementById('edit-lead-phone').value.trim(),
                        email: document.getElementById('edit-lead-email').value.trim(),
                        profession: (document.getElementById('edit-lead-profession')?.value || '').trim(),
                        service_type: (document.getElementById('edit-lead-service-type')?.value || '').trim()
                    };

                    const customAnswers = collectCustomFieldValues(document.getElementById('edit-lead-custom-fields-container'));
                    if (Object.keys(customAnswers).length > 0) {
                        data.questionnaire_answers = customAnswers;
                    }

                    const res = await fetch(`/api/leads/${currentLeadId}`, {
                        method: 'PUT',
                        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });

                    if (!res.ok) {
                        const err = await res.json();
                        throw new Error(err.error || "Failed to edit lead");
                    }

                    if (window.showToast) window.showToast("Lead updated successfully", "success");
                    closeEditModal();
                    
                    // Reload drawer and list
                    const updatedRes = await fetch(`/api/leads/${currentLeadId}/profile`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (updatedRes.ok) {
                        populateDrawer(await updatedRes.json());
                    }
                    loadLeads();
                } catch (err) {
                    if (window.showToast) window.showToast(err.message, "error");
                } finally {
                    saveBtn.innerHTML = originalText;
                    saveBtn.disabled = false;
                }
            });
        }

        if (deleteBtn) {
            deleteBtn.classList.remove('hidden');
            deleteBtn.addEventListener('click', async () => {
                if (!confirm("Are you sure you want to delete this lead? This action cannot be undone.")) return;
                
                try {
                    const token = localStorage.getItem('crm_token');
                    const res = await fetch(`/api/leads/${currentLeadId}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': `Bearer ${token}` }
                    });

                    if (!res.ok) {
                        const err = await res.json();
                        throw new Error(err.error || "Failed to delete lead");
                    }

                    if (window.showToast) window.showToast("Lead deleted successfully", "success");
                    closeDrawerBtn.click(); // Close the drawer
                    loadLeads(); // Reload the list
                } catch (err) {
                    if (window.showToast) window.showToast(err.message, "error");
                }
            });
        }

        const selectAllBtn = document.getElementById('select-all-btn');
        if (selectAllBtn) {
            selectAllBtn.classList.remove('hidden');
            selectAllBtn.addEventListener('click', () => {
                const boxes = document.querySelectorAll('.lead-checkbox');
                if (boxes.length === 0) return;
                const allChecked = Array.from(boxes).every(b => b.checked);
                boxes.forEach(b => b.checked = !allChecked);
            });
        }

        } // end admin-only buttons; owner filter below is for EVERYONE
        // (leads page shows all leads to all roles — filter stays available)

        const container = document.getElementById('filter-owner-container');
        if (container) container.classList.remove('hidden');
        
        const select = document.getElementById('filter-owner');
        const bulkSelect = document.getElementById('bulk-assign-owner');
        
        if (select || bulkSelect) {
            const token = localStorage.getItem('crm_token');
            fetch('/api/team/members', {
                headers: { 'Authorization': `Bearer ${token}` }
            })
            .then(res => res.json())
            .then(members => {
                // Add Pending to filter
                if (select) {
                    const pendingOpt = document.createElement('option');
                    pendingOpt.value = 'none';
                    pendingOpt.textContent = 'Pending (Unassigned)';
                    select.appendChild(pendingOpt);
                }

                members.forEach(m => {
                    if (select) {
                        const opt = document.createElement('option');
                        opt.value = m.id;
                        opt.textContent = m.full_name;
                        select.appendChild(opt);
                    }
                    if (bulkSelect) {
                        const bulkOpt = document.createElement('option');
                        bulkOpt.value = m.id;
                        bulkOpt.textContent = m.full_name;
                        bulkSelect.appendChild(bulkOpt);
                    }
                });
                
                // If URL owner filter is present, ensure select option matches
                const urlParams = new URLSearchParams(window.location.search);
                const ownerParam = urlParams.get('owner');
                if (ownerParam && select) {
                    select.value = ownerParam;
                }
            })
            .catch(err => console.error("Failed to load members for filter/bulk assign", err));
        }

    if (IS_ADMIN) {
        // Bulk Assign Modal Logic
        const bulkAssignModal = document.getElementById('bulk-assign-modal');
        const bulkAssignModalContent = document.getElementById('bulk-assign-modal-content');
        const bulkAssignForm = document.getElementById('bulk-assign-form');
        
        const openBulkAssignModal = () => {
            const selectedBoxes = document.querySelectorAll('.lead-checkbox:checked');
            if (selectedBoxes.length === 0) {
                if (window.showToast) window.showToast("Please select at least one lead.", "info");
                return;
            }
            document.getElementById('bulk-assign-count').textContent = selectedBoxes.length;
            bulkAssignForm.reset();
            bulkAssignModal.classList.remove('hidden');
            requestAnimationFrame(() => {
                bulkAssignModal.classList.remove('opacity-0');
                bulkAssignModalContent.classList.remove('scale-95');
            });
        };

        const closeBulkAssignModal = () => {
            bulkAssignModal.classList.add('opacity-0');
            bulkAssignModalContent.classList.add('scale-95');
            setTimeout(() => {
                bulkAssignModal.classList.add('hidden');
            }, 200);
        };

        if (bulkAssignBtn) bulkAssignBtn.addEventListener('click', openBulkAssignModal);
        document.getElementById('close-bulk-assign-modal')?.addEventListener('click', closeBulkAssignModal);
        document.getElementById('cancel-bulk-assign-btn')?.addEventListener('click', closeBulkAssignModal);

        if (bulkAssignForm) {
            bulkAssignForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const selectedBoxes = document.querySelectorAll('.lead-checkbox:checked');
                const leadIds = Array.from(selectedBoxes).map(cb => parseInt(cb.value, 10));
                
                let ownerId = document.getElementById('bulk-assign-owner').value;
                if (ownerId === 'none') ownerId = null; // Unassign
                else if (ownerId) ownerId = parseInt(ownerId, 10);
                
                const submitBtn = document.getElementById('save-bulk-assign-btn');
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = 'Assigning...';
                submitBtn.disabled = true;

                try {
                    const token = localStorage.getItem('crm_token');
                    const res = await fetch('/api/leads/bulk-assign', {
                        method: 'POST',
                        headers: { 
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ lead_ids: leadIds, owner_id: ownerId })
                    });
                    
                    if (!res.ok) {
                        const errData = await res.json().catch(()=>({}));
                        throw new Error(errData.error || errData.msg || "Failed to bulk assign leads");
                    }
                    
                    if (window.showToast) window.showToast(`Successfully updated ${leadIds.length} lead(s).`, "success");
                    closeBulkAssignModal();
                    loadLeads();
                } catch (err) {
                    console.error(err);
                    if (window.showToast) window.showToast(err.message, "error");
                } finally {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }
            });
        }
    }

    // Import Leads Modal Logic
    const importBtn = document.getElementById('import-leads-btn');
    const importModal = document.getElementById('import-lead-modal');
    const importModalContent = document.getElementById('import-lead-modal-content');
    const closeImportBtn = document.getElementById('close-import-modal-btn');
    const cancelImportBtn = document.getElementById('cancel-import-btn');
    const importForm = document.getElementById('import-lead-form');
    const importOwnerSelect = document.getElementById('import-owner-select');
    const importResultBox = document.getElementById('import-result-box');
    const importSpinner = document.getElementById('import-spinner');
    const submitImportBtn = document.getElementById('submit-import-btn');

    const openImportModal = async () => {
        if (!importModal) return;
        importForm.reset();
        importResultBox.className = 'hidden p-4 rounded-xl border';
        importResultBox.innerHTML = '';
        if (typeof resetImportMapping === 'function') resetImportMapping();
        importModal.classList.remove('hidden');
        requestAnimationFrame(() => {
            importModal.classList.remove('opacity-0');
            importModalContent.classList.remove('scale-95');
        });
        
        // Populate team members into importOwnerSelect
        try {
            const token = localStorage.getItem('crm_token');
            const res = await fetch('/api/team/members', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const members = await res.json();
                importOwnerSelect.innerHTML = '<option value="">Leave Unassigned</option>';
                members.forEach(m => {
                    const opt = document.createElement('option');
                    opt.value = m.id;
                    opt.textContent = m.full_name;
                    importOwnerSelect.appendChild(opt);
                });
            }
        } catch (e) {
            console.error("Failed to load members for import modal", e);
        }
    };

    const closeImportModal = () => {
        if (!importModal) return;
        importModal.classList.add('opacity-0');
        importModalContent.classList.add('scale-95');
        setTimeout(() => importModal.classList.add('hidden'), 200);
    };

    if (importBtn) importBtn.addEventListener('click', openImportModal);
    if (closeImportBtn) closeImportBtn.addEventListener('click', closeImportModal);
    if (cancelImportBtn) cancelImportBtn.addEventListener('click', closeImportModal);

    // Mapped import flow: 1) upload -> preview headers + suggested mapping,
    // 2) user maps each header to a CRM field (or skips it) and previews
    // parsed rows, 3) confirm -> import with that mapping.
    let importMappingReady = false;
    const importMappingBox = document.getElementById('import-mapping-box');
    const importPreviewBox = document.getElementById('import-preview-box');
    const FIELD_LABELS = { full_name: 'Full Name', phone: 'Phone', email: 'Email', profession: 'Profession', service_type: 'Service Type', project_name: 'Project Name', budget: 'Budget', source: 'Source', notes: 'Notes' };
    const renderImportMapping = (preview) => {
        if (!importMappingBox) return;
        const rowsHtml = (preview.preview_rows || []).map(r =>
            `<tr>${preview.headers.map(h => `<td class="px-2 py-1 border-b border-slate-800 whitespace-nowrap">${(r[h] ?? '')}</td>`).join('')}</tr>`).join('');
        importMappingBox.innerHTML = `<div class="text-xs font-semibold text-slate-400 uppercase">Map columns (${preview.total_rows} rows found) — leave as “Skip” to ignore a column</div>` +
            preview.headers.map(h => {
                const suggested = (preview.suggested_mapping || {})[h] || '';
                const opts = `<option value="">Skip</option>` + Object.entries(FIELD_LABELS).map(([v, l]) =>
                    `<option value="${v}" ${v === suggested ? 'selected' : ''}>${l}</option>`).join('');
                return `<div class="flex items-center gap-2 text-xs"><span class="flex-1 truncate text-slate-300">${h}</span><select data-import-header="${h}" class="bg-[#161825] border border-slate-700 rounded-lg px-2 py-1.5 text-slate-200">${opts}</select></div>`;
            }).join('');
        importMappingBox.classList.remove('hidden');
        if (importPreviewBox) {
            importPreviewBox.innerHTML = `<div class="font-semibold text-slate-400 mb-2">Preview (first ${preview.preview_rows.length} rows)</div><table class="text-xs"><thead><tr>${preview.headers.map(h => `<th class="px-2 py-1 text-left text-slate-400">${h}</th>`).join('')}</tr></thead><tbody>${rowsHtml}</tbody></table>`;
            importPreviewBox.classList.remove('hidden');
        }
        const submitLabel = submitImportBtn.querySelector('span') || submitImportBtn;
        submitImportBtn.childNodes.forEach(n => { if (n.nodeType === 3) n.remove(); });
        submitImportBtn.insertAdjacentText('beforeend', 'Confirm Import');
    };
    const resetImportMapping = () => {
        importMappingReady = false;
        if (importMappingBox) { importMappingBox.classList.add('hidden'); importMappingBox.innerHTML = ''; }
        if (importPreviewBox) { importPreviewBox.classList.add('hidden'); importPreviewBox.innerHTML = ''; }
        submitImportBtn.childNodes.forEach(n => { if (n.nodeType === 3) n.remove(); });
        submitImportBtn.insertAdjacentText('beforeend', 'Start Import');
    };

    if (importForm) {
        importForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('import-file-input');
            if (!fileInput.files || fileInput.files.length === 0) {
                if (window.showToast) window.showToast("Please choose a CSV or Excel file.", "error");
                return;
            }

            const file = fileInput.files[0];
            const dupStrategy = document.querySelector('input[name="import_dup_strategy"]:checked')?.value || 'merge';
            const ownerId = importOwnerSelect.value || '';
            const defaultSource = document.getElementById('import-source-input').value.trim() || 'CSV Import';
            const token = localStorage.getItem('crm_token');

            // Step 1: preview + mapping (no import yet).
            if (!importMappingReady) {
                submitImportBtn.disabled = true;
                importSpinner.classList.remove('hidden');
                try {
                    const previewData = new FormData();
                    previewData.append('file', file);
                    const previewRes = await fetch('/api/leads/import/preview', {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${token}` },
                        body: previewData
                    });
                    const preview = await previewRes.json();
                    if (!previewRes.ok) throw new Error(preview.error || "Failed to preview file");
                    renderImportMapping(preview);
                    importMappingReady = true;
                    if (window.showToast) window.showToast("Map the columns, then Confirm Import.", "success");
                } catch (err) {
                    if (window.showToast) window.showToast(err.message, "error");
                } finally {
                    submitImportBtn.disabled = false;
                    importSpinner.classList.add('hidden');
                }
                return;
            }

            // Step 2: confirm import with the user's mapping.
            const mapping = {};
            if (importMappingBox) {
                importMappingBox.querySelectorAll('select[data-import-header]').forEach(sel => {
                    mapping[sel.getAttribute('data-import-header')] = sel.value;
                });
            }
            const formData = new FormData();
            formData.append('file', file);
            formData.append('duplicate_strategy', dupStrategy);
            formData.append('mapping', JSON.stringify(mapping));
            if (ownerId) formData.append('assigned_to_id', ownerId);
            formData.append('default_source', defaultSource);

            submitImportBtn.disabled = true;
            importSpinner.classList.remove('hidden');

            try {
                const res = await fetch('/api/leads/import', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` },
                    body: formData
                });
                const result = await res.json();
                if (!res.ok) {
                    throw new Error(result.error || result.msg || "Failed to import leads");
                }

                importResultBox.className = 'p-4 rounded-xl border bg-emerald-500/10 border-emerald-500/30 text-emerald-300 text-xs space-y-1 block';
                importResultBox.innerHTML = `
                    <div class="font-bold text-sm text-emerald-400 flex items-center gap-1.5">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                        Import Complete!
                    </div>
                    <div>Total Processed: <strong>${result.total_processed}</strong></div>
                    <div>New Leads Created: <strong>${result.created_count}</strong></div>
                    <div>Merged with Existing: <strong>${result.merged_count}</strong></div>
                    <div>Skipped (Duplicates): <strong>${result.skipped_count}</strong></div>
                    ${result.errors && result.errors.length ? `<div class="text-rose-400 mt-2 font-medium">Errors (${result.errors.length}): ${result.errors.slice(0, 3).map(e => e.error).join('; ')}</div>` : ''}
                `;

                if (window.showToast) window.showToast(`Imported ${result.created_count} new leads, merged ${result.merged_count}.`, "success");
                resetImportMapping();
                loadLeads();
            } catch (err) {
                console.error(err);
                importResultBox.className = 'p-4 rounded-xl border bg-rose-500/10 border-rose-500/30 text-rose-300 text-xs block';
                importResultBox.innerHTML = `<strong>Error:</strong> ${err.message}`;
                if (window.showToast) window.showToast(err.message, "error");
            } finally {
                submitImportBtn.disabled = false;
                importSpinner.classList.add('hidden');
            }
        });
    }

    // Lead Questionnaire Modal Logic
    const editQuestionnaireBtn = document.getElementById('drawer-edit-questionnaire-btn');
    const questionnaireModal = document.getElementById('edit-questionnaire-modal');
    const questionnaireModalContent = document.getElementById('edit-questionnaire-modal-content');
    const closeQuestionnaireBtn = document.getElementById('close-questionnaire-modal-btn');
    const cancelQuestionnaireBtn = document.getElementById('cancel-questionnaire-btn');
    const questionnaireForm = document.getElementById('edit-questionnaire-form');
    const questionnaireFieldsContainer = document.getElementById('questionnaire-fields-container');
    const saveQuestionnaireBtn = document.getElementById('save-questionnaire-btn');

    const openQuestionnaireModal = (leadId) => {
        const id = leadId || currentLeadId || (currentLeadData ? currentLeadData.id : null) || window.currentLeadId;
        if (!id) {
            console.warn("No lead selected for questionnaire page");
            if (window.showToast) window.showToast("Please select a lead first", "warning");
            return;
        }
        window.location.href = `/lead-details.html?id=${id}`;
    };

    const closeQuestionnaireModal = () => {
        const modal = document.getElementById('edit-questionnaire-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.style.display = 'none';
        }
    };

    window.openQuestionnaireModal = openQuestionnaireModal;
    window.closeQuestionnaireModal = closeQuestionnaireModal;

    if (editQuestionnaireBtn) editQuestionnaireBtn.addEventListener('click', () => openQuestionnaireModal());
    if (closeQuestionnaireBtn) closeQuestionnaireBtn.addEventListener('click', closeQuestionnaireModal);
    if (cancelQuestionnaireBtn) cancelQuestionnaireBtn.addEventListener('click', closeQuestionnaireModal);

    if (questionnaireForm) {
        questionnaireForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!currentLeadId) return;

            const formData = new FormData(questionnaireForm);
            const answers = {};
            for (let [key, val] of formData.entries()) {
                if (val !== '') answers[key] = val;
            }

            saveQuestionnaireBtn.disabled = true;
            const originalText = saveQuestionnaireBtn.innerHTML;
            saveQuestionnaireBtn.innerHTML = 'Saving...';

            try {
                const token = localStorage.getItem('crm_token');
                const res = await fetch(`/api/leads/${currentLeadId}/questionnaire`, {
                    method: 'PUT',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ answers })
                });

                if (!res.ok) {
                    const err = await res.json().catch(()=>({}));
                    throw new Error(err.error || err.msg || "Failed to save questionnaire");
                }

                if (window.showToast) window.showToast("Questionnaire answers updated!", "success");
                closeQuestionnaireModal();

                // Refresh profile in drawer
                const refreshRes = await fetch(`/api/leads/${currentLeadId}/profile`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (refreshRes.ok) {
                    populateDrawer(await refreshRes.json());
                }
            } catch (err) {
                console.error(err);
                if (window.showToast) window.showToast(err.message, "error");
            } finally {
                saveQuestionnaireBtn.disabled = false;
                saveQuestionnaireBtn.innerHTML = originalText;
            }
        });
    }

    // =========================================================================
    // Architecture v2.0 Module Functions: Debrief, Exit, Objections, Coaching
    // =========================================================================

    // ── Drawer: Objections (M-08) ─────────────────────────────────────────────
    async function loadDrawerObjections(leadId) {
        const container = document.getElementById('drawer-objections-list');
        if (!container || !leadId) return;
        try {
            const token = localStorage.getItem('crm_token');
            const res = await fetch(`/api/leads/${leadId}/objections`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) throw new Error("Failed to load objections");
            const objections = await res.json();
            if (objections.length === 0) {
                container.innerHTML = '<div class="text-xs text-slate-500 py-4 text-center">No objections logged yet.</div>';
                return;
            }
            container.innerHTML = objections.map(o => `
                <div class="bg-slate-900/60 border border-slate-800 rounded-xl p-3 space-y-1.5">
                    <div class="flex items-center justify-between">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">${o.category || 'OBJECTION'}</span>
                        <span class="text-[10px] text-slate-500">Intensity: <strong class="text-rose-400">${o.intensity || 3}/5</strong></span>
                    </div>
                    <div class="text-xs text-slate-200 font-medium">${o.specific_objection}</div>
                    ${o.competitor_name ? `<div class="text-[11px] text-purple-400">Competitor: ${o.competitor_name}</div>` : ''}
                    ${o.executive_response ? `<div class="text-[11px] text-slate-400 bg-slate-800/40 p-2 rounded border border-slate-700/40"><strong class="text-slate-300">Executive Response:</strong> ${o.executive_response}</div>` : ''}
                    <div class="text-[10px] text-slate-500 flex justify-between pt-1">
                        <span>${formatDate(o.created_at)}</span>
                        ${o.is_principal ? '<span class="text-rose-400 font-semibold">Primary Blocker</span>' : ''}
                    </div>
                </div>
            `).join('');
        } catch (e) {
            console.error("Failed to load objections", e);
            container.innerHTML = '<div class="text-xs text-rose-400 py-2">Error loading objections</div>';
        }
    }

    // ── Drawer: Coaching (M-05 & M-09) ────────────────────────────────────────
    async function loadDrawerCoaching(leadId) {
        const container = document.getElementById('drawer-coaching-list');
        if (!container) return;
        try {
            const token = localStorage.getItem('crm_token');
            const res = await fetch('/api/leads/coaching', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) throw new Error("Failed to load coaching logs");
            const logs = await res.json();
            const relevant = logs.filter(l => l.opportunity_id === leadId);
            if (relevant.length === 0) {
                container.innerHTML = '<div class="text-xs text-slate-500 py-4 text-center">No manager coaching scorecards recorded yet.</div>';
                return;
            }
            container.innerHTML = relevant.map(c => `
                <div class="bg-slate-900/60 border border-slate-800 rounded-xl p-3 space-y-2">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-bold text-white">Score: <strong class="text-amber-400 text-sm">${c.score}/10</strong></span>
                        <span class="text-[10px] text-slate-500">${formatDate(c.session_date || c.created_at)}</span>
                    </div>
                    ${c.strengths ? `<div class="text-xs text-emerald-400 bg-emerald-500/10 p-2 rounded border border-emerald-500/20"><strong>Strengths:</strong> ${c.strengths}</div>` : ''}
                    ${c.areas_for_improvement ? `<div class="text-xs text-amber-300 bg-amber-500/10 p-2 rounded border border-amber-500/20"><strong>Improvement:</strong> ${c.areas_for_improvement}</div>` : ''}
                    ${c.action_items ? `<div class="text-xs text-indigo-300 bg-indigo-500/10 p-2 rounded border border-indigo-500/20"><strong>Action Items:</strong> ${c.action_items}</div>` : ''}
                </div>
            `).join('');
        } catch (e) {
            console.error("Failed to load coaching", e);
            container.innerHTML = '<div class="text-xs text-rose-400 py-2">Error loading coaching scorecards</div>';
        }
    }

    // ── Alternative Exit Modal (Section A) ────────────────────────────────────
    window.openExitModal = function(leadId) {
        const id = leadId || currentLeadId || window.currentLeadId;
        if (!id) return;
        document.getElementById('exit-lead-id').value = id;
        document.getElementById('exit-form').reset();
        handleExitStageChange();

        const modal = document.getElementById('exit-modal');
        const content = document.getElementById('exit-modal-content');
        modal.classList.remove('hidden');
        requestAnimationFrame(() => {
            modal.classList.remove('opacity-0');
            content.classList.remove('scale-95');
        });
        setTimeout(() => jumpToField(document.getElementById('exit-stage-select')), 250);
    };

    window.closeExitModal = function() {
        const modal = document.getElementById('exit-modal');
        const content = document.getElementById('exit-modal-content');
        modal.classList.add('opacity-0');
        content.classList.add('scale-95');
        setTimeout(() => modal.classList.add('hidden'), 200);
    };

    window.handleExitStageChange = function() {
        const stage = document.getElementById('exit-stage-select').value;
        const lostFields = document.getElementById('exit-closed-lost-fields');
        const nurtureFields = document.getElementById('exit-nurture-fields');
        if (stage === 'CLOSED_LOST') {
            lostFields.classList.remove('hidden');
            nurtureFields.classList.add('hidden');
        } else if (stage === 'NURTURE') {
            lostFields.classList.add('hidden');
            nurtureFields.classList.remove('hidden');
        } else {
            lostFields.classList.add('hidden');
            nurtureFields.classList.add('hidden');
        }
    };

    const exitForm = document.getElementById('exit-form');
    if (exitForm) {
        exitForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const leadId = document.getElementById('exit-lead-id').value;
            const target_stage = document.getElementById('exit-stage-select').value;
            const notes = document.getElementById('exit-notes').value;
            const payload = { target_stage, notes };

            if (target_stage === 'CLOSED_LOST') {
                payload.reason_code = document.getElementById('exit-reason-code').value;
                payload.competitor_name = document.getElementById('exit-competitor-name').value;
                payload.authorising_officer = document.getElementById('exit-authorising-officer').value;
            } else if (target_stage === 'NURTURE') {
                payload.campaign_name = document.getElementById('exit-campaign-name').value;
                payload.follow_up_date = document.getElementById('exit-follow-up-date').value;
            }

            try {
                const token = localStorage.getItem('crm_token');
                const res = await fetch(`/api/leads/${leadId}/exit`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) {
                    const err = await res.json().catch(()=>({}));
                    throw new Error(err.error || err.msg || "Failed to exit lead");
                }
                if (window.showToast) window.showToast(`Lead routed to ${target_stage} successfully!`, "success");
                closeExitModal();
                loadLeads();
                if (currentLeadId === parseInt(leadId)) {
                    openDrawer(leadId);
                }
            } catch (err) {
                console.error(err);
                if (window.showToast) window.showToast(err.message, "error");
            }
        });
    }

    // ── Post-Visit Debrief Modal (Fix 4 & M-07) ────────────────────────────────
    window.openDebriefModal = function(apptId) {
        document.getElementById('debrief-appt-id').value = apptId;
        document.getElementById('debrief-form').reset();
        const modal = document.getElementById('debrief-modal');
        const content = document.getElementById('debrief-modal-content');
        modal.classList.remove('hidden');
        requestAnimationFrame(() => {
            modal.classList.remove('opacity-0');
            content.classList.remove('scale-95');
        });
        setTimeout(() => jumpToField(document.getElementById('debrief-notes')), 250);
    };

    window.openDebriefModalForLead = async function(leadId) {
        const id = leadId || currentLeadId;
        if (!id) return;
        try {
            const token = localStorage.getItem('crm_token');
            const res = await fetch(`/api/leads/${id}/appointments`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const appts = await res.json();
                if (appts.length > 0) {
                    // Pick latest appointment
                    openDebriefModal(appts[appts.length - 1].id);
                    return;
                }
            }
            if (window.showToast) window.showToast("No appointment found. Book an appointment first.", "info");
        } catch (e) {
            console.error(e);
        }
    };

    window.closeDebriefModal = function() {
        const modal = document.getElementById('debrief-modal');
        const content = document.getElementById('debrief-modal-content');
        modal.classList.add('opacity-0');
        content.classList.add('scale-95');
        setTimeout(() => modal.classList.add('hidden'), 200);
    };

    const debriefForm = document.getElementById('debrief-form');
    if (debriefForm) {
        debriefForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const apptId = document.getElementById('debrief-appt-id').value;
            const payload = {
                notes: document.getElementById('debrief-notes').value,
                principal_objection: document.getElementById('debrief-objection-code').value || undefined,
                objection_intensity: document.getElementById('debrief-intensity').value,
                competitor_name: document.getElementById('debrief-competitor').value || undefined,
                executive_response: document.getElementById('debrief-response').value || undefined,
                next_action_type: document.getElementById('debrief-next-action-type').value,
                next_action_deadline: document.getElementById('debrief-next-action-deadline').value || undefined,
                mark_completed: true
            };

            try {
                const token = localStorage.getItem('crm_token');
                const res = await fetch(`/api/leads/appointments/${apptId}/debrief`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) {
                    const err = await res.json().catch(()=>({}));
                    throw new Error(err.error || err.msg || "Failed to submit debrief");
                }
                if (window.showToast) window.showToast("Post-visit debrief recorded! Stage updated to VISIT_COMPLETED.", "success");
                closeDebriefModal();
                loadLeads();
                if (currentLeadId) openDrawer(currentLeadId);
            } catch (err) {
                console.error(err);
                if (window.showToast) window.showToast(err.message, "error");
            }
        });
    }

    // ── Log Objection Modal (M-08) ────────────────────────────────────────────
    window.openObjectionModal = function(leadId) {
        const id = leadId || currentLeadId || window.currentLeadId;
        if (!id) return;
        document.getElementById('obj-lead-id').value = id;
        document.getElementById('objection-form').reset();
        const modal = document.getElementById('objection-modal');
        const content = document.getElementById('objection-modal-content');
        modal.classList.remove('hidden');
        requestAnimationFrame(() => {
            modal.classList.remove('opacity-0');
            content.classList.remove('scale-95');
        });
        setTimeout(() => focusFirstField(modal), 250);
    };

    window.closeObjectionModal = function() {
        const modal = document.getElementById('objection-modal');
        const content = document.getElementById('objection-modal-content');
        modal.classList.add('opacity-0');
        content.classList.add('scale-95');
        setTimeout(() => modal.classList.add('hidden'), 200);
    };

    const objectionForm = document.getElementById('objection-form');
    if (objectionForm) {
        objectionForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const leadId = document.getElementById('obj-lead-id').value;
            const payload = {
                category: document.getElementById('obj-category').value,
                specific_objection: document.getElementById('obj-specific').value,
                intensity: parseInt(document.getElementById('obj-intensity').value, 10),
                competitor_name: document.getElementById('obj-competitor').value || undefined,
                executive_response: document.getElementById('obj-response').value || undefined,
                is_principal: document.getElementById('obj-is-principal').checked,
                reactivation_eligible: document.getElementById('obj-reactivation').checked
            };

            try {
                const token = localStorage.getItem('crm_token');
                const res = await fetch(`/api/leads/${leadId}/objections`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) {
                    const err = await res.json().catch(()=>({}));
                    throw new Error(err.error || err.msg || "Failed to log objection");
                }
                if (window.showToast) window.showToast("Objection captured into Intelligence bank!", "success");
                closeObjectionModal();
                loadDrawerObjections(leadId);
            } catch (err) {
                console.error(err);
                if (window.showToast) window.showToast(err.message, "error");
            }
        });
    }

    // ── Manager Coaching Modal (M-05 & M-09) ──────────────────────────────────
    window.openCoachingModal = async function(leadId) {
        const id = leadId || currentLeadId || window.currentLeadId;
        document.getElementById('coach-lead-id').value = id || '';
        document.getElementById('coaching-form').reset();

        // Populate executive dropdown
        try {
            const token = localStorage.getItem('crm_token');
            const res = await fetch('/api/team/members', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const members = await res.json();
                const sel = document.getElementById('coach-executive-select');
                sel.innerHTML = members.map(m => `<option value="${m.id}">${m.full_name || m.username} (${m.role})</option>`).join('');
                if (currentLeadData && currentLeadData.assigned_to_id) {
                    sel.value = currentLeadData.assigned_to_id;
                }
            }
        } catch (e) {
            console.error(e);
        }

        const modal = document.getElementById('coaching-modal');
        const content = document.getElementById('coaching-modal-content');
        modal.classList.remove('hidden');
        requestAnimationFrame(() => {
            modal.classList.remove('opacity-0');
            content.classList.remove('scale-95');
        });
    };

    window.closeCoachingModal = function() {
        const modal = document.getElementById('coaching-modal');
        const content = document.getElementById('coaching-modal-content');
        modal.classList.add('opacity-0');
        content.classList.add('scale-95');
        setTimeout(() => modal.classList.add('hidden'), 200);
    };

    const coachingForm = document.getElementById('coaching-form');
    if (coachingForm) {
        coachingForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const leadId = document.getElementById('coach-lead-id').value;
            const payload = {
                opportunity_id: leadId ? parseInt(leadId, 10) : undefined,
                executive_id: parseInt(document.getElementById('coach-executive-select').value, 10),
                score: parseInt(document.getElementById('coach-score').value, 10),
                strengths: document.getElementById('coach-strengths').value,
                areas_for_improvement: document.getElementById('coach-improvements').value,
                action_items: document.getElementById('coach-action-items').value
            };

            try {
                const token = localStorage.getItem('crm_token');
                const res = await fetch('/api/leads/coaching', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) {
                    const err = await res.json().catch(()=>({}));
                    throw new Error(err.error || err.msg || "Failed to save coaching scorecard");
                }
                if (window.showToast) window.showToast("Manager Coaching scorecard saved!", "success");
                closeCoachingModal();
                if (leadId) loadDrawerCoaching(leadId);
            } catch (err) {
                console.error(err);
                if (window.showToast) window.showToast(err.message, "error");
            }
        });
    }

    // ── Bulk Import CSV Modal (M-01) ──────────────────────────────────────────
    window.openImportModal = function() {
        const modal = document.getElementById('import-modal');
        if (!modal) return;
        const form = document.getElementById('import-leads-form');
        if (form) form.reset();
        const text = document.getElementById('file-chosen-text');
        if (text) text.textContent = 'Drag and drop your .csv file here, or click to browse';
        const statusBox = document.getElementById('import-status-box');
        if (statusBox) {
            statusBox.className = 'hidden p-3 rounded-xl text-xs space-y-1';
            statusBox.innerHTML = '';
        }
        modal.classList.remove('hidden');
        modal.style.display = 'flex';
    };

    window.closeImportModal = function() {
        const modal = document.getElementById('import-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.style.display = 'none';
        }
    };

    const importLeadsBtn = document.getElementById('import-leads-btn');
    if (importLeadsBtn) {
        importLeadsBtn.addEventListener('click', openImportModal);
    }

    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('import-csv-file');
    if (dropZone && fileInput) {
        dropZone.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('border-indigo-500', 'bg-indigo-500/10');
        });
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('border-indigo-500', 'bg-indigo-500/10');
        });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-indigo-500', 'bg-indigo-500/10');
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                document.getElementById('file-chosen-text').textContent = `Selected: ${e.dataTransfer.files[0].name}`;
            }
        });
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                document.getElementById('file-chosen-text').textContent = `Selected: ${fileInput.files[0].name}`;
            }
        });
    }

    // NOTE: must NOT be named `importForm` — that identifier is already
    // declared above for #import-lead-form. Redeclaring it with `const` in the
    // same scope is a SyntaxError that kills this entire file, so the Add Lead
    // button and the leads table both silently stopped working.
    const csvImportForm = document.getElementById('import-leads-form');
    if (csvImportForm) {
        csvImportForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('import-csv-file');
            if (!fileInput.files || fileInput.files.length === 0) {
                if (window.showToast) window.showToast('Please select a CSV file first', 'error');
                return;
            }

            const submitBtn = document.getElementById('submit-import-btn');
            const statusBox = document.getElementById('import-status-box');
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg> Importing...`;

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            try {
                const token = localStorage.getItem('crm_token');
                const res = await fetch('/api/leads/import', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` },
                    body: formData
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    throw new Error(data.message || data.error || 'Import failed');
                }

                statusBox.className = 'p-3 rounded-xl text-xs space-y-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-300';
                statusBox.innerHTML = `
                    <div class="font-bold flex items-center gap-1.5">
                        <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                        Import Complete!
                    </div>
                    <div>${data.message}</div>
                    ${data.errors && data.errors.length > 0 ? `<div class="text-rose-400 mt-1">Warnings: ${data.errors.join(', ')}</div>` : ''}
                `;
                statusBox.classList.remove('hidden');

                if (window.showToast) window.showToast(`Imported ${data.imported} lead(s) successfully!`, 'success');
                setTimeout(() => {
                    closeImportModal();
                    loadLeads();
                }, 1500);
            } catch (err) {
                console.error(err);
                statusBox.className = 'p-3 rounded-xl text-xs space-y-1 bg-rose-500/10 border border-rose-500/30 text-rose-300';
                statusBox.innerHTML = `<strong>Error:</strong> ${err.message}`;
                statusBox.classList.remove('hidden');
                if (window.showToast) window.showToast(err.message, 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/></svg> <span>Start Import</span>`;
            }
        });
    }

    // Initial Load
    loadLeads();
});

