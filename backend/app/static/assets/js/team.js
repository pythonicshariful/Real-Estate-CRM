import { TeamAPI, AuthAPI } from './api.js';

function setupTeamListeners() {
  loadUsers();

  const openModalBtn = document.getElementById('open-create-user-modal');
  const closeModalBtn = document.getElementById('close-create-user-modal');
  const modal = document.getElementById('create-user-modal');
  const form = document.getElementById('create-user-form');

  if (openModalBtn && modal) {
    openModalBtn.addEventListener('click', () => {
      modal.classList.remove('hidden');
    });
  }

  if (closeModalBtn && modal) {
    closeModalBtn.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('user-email').value.trim();
      const full_name = document.getElementById('user-name').value.trim();
      const password = document.getElementById('user-password').value;
      const role = document.getElementById('user-role').value;
      const phone = document.getElementById('user-phone').value.trim();
      const max_capacity = parseInt(document.getElementById('user-capacity').value || '30', 10);

      const btn = document.getElementById('create-user-submit-btn');
      if (btn) btn.disabled = true;

      try {
        const res = await TeamAPI.createUser({
          email,
          full_name,
          password,
          role,
          phone,
          max_lead_capacity: max_capacity
        });
        window.showToast(res.message || 'User account created successfully!', 'success');
        modal.classList.add('hidden');
        form.reset();
        await loadUsers();
      } catch (err) {
        window.showToast(err.message || 'Failed to create user', 'error');
      } finally {
        if (btn) btn.disabled = false;
      }
    });
  }
}

async function loadUsers() {
  const container = document.getElementById('team-users-list');
  if (!container) return;

  try {
    const users = await TeamAPI.getUsers();
    container.innerHTML = '';

    if (!users || users.length === 0) {
      container.innerHTML = `<div class="col-span-full text-center py-8 text-slate-400">No team accounts found.</div>`;
      return;
    }

    users.forEach(user => {
      const card = document.createElement('div');
      card.className = 'glass p-5 rounded-2xl flex flex-col justify-between space-y-4 border border-white/10 hover:border-indigo-500/40 transition-all';
      
      const initials = (user.full_name || user.email).split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
      
      let roleBadgeColor = 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30';
      if (user.role === 'ADMIN' || user.role === 'CEO') roleBadgeColor = 'bg-rose-500/20 text-rose-300 border-rose-500/30';
      if (user.role === 'GM' || user.role === 'MANAGER') roleBadgeColor = 'bg-amber-500/20 text-amber-300 border-amber-500/30';

      const statusBadge = user.is_active 
        ? '<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Active</span>'
        : '<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-500/20 text-slate-400 border border-slate-500/30">Deactivated</span>';

      card.innerHTML = `
        <div class="flex items-start justify-between">
          <div class="flex items-center gap-3">
            <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white font-bold text-lg shadow-lg">
              ${initials}
            </div>
            <div>
              <div class="font-semibold text-white text-base">${user.full_name || 'N/A'}</div>
              <div class="text-xs text-slate-400">${user.email}</div>
            </div>
          </div>
          ${statusBadge}
        </div>

        <div class="grid grid-cols-2 gap-2 text-xs py-2 border-y border-white/5 text-slate-300">
          <div>
            <span class="text-slate-500 block">Role</span>
            <span class="px-2 py-0.5 inline-block rounded text-[11px] font-semibold border ${roleBadgeColor} mt-0.5">${user.role}</span>
          </div>
          <div>
            <span class="text-slate-500 block">Calendar Color</span>
            <input type="color" data-id="${user.id}" class="color-picker-input mt-1 bg-transparent border-0 w-8 h-8 p-0 cursor-pointer rounded-lg" value="${user.calendar_color || '#6366f1'}">
          </div>
        </div>

        <div class="flex items-center justify-between text-xs pt-1">
          <span class="text-slate-400">${user.phone || 'No Phone'}</span>
          <button data-id="${user.id}" class="toggle-status-btn px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${user.is_active ? 'bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30' : 'bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30'}">
            ${user.is_active ? 'Deactivate' : 'Activate'}
          </button>
        </div>
      `;

      container.appendChild(card);
    });

    // Attach toggle status listeners
    document.querySelectorAll('.toggle-status-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const userId = e.currentTarget.dataset.id;
        try {
          const res = await TeamAPI.toggleUserStatus(userId);
          window.showToast(res.message || 'Status updated', 'info');
          await loadUsers();
        } catch (err) {
          window.showToast(err.message || 'Failed to toggle status', 'error');
        }
      });
    });

    // Attach color picker listeners
    document.querySelectorAll('.color-picker-input').forEach(picker => {
      picker.addEventListener('change', async (e) => {
        const userId = e.currentTarget.dataset.id;
        const newColor = e.currentTarget.value;
        try {
          await TeamAPI.updateUserColor(userId, newColor);
          window.showToast('Calendar color updated', 'success');
        } catch (err) {
          window.showToast(err.message || 'Failed to update color', 'error');
        }
      });
    });

  } catch (err) {
    console.error('Failed to load team users:', err);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupTeamListeners);
} else {
  setupTeamListeners();
}
