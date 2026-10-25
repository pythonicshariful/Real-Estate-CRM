/* ==========================================================================
   notifications.js — in-app notification bell (event reminders)
   --------------------------------------------------------------------------
   Shared by dashboard, leads, lead-details and events pages. It injects a
   bell with an unread badge into the page header, polls
   GET /api/notifications/ every 60s, and shows a dropdown panel of recent
   notifications. Clicking a notification marks it read and navigates to
   its lead (or the events page). Delivery is pull-based only — there is
   no push/email channel here; notifications appear while logged in.
   ========================================================================== */
(function () {
  'use strict';

  var POLL_MS = 60000;
  var timer = null;
  var panelOpen = false;

  function token() {
    try { return localStorage.getItem('crm_token'); } catch (e) { return null; }
  }

  function esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function fmtTime(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    return isNaN(d.getTime()) ? '' : d.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
  }

  /* ------------------------------------------------------------------ */
  /* Bell DOM (injected into the header's right-side container)          */
  /* ------------------------------------------------------------------ */
  function buildBell() {
    if (document.getElementById('crm-notif-bell')) return;
    var header = document.querySelector('header');
    if (!header) return;
    // Right-side container: last direct child div of the header on all
    // main pages (dashboard / leads / lead-details / events).
    var container = header.querySelector(':scope > div:last-child') || header;

    var wrap = document.createElement('div');
    wrap.id = 'crm-notif-bell';
    wrap.style.position = 'relative';
    wrap.innerHTML =
      '<button id="crm-notif-bell-btn" type="button" class="btn-ghost px-3 py-2 rounded-xl text-xs font-medium flex items-center gap-1.5" title="Notifications" aria-label="Notifications">' +
        '<span style="position:relative;display:inline-flex;">' +
          '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/></svg>' +
          '<span id="crm-notif-badge" class="hidden" style="position:absolute;top:-6px;right:-8px;min-width:16px;height:16px;border-radius:9999px;background:#f43f5e;color:#fff;font-size:10px;font-weight:700;display:flex;align-items:center;justify-content:center;padding:0 4px;">0</span>' +
        '</span>' +
      '</button>' +
      '<div id="crm-notif-panel" class="hidden" style="position:absolute;right:0;top:calc(100% + 8px);width:320px;max-width:92vw;max-height:380px;overflow-y:auto;background:#0f1019;border:1px solid #1e293b;border-radius:16px;z-index:60;box-shadow:0 10px 30px rgba(0,0,0,0.5);">' +
        '<div class="flex items-center justify-between px-4 py-3" style="position:sticky;top:0;background:#0f1019;border-bottom:1px solid #1e293b;">' +
          '<span class="text-sm font-bold text-white">Notifications</span>' +
          '<button id="crm-notif-read-all" type="button" class="text-xs font-semibold text-indigo-400 hover:text-indigo-300">Mark all read</button>' +
        '</div>' +
        '<div id="crm-notif-list" class="p-2"></div>' +
      '</div>';
    container.appendChild(wrap);

    document.getElementById('crm-notif-bell-btn').addEventListener('click', function (e) {
      e.stopPropagation();
      togglePanel();
    });
    document.getElementById('crm-notif-read-all').addEventListener('click', function (e) {
      e.stopPropagation();
      markAllRead();
    });
    document.addEventListener('click', function (e) {
      if (panelOpen && !wrap.contains(e.target)) closePanel();
    });
  }

  function togglePanel() {
    panelOpen ? closePanel() : openPanel();
  }

  function openPanel() {
    panelOpen = true;
    document.getElementById('crm-notif-panel').classList.remove('hidden');
    refresh(true);
  }

  function closePanel() {
    panelOpen = false;
    var p = document.getElementById('crm-notif-panel');
    if (p) p.classList.add('hidden');
  }

  /* ------------------------------------------------------------------ */
  /* API                                                                  */
  /* ------------------------------------------------------------------ */
  async function api(path, opts) {
    var t = token();
    if (!t) return null;
    var res = await fetch(path, Object.assign({
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + t }
    }, opts || {}));
    if (res.status === 401) {
      // Token dead — stop polling quietly; the app's own session handling
      // (sidebar.js) decides about logout.
      if (timer) { clearInterval(timer); timer = null; }
      return null;
    }
    if (!res.ok) return null;
    return res.json();
  }

  function renderList(items) {
    var list = document.getElementById('crm-notif-list');
    if (!list) return;
    if (!items || items.length === 0) {
      list.innerHTML = '<div class="text-xs text-slate-500 px-3 py-4 text-center">No notifications yet.</div>';
      return;
    }
    list.innerHTML = items.map(function (n) {
      return '<div class="crm-notif-item cursor-pointer px-3 py-2.5 rounded-xl hover:bg-slate-800/60 transition-colors" data-id="' + n.id + '" data-lead="' + (n.lead_id || '') + '" data-event="' + (n.event_id || '') + '" style="' + (n.is_read ? '' : 'background:rgba(99,102,241,0.08);') + '">' +
        '<div class="text-xs font-semibold ' + (n.is_read ? 'text-slate-300' : 'text-white') + '">' + esc(n.title) + '</div>' +
        (n.body ? '<div class="text-xs text-slate-400 mt-0.5">' + esc(n.body) + '</div>' : '') +
        '<div class="text-[10px] text-slate-500 mt-1">' + esc(fmtTime(n.created_at)) + '</div>' +
      '</div>';
    }).join('');
    list.querySelectorAll('.crm-notif-item').forEach(function (el) {
      el.addEventListener('click', function () {
        var id = el.getAttribute('data-id');
        var leadId = el.getAttribute('data-lead');
        var eventId = el.getAttribute('data-event');
        api('/api/notifications/' + id + '/read', { method: 'POST' }).catch(function () {});
        closePanel();
        if (leadId) window.location.href = '/lead-details.html?id=' + leadId;
        else if (eventId) window.location.href = '/events.html';
      });
    });
  }

  function updateBadge(unread) {
    var badge = document.getElementById('crm-notif-badge');
    if (!badge) return;
    if (unread > 0) {
      badge.textContent = unread > 99 ? '99+' : String(unread);
      badge.classList.remove('hidden');
      badge.style.display = 'flex';
    } else {
      badge.classList.add('hidden');
      badge.style.display = 'none';
    }
  }

  async function refresh(render) {
    var data = await api('/api/notifications/?limit=20');
    if (!data) return;
    updateBadge(data.unread_count || 0);
    if (render || panelOpen) renderList(data.notifications || []);
  }

  function start() {
    if (!token()) return;
    buildBell();
    refresh(false);
    timer = setInterval(function () { refresh(false); }, POLL_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }

  // Expose for other scripts (e.g. after creating an event, refresh now).
  window.crmNotificationsRefresh = function () { refresh(true); };
})();
