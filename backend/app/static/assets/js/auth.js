import { AuthAPI } from './api.js';

let tempMfaToken = null;

function setupListeners() {
  initAuth();
  
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('email').value;
      const password = document.getElementById('password').value;
      await handleLogin(email, password);
    });
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupListeners);
} else {
  setupListeners();
}

async function initAuth() {
  const token = localStorage.getItem('crm_token');
  if (token && token !== 'undefined' && (window.location.pathname.endsWith('index.html') || window.location.pathname === '/')) {
    try {
      const user = await AuthAPI.getMe();
      if (user) {
        const role = localStorage.getItem('crm_role');
        window.location.href = role === 'ADMIN' ? '/admin-dashboard.html' : '/dashboard.html';
      }
    } catch (e) {
      localStorage.removeItem('crm_token');
      localStorage.removeItem('crm_role');
      localStorage.removeItem('crm_color');
      localStorage.removeItem('crm_name');
    }
  }
}

async function handleLogin(email, password) {
  const btn = document.getElementById('btn-text');
  const spinner = document.getElementById('btn-spinner');
  const errorEl = document.getElementById('login-error');
  if (errorEl) errorEl.textContent = '';
  btn.classList.add('hidden');
  spinner.classList.remove('hidden');

  try {
    const res = await AuthAPI.login(email, password);
    const token = res.access_token || res.token;
    
    // Store auth details
    localStorage.setItem('crm_token', token);
    if (res.role) localStorage.setItem('crm_role', res.role);
    if (res.color) localStorage.setItem('crm_color', res.color);
    if (res.full_name) localStorage.setItem('crm_name', res.full_name);
    
    // Redirect based on role
    const redirectTo = res.redirect_to || (res.role === 'ADMIN' ? 'admin-dashboard.html' : 'dashboard.html');
    window.location.href = '/' + redirectTo;
    
  } catch (err) {
    const msg = err.message || 'Login failed. Please check your credentials.';
    if (errorEl) {
      errorEl.textContent = msg;
      errorEl.classList.remove('hidden');
    }
    window.showToast && window.showToast(msg, 'error');
  } finally {
    btn.classList.remove('hidden');
    spinner.classList.add('hidden');
  }
}

export function logout() {
  localStorage.removeItem('crm_token');
  localStorage.removeItem('crm_role');
  localStorage.removeItem('crm_color');
  localStorage.removeItem('crm_name');
  window.location.href = '/index.html';
}

window.logout = logout;
