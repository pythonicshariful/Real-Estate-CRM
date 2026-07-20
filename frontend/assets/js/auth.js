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

  const verifyMfaBtn = document.getElementById('verify-mfa');
  if (verifyMfaBtn) {
    verifyMfaBtn.addEventListener('click', async () => {
      const inputs = document.querySelectorAll('.mfa-input');
      const code = Array.from(inputs).map(i => i.value).join('');
      if (code.length === 6) {
        await handleMFA(code);
      } else {
        window.showToast('Please enter 6 digit code', 'error');
      }
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
      if (user) window.location.href = '/dashboard.html';
    } catch (e) {
      localStorage.removeItem('crm_token');
    }
  }
}

async function handleLogin(email, password) {
  const btn = document.getElementById('btn-text');
  const spinner = document.getElementById('btn-spinner');
  btn.classList.add('hidden');
  spinner.classList.remove('hidden');

  try {
    const res = await AuthAPI.login(email, password);
    const token = res.access_token || res.token;
    if (res.mfaRequired || res.mfa_required) {
      tempMfaToken = token;
      document.getElementById('step-1').classList.add('hidden');
      document.getElementById('step-mfa').classList.remove('hidden');
      document.querySelector('.mfa-input').focus();
    } else {
      localStorage.setItem('crm_token', token);
      window.location.href = '/dashboard.html';
    }
  } catch (err) {
    window.showToast && window.showToast(err.message, 'error');
  } finally {
    btn.classList.remove('hidden');
    spinner.classList.add('hidden');
  }
}

async function handleMFA(code) {
  try {
    const res = await AuthAPI.verifyMFA(code, tempMfaToken);
    const token = res.access_token || res.token;
    localStorage.setItem('crm_token', token);
    window.location.href = '/dashboard.html';
  } catch (err) {
    window.showToast && window.showToast(err.message, 'error');
  }
}

export function logout() {
  localStorage.removeItem('crm_token');
  window.location.href = '/index.html';
}

window.logout = logout;
