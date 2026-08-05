// ============================================================
//  CRM Shared Sidebar — sidebar.js (RBAC v3)
//  Role-aware navigation for ADMIN and LEAD_OWNER
// ============================================================

(function () {
  const CURRENT = window.location.pathname.split('/').pop() || 'dashboard.html';
  const USER_ROLE = localStorage.getItem('crm_role') || 'LEAD_OWNER';
  const USER_COLOR = localStorage.getItem('crm_color') || '#6366f1';
  const USER_NAME = localStorage.getItem('crm_name') || 'User';
  const USER_AVATAR = localStorage.getItem('crm_avatar') && localStorage.getItem('crm_avatar') !== 'null' ? localStorage.getItem('crm_avatar') : '/assets/img/default-avatar.png';
  const IS_ADMIN = USER_ROLE === 'ADMIN';

  // Global fetch interceptor to catch 401 Unauthorized responses and log out
  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    const response = await originalFetch.apply(this, args);
    if (response.status === 401) {
      if (typeof window.doLogout === 'function') {
        window.doLogout();
      } else {
        localStorage.removeItem('crm_token');
        localStorage.removeItem('crm_role');
        localStorage.removeItem('crm_color');
        localStorage.removeItem('crm_name');
        window.location.href = '/index.html';
      }
    }
    return response;
  };

  // ----- ADMIN navigation modules -----
  const ADMIN_MODULES = [
    {
      section: 'Command Center',
      items: [
        { href: 'admin-dashboard.html', label: 'Dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
        { href: 'team.html', label: 'Team', icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z' },
        { href: 'lead-owners.html', label: 'Lead Owners', icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z' },
        { href: 'projects.html', label: 'Projects', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
      ]
    },
    {
      section: 'CRM & Data',
      items: [
        { href: 'leads.html', label: 'Leads', icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6' },
        { href: 'contacts.html', label: 'Clients', icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z' },
        { href: 'events.html', label: 'Events', icon: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' },
        { href: 'tasks.html', label: 'Tasks', icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z' },
        { href: 'activities.html', label: 'Activity Log', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
      ]
    },
    {
      section: 'Operations',
      items: [
        { href: 'sales.html', label: 'Sales', icon: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
        { href: 'expenses.html', label: 'Expenses', icon: 'M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z' },
        { href: 'tickets.html', label: 'Tickets', badgeColor: 'bg-rose-500', icon: 'M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z' },
        { href: 'messages.html', label: 'Messages', badgeColor: 'bg-indigo-500', icon: 'M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z' },
        { href: 'notes.html', label: 'Notes', icon: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z' },
      ]
    },
    {
      section: 'System',
      items: [
        { href: 'reports.html', label: 'Reports', icon: 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
        { href: 'help.html', label: 'Help & Support', icon: 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
        { href: 'settings.html', label: 'Settings', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' },
      ]
    }
  ];

  // ----- LEAD OWNER navigation modules -----
  const OWNER_MODULES = [
    {
      section: 'My Workspace',
      items: [
        { href: 'dashboard.html', label: 'Dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
      ]
    },
    {
      section: 'CRM & Data',
      items: [
        { href: 'leads.html', label: 'My Leads', icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6' },
        { href: 'contacts.html', label: 'My Clients', icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z' },
        { href: 'events.html', label: 'My Events', icon: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' },
        { href: 'tasks.html', label: 'My Tasks', icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z' },
        { href: 'activities.html', label: 'My Activities', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
      ]
    },
    {
      section: 'Operations',
      items: [
        { href: 'tickets.html', label: 'Tickets', badgeColor: 'bg-rose-500', icon: 'M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z' },
        { href: 'messages.html', label: 'Messages', badgeColor: 'bg-indigo-500', icon: 'M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z' },
        { href: 'notes.html', label: 'Notes', icon: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z' },
      ]
    },
    {
      section: 'System',
      items: [
        { href: 'reports.html', label: 'My Reports', icon: 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
        { href: 'help.html', label: 'Help & Support', icon: 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
      ]
    },
  ];

  const MODULES = IS_ADMIN ? ADMIN_MODULES : OWNER_MODULES;

  function buildSidebar() {
    const accentColor = IS_ADMIN ? '#6366f1' : USER_COLOR;
    const roleLabel = IS_ADMIN ? 'Main Admin' : 'Lead Owner';
    
    let html = `
      <aside class="sidebar glass-dark h-full flex flex-col border-r border-slate-800 relative z-20">
        <div class="p-5 flex items-center gap-3 border-b border-slate-800/60">
          <div id="sidebar-logo-container" class="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm bg-cover bg-center" style="background: linear-gradient(135deg, ${accentColor}, ${accentColor}cc)">
            <span id="sidebar-logo-text">SL</span>
          </div>
          <div>
            <div id="sidebar-company-name" class="font-bold text-sm tracking-tight text-white">Southeast CRM</div>
            <div class="text-xs" style="color: ${accentColor}">${roleLabel}</div>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto px-3 py-4 space-y-6 scrollbar-hide">
    `;

    for (const group of MODULES) {
      html += `
        <div>
          <div class="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 px-2">${group.section}</div>
          <nav class="space-y-0.5">
      `;
      for (const item of group.items) {
        const isActive = CURRENT === item.href || CURRENT === item.href.replace('.html', '');
        const activeStyle = isActive ? `style="background: ${accentColor}22; border-color: ${accentColor}55; color: white;"` : '';
        const activeClass = isActive
          ? 'border border-transparent'
          : 'text-slate-400 hover:text-white hover:bg-white/5 border border-transparent';

        const badgeId = `sidebar-badge-${item.label.toLowerCase()}`;

        html += `
          <div class="flex items-center gap-1 pr-1">
            <a href="/${item.href}" class="flex-1 flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${activeClass} group" ${activeStyle}>
              <svg class="w-4 h-4 flex-shrink-0 ${isActive ? '' : 'text-slate-500 group-hover:text-slate-300'}" fill="none" stroke="currentColor" viewBox="0 0 24 24" ${isActive ? `style="color:${accentColor}"` : ''}>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="${item.icon}"/>
              </svg>
              <span class="flex-1">${item.label}</span>
              <span id="${badgeId}" class="px-1.5 py-0.5 rounded-full text-[10px] font-bold text-white ${item.badgeColor || 'bg-slate-500'} hidden"></span>
            </a>
            <a href="/help.html?topic=${item.label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}" target="_blank" class="p-1.5 text-slate-500 hover:text-sky-400 hover:bg-slate-800 rounded-lg transition-colors shrink-0" title="User Manual for ${item.label}">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            </a>
          </div>
        `;
      }
      html += `</nav></div>`;
    }

    // Color indicator strip for Lead Owner
    const colorStrip = !IS_ADMIN ? `
      <div class="px-3 py-2">
        <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-900/50 border border-slate-800">
          <div class="w-3 h-3 rounded-full flex-shrink-0" style="background: ${USER_COLOR}"></div>
          <div class="text-[10px] text-slate-400">Your color — used across all views</div>
        </div>
      </div>
    ` : '';

    const initials = USER_NAME.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();

    html += `
        </div>
        ${colorStrip}
        <div class="p-3 border-t border-slate-800">
          <div class="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-all group">
            <img class="w-8 h-8 rounded-lg object-cover flex-shrink-0 cursor-pointer" src="${USER_AVATAR}" onclick="window.location.href = '/settings.html'" title="My Profile" />
            <div class="flex-1 min-w-0 cursor-pointer" onclick="window.location.href = '/settings.html'" title="My Profile">
              <div class="text-xs font-semibold text-white truncate hover:text-indigo-400 transition-colors">${USER_NAME}</div>
              <div class="text-[10px] text-slate-500 truncate">${roleLabel}</div>
            </div>
            <button onclick="window.doLogout && window.doLogout();" class="p-1.5 rounded-md hover:bg-white/10 text-slate-500 hover:text-rose-400 transition-colors" title="Log Out">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
              </svg>
            </button>
          </div>
        </div>
      </aside>
    `;
    return html;
  }

  // Auth guard — redirect to login if no token
  function authGuard() {
    const token = localStorage.getItem('crm_token');
    const page = window.location.pathname.split('/').pop();
    const isPublic = ['index.html', ''].includes(page);
    if (!isPublic && (!token || token === 'undefined')) {
      window.location.href = '/index.html';
      return false;
    }
    // Admin guard — prevent lead owners from accessing admin pages
    const adminPages = ['admin-dashboard.html', 'lead-owners.html'];
    const role = localStorage.getItem('crm_role');
    if (adminPages.includes(page) && role !== 'ADMIN') {
      window.location.href = '/dashboard.html';
      return false;
    }
    return true;
  }

  // Logout handler
  window.doLogout = async function () {
    const token = localStorage.getItem('crm_token');
    if (token) {
      try {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
      } catch (err) {
        console.error("Failed to log out session via API", err);
      }
    }
    localStorage.removeItem('crm_token');
    localStorage.removeItem('crm_role');
    localStorage.removeItem('crm_color');
    localStorage.removeItem('crm_name');
    localStorage.removeItem('crm_avatar');
    window.location.href = '/index.html';
  };
  window.logout = window.doLogout;

  // Toggle mobile drawer
  function toggleMobileSidebar(show) {
    const sidebar = document.querySelector('.sidebar');
    let backdrop = document.getElementById('sidebar-backdrop');
    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.id = 'sidebar-backdrop';
      backdrop.className = 'sidebar-backdrop';
      document.body.appendChild(backdrop);
      backdrop.addEventListener('click', () => toggleMobileSidebar(false));
    }

    if (!sidebar) return;
    const shouldOpen = show !== undefined ? show : !sidebar.classList.contains('mobile-open');
    if (shouldOpen) {
      sidebar.classList.add('mobile-open');
      backdrop.classList.add('active');
    } else {
      sidebar.classList.remove('mobile-open');
      backdrop.classList.remove('active');
    }
  }

  // Setup mobile navigation controls
  function setupMobileNav() {
    // Inject backdrop
    let backdrop = document.getElementById('sidebar-backdrop');
    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.id = 'sidebar-backdrop';
      backdrop.className = 'sidebar-backdrop';
      document.body.appendChild(backdrop);
      backdrop.addEventListener('click', () => toggleMobileSidebar(false));
    }

    // Inject hamburger button into page header if not present
    const header = document.querySelector('header');
    if (header && !document.getElementById('mobile-sidebar-toggle')) {
      const toggleBtn = document.createElement('button');
      toggleBtn.id = 'mobile-sidebar-toggle';
      toggleBtn.className = 'md:hidden p-1.5 mr-3 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors flex-shrink-0';
      toggleBtn.setAttribute('aria-label', 'Toggle Navigation');
      toggleBtn.innerHTML = `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>`;
      toggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleMobileSidebar();
      });

      // Insert at very beginning of header
      if (header.firstChild) {
        header.insertBefore(toggleBtn, header.firstChild);
      } else {
        header.appendChild(toggleBtn);
      }
    }

    // Auto close sidebar when clicking links inside sidebar
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
      sidebar.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => toggleMobileSidebar(false));
      });
    }
  }

  async function updateBadges() {
    const token = localStorage.getItem('crm_token');
    if (!token || token === 'undefined') return;

    try {
      const res = await fetch('/api/dashboard/badges', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) return;
      const data = await res.json();
      
      const setBadge = (id, count) => {
        const el = document.getElementById(id);
        if (el) {
          if (count > 0) {
            el.textContent = count;
            el.classList.remove('hidden');
          } else {
            el.classList.add('hidden');
          }
        }
      };

      setBadge('sidebar-badge-messages', data.messages);
      setBadge('sidebar-badge-tickets', data.tickets);
    } catch (e) {
      // silently fail in background
    }
  }

  async function loadBranding() {
    try {
      const res = await fetch('/api/settings/branding');
      if (!res.ok) return;
      const data = await res.json();
      
      const nameEl = document.getElementById('sidebar-company-name');
      const logoContainer = document.getElementById('sidebar-logo-container');
      const logoText = document.getElementById('sidebar-logo-text');
      
      if (nameEl && data.company_name) {
        nameEl.textContent = data.company_name;
        // Optionally update document title
        document.title = document.title.replace('Southeast CRM', data.company_name);
      }
      
      if (logoContainer && data.company_logo) {
        logoContainer.style.background = 'none';
        logoContainer.style.backgroundImage = `url(${data.company_logo})`;
        logoContainer.style.backgroundSize = 'cover';
        logoContainer.style.backgroundPosition = 'center';
        if (logoText) logoText.style.display = 'none';
      } else {
        const accentColor = IS_ADMIN ? '#6366f1' : USER_COLOR;
        if (logoContainer) {
          logoContainer.style.background = `linear-gradient(135deg, ${accentColor}, ${accentColor}cc)`;
        }
        if (logoText) {
          logoText.style.display = '';
          if (data.company_name) {
            const initials = data.company_name.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase();
            logoText.textContent = initials || 'SL';
          }
        }
      }
    } catch (e) {
      // silently fail
    }
  }
  window.loadBranding = loadBranding;
  window.updateBadges = updateBadges;

  // Init
  function init() {
    if (!authGuard()) return;
    const container = document.getElementById('sidebar-container');
    if (container) {
      container.innerHTML = buildSidebar();
      setupMobileNav();
      updateBadges();
      loadBranding();
      setInterval(updateBadges, 30000); // 30s polling
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
