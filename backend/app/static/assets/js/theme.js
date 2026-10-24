/* ==========================================================================
   Theme controller — light / dark with persistence
   Injects a segmented toggle into the page header (or sidebar footer).
   ========================================================================== */
(function () {
  'use strict';

  const STORAGE_KEY = 'crm_theme';
  const root = document.documentElement;

  /* ---------- apply as early as possible (prevents flash) ---------- */
  function preferred() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  function apply(theme) {
    root.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
    document.dispatchEvent(new CustomEvent('crm:themechange', { detail: { theme } }));
  }

  // set immediately (this script is loaded in <head> on themed pages)
  root.setAttribute('data-theme', preferred());

  const ICONS = {
    light: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.2 5.2l1.5 1.5M17.3 17.3l1.5 1.5M18.8 5.2l-1.5 1.5M6.7 17.3l-1.5 1.5"/></svg>',
    dark:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.5 14.2A8.5 8.5 0 1 1 9.8 3.5a6.8 6.8 0 0 0 10.7 10.7Z"/></svg>'
  };

  function buildToggle() {
    const wrap = document.createElement('div');
    wrap.className = 'theme-toggle';
    wrap.setAttribute('role', 'group');
    wrap.setAttribute('aria-label', 'Colour theme');

    ['light', 'dark'].forEach(function (t) {
      const b = document.createElement('button');
      b.type = 'button';
      b.dataset.themeValue = t;
      b.title = t === 'light' ? 'Light theme' : 'Dark theme';
      b.setAttribute('aria-label', t === 'light' ? 'Use light theme' : 'Use dark theme');
      b.innerHTML = ICONS[t];
      b.addEventListener('click', function () { apply(t); sync(); });
      wrap.appendChild(b);
    });
    return wrap;
  }

  function sync() {
    const cur = root.getAttribute('data-theme') || 'dark';
    document.querySelectorAll('.theme-toggle button').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.themeValue === cur));
    });
    const m = document.querySelector('meta[name="theme-color"]');
    if (m) m.setAttribute('content', cur === 'light' ? '#F0FDFA' : '#080E16');
  }

  function mount() {
    // 1) explicit placeholder
    const slot = document.querySelector('[data-theme-toggle]');
    if (slot && !slot.querySelector('.theme-toggle')) {
      slot.appendChild(buildToggle());
      sync();
      return;
    }
    // 2) page header — first flex container in the top area
    const header = document.querySelector('header, .topbar, [data-theme-slot="header"]');
    if (header && !header.querySelector('.theme-toggle')) {
      const toggle = buildToggle();
      toggle.style.marginLeft = 'auto';
      header.appendChild(toggle);
      sync();
      return;
    }
    // 3) sidebar footer
    const sidebar = document.querySelector('.sidebar, aside');
    if (sidebar && !sidebar.querySelector('.theme-toggle')) {
      const toggle = buildToggle();
      toggle.style.margin = '12px 16px 18px';
      sidebar.appendChild(toggle);
      sync();
    }
  }

  window.crmTheme = {
    get: function () { return root.getAttribute('data-theme') || 'dark'; },
    set: apply,
    toggle: function () { apply(window.crmTheme.get() === 'light' ? 'dark' : 'light'); }
  };

  // keyboard shortcut: Shift + D
  document.addEventListener('keydown', function (e) {
    if (e.shiftKey && (e.key === 'D' || e.key === 'd') &&
        !/^(INPUT|TEXTAREA|SELECT)$/.test((e.target.tagName || ''))) {
      window.crmTheme.toggle();
    }
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
})();
