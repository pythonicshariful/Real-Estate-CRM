// ============================================================
//  CRM Shared Sidebar — sidebar.js (RBAC v3)
//  Role-aware navigation for ADMIN and LEAD_OWNER
// ============================================================

(function () {
  const CURRENT = window.location.pathname.split('/').pop() || 'dashboard.html';
  const USER_ROLE = localStorage.getItem('crm_role') || 'LEAD_OWNER';
  const USER_COLOR = localStorage.getItem('crm_color') || '#6366f1';
  const USER_NAME = localStorage.getItem('crm_name') || 'User';
  const IS_ADMIN = USER_ROLE === 'ADMIN';

  // ----- ADMIN navigation modules -----
  const ADMIN_MODULES = [
    {
      section: 'Command Center',
      items: [
        { href: 'admin-dashboard.html', label: 'Admin Dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
        { href: 'lead-owners.html', label: 'Lead Owners', icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z' },
      ]
    },
    {
      section: 'All Data',
      items: [
        { href: 'leads.html', label: 'All Leads', icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6' },
        { href: 'events.html', label: 'All Events', icon: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' },
        { href: 'reports.html', label: 'Reports', icon: 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
      ]
    },
    {
      section: 'Organization',
      items: [
        { href: 'projects.html', label: 'Projects', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
        { href: 'settings.html', label: 'Settings', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' },
      ]
    },
  ];

  // ----- LEAD OWNER navigation modules -----
  const OWNER_MODULES = [
    {
      section: 'My Workspace',
      items: [
        { href: 'dashboard.html', label: 'My Dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
        { href: 'leads.html', label: 'My Leads', icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6' },
        { href: 'events.html', label: 'My Events', icon: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' },
      ]
    },
    {
      section: 'Tools',
      items: [
        { href: 'notes.html', label: 'My Notes', icon: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z' },
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
          <div class="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm" style="background: linear-gradient(135deg, ${accentColor}, ${accentColor}cc)">SL</div>
          <div>
            <div class="font-bold text-sm tracking-tight text-white">Southeast CRM</div>
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

        html += `
          <a href="/${item.href}" class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${activeClass} group" ${activeStyle}>
            <svg class="w-4 h-4 flex-shrink-0 ${isActive ? '' : 'text-slate-500 group-hover:text-slate-300'}" fill="none" stroke="currentColor" viewBox="0 0 24 24" ${isActive ? `style="color:${accentColor}"` : ''}>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="${item.icon}"/>
            </svg>
            <span class="flex-1">${item.label}</span>
            ${item.badge ? `<span class="px-1.5 py-0.5 rounded-full text-[10px] font-bold text-white ${item.badgeColor}">${item.badge}</span>` : ''}
          </a>
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
          <div class="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 cursor-pointer transition-all group" onclick="window.doLogout && window.doLogout()">
            <div class="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-xs flex-shrink-0" style="background: ${accentColor}">
              ${initials}
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-xs font-semibold text-white truncate">${USER_NAME}</div>
              <div class="text-[10px] text-slate-500 truncate">${roleLabel}</div>
            </div>
            <svg class="w-4 h-4 text-slate-600 group-hover:text-rose-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
            </svg>
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
  window.doLogout = function () {
    localStorage.removeItem('crm_token');
    localStorage.removeItem('crm_role');
    localStorage.removeItem('crm_color');
    localStorage.removeItem('crm_name');
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

  // Init
  function init() {
    if (!authGuard()) return;
    const container = document.getElementById('sidebar-container');
    if (container) {
      container.innerHTML = buildSidebar();
      setupMobileNav();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
