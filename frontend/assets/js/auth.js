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
  
  const verifyBtn = document.getElementById('verify-mfa');
  if (verifyBtn) {
    verifyBtn.addEventListener('click', async () => {
      await handleVerifyMfa();
    });
  }
  
  const mfaInputs = document.querySelectorAll('.mfa-input');
  mfaInputs.forEach((input, index) => {
    input.addEventListener('input', (e) => {
      if (e.target.value.length === 1 && index < mfaInputs.length - 1) {
        mfaInputs[index + 1].focus();
      }
    });
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && e.target.value === '' && index > 0) {
        mfaInputs[index - 1].focus();
      }
    });
  });
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
    
    if (res.mfa_required) {
      tempMfaToken = token;
      const promptEl = document.getElementById('mfa-prompt-text');
      if (promptEl) {
        if (res.mfa_type === 'email') {
          promptEl.textContent = 'Enter the 6-digit code sent to your email.';
        } else {
          promptEl.textContent = 'Enter the 6-digit code from your authenticator app.';
        }
      }
      document.getElementById('step-1').classList.add('hidden');
      document.getElementById('step-mfa').classList.remove('hidden');
      const firstInput = document.querySelector('.mfa-input');
      if (firstInput) firstInput.focus();
      return;
    }
    
    // Store auth details
    localStorage.setItem('crm_token', token);
    if (res.role) localStorage.setItem('crm_role', res.role);
    if (res.color) localStorage.setItem('crm_color', res.color);
    if (res.full_name) localStorage.setItem('crm_name', res.full_name);
    if (res.avatar_url) localStorage.setItem('crm_avatar', res.avatar_url);
    
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

async function handleVerifyMfa() {
  const inputs = document.querySelectorAll('.mfa-input');
  const code = Array.from(inputs).map(i => i.value).join('');
  if (code.length !== 6) {
    if (window.showToast) window.showToast('Please enter the full 6-digit code', 'error');
    return;
  }
  
  const btn = document.getElementById('verify-mfa');
  btn.textContent = 'Verifying...';
  
  try {
    const res = await fetch('/api/auth/verify-mfa', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${tempMfaToken}`
      },
      body: JSON.stringify({ token: code })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.msg || data.message || 'MFA Verification failed');
    
    // Store new full token
    localStorage.setItem('crm_token', data.access_token);
    
    // Re-fetch me to get full info and role to redirect properly
    const meRes = await fetch('/api/auth/me', { headers: { 'Authorization': `Bearer ${data.access_token}` } });
    const me = await meRes.json();
    
    if (me.role) localStorage.setItem('crm_role', me.role);
    if (me.calendar_color) localStorage.setItem('crm_color', me.calendar_color);
    if (me.full_name) localStorage.setItem('crm_name', me.full_name);
    if (me.avatar_url) localStorage.setItem('crm_avatar', me.avatar_url);
    
    window.location.href = (me.role === 'ADMIN' || me.role === 'UserRole.ADMIN') ? '/admin-dashboard.html' : '/dashboard.html';
    
  } catch (err) {
    if (window.showToast) window.showToast(err.message, 'error');
    btn.textContent = 'Verify & Continue';
  }
}

export function logout() {
  localStorage.removeItem('crm_token');
  localStorage.removeItem('crm_role');
  localStorage.removeItem('crm_color');
  localStorage.removeItem('crm_name');
  localStorage.removeItem('crm_avatar');
  window.location.href = '/index.html';
}

window.logout = logout;
