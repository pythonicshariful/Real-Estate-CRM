/* ==========================================================================
   crm-store.js — safe storage bootstrap
   --------------------------------------------------------------------------
   Must be the FIRST script on every page.

   Problem it solves
   -----------------
   When the CRM is embedded in a sandboxed iframe (sandbox="allow-scripts"
   without allow-same-origin — which is what in-app previews and many embeds
   use), the document gets an opaque origin and *any* access to
   `window.localStorage` throws a SecurityError:

       Failed to read the 'localStorage' property from 'Window':
       The document is sandboxed and lacks the 'allow-same-origin' flag.

   The login flow stored the JWT in localStorage, so that write threw, the
   session was never persisted and the app behaved as if it logged you
   straight back out.

   This script probes localStorage once. If it works, nothing changes. If it
   is blocked, it installs an API-compatible shim backed by `window.name`,
   which survives same-tab navigation (unlike an in-memory store) and needs
   no permissions. Every existing `localStorage.getItem(...)` call in the
   codebase keeps working untouched.
   ========================================================================== */
(function () {
  'use strict';

  var PROBE = '__crm_ls_probe__';
  var works = false;

  try {
    window.localStorage.setItem(PROBE, '1');
    window.localStorage.removeItem(PROBE);
    works = true;
  } catch (e) {
    works = false;
  }

  if (works) {
    window.crmStorageMode = 'localStorage';
    return;
  }

  /* ---------------- fallback store ------------------------------------- */
  var NS = '__crmstore__:';
  var memory = {};          // last-resort, survives only within one document

  function readAll() {
    try {
      if (typeof window.name === 'string' && window.name.indexOf(NS) === 0) {
        return JSON.parse(window.name.slice(NS.length)) || {};
      }
    } catch (e) { /* corrupted — start clean */ }
    return memory;
  }

  function writeAll(obj) {
    memory = obj;                       // always keep the in-document copy
    try {
      window.name = NS + JSON.stringify(obj);
    } catch (e) { /* quota or blocked — memory copy still holds */ }
  }

  function makeShim() {
    return {
      getItem: function (k) {
        var all = readAll();
        return Object.prototype.hasOwnProperty.call(all, k) ? all[k] : null;
      },
      setItem: function (k, v) {
        var all = readAll();
        all[k] = String(v);
        writeAll(all);
      },
      removeItem: function (k) {
        var all = readAll();
        delete all[k];
        writeAll(all);
      },
      clear: function () { writeAll({}); },
      key: function (i) {
        var keys = Object.keys(readAll());
        return i >= 0 && i < keys.length ? keys[i] : null;
      },
      get length() { return Object.keys(readAll()).length; }
    };
  }

  var shim = makeShim();

  function install(name) {
    try {
      Object.defineProperty(window, name, {
        configurable: true,
        enumerable: true,
        get: function () { return shim; }
      });
      return window[name] === shim;
    } catch (e) {
      try {
        window[name] = shim;
        return window[name] === shim;
      } catch (e2) {
        return false;
      }
    }
  }

  install('localStorage');
  install('sessionStorage');

  window.crmStorageMode = 'window.name (sandbox fallback)';
})();


/* ==========================================================================
   Sandboxed-frame form shim
   --------------------------------------------------------------------------
   In a frame with sandbox="allow-scripts" (no allow-forms) the browser
   refuses form submission *before* it fires the `submit` event, per the HTML
   spec step "if form cannot navigate, return". Every handler written as
   form.addEventListener('submit', e => { e.preventDefault(); ... }) therefore
   never runs — the login button just does nothing.

   We cannot lift the frame's sandbox, but we can fire the event ourselves.
   This shim is installed only when the document really is sandboxed
   (window.origin === 'null'), so a normal browser behaves exactly as before.
   ========================================================================== */
(function () {
  'use strict';

  var sandboxed = false;
  try {
    sandboxed = (String(window.origin) === 'null');
  } catch (e) {
    sandboxed = true;
  }
  window.crmSandboxed = sandboxed;
  if (!sandboxed) return;

  function fireSubmitters(form, submitter) {
    var ev;
    try {
      ev = new SubmitEvent('submit', { bubbles: true, cancelable: true, submitter: submitter });
    } catch (e) {
      ev = new Event('submit', { bubbles: true, cancelable: true });
    }
    form.dispatchEvent(ev);
  }

  document.addEventListener('click', function (e) {
    var btn = e.target && e.target.closest
      ? e.target.closest('button[type="submit"], input[type="submit"], button:not([type])')
      : null;
    if (!btn) return;
    var form = btn.form || (btn.closest ? btn.closest('form') : null);
    if (!form) return;
    e.preventDefault();
    fireSubmitters(form, btn);
  }, true);

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter') return;
    var el = e.target;
    if (!el || !el.form || el.tagName === 'TEXTAREA') return;
    e.preventDefault();
    fireSubmitters(el.form, null);
  }, true);
})();
