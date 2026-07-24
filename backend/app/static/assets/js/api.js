const API_BASE = '/api';

export async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem('crm_token');
  
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers
    });

    if (res.status === 401) {
      // Token expired or invalid — throw so caller can decide what to do
      throw new Error('Unauthorized');
    }

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.message || 'API Error');
    }

    return await res.json();
  } catch (err) {
    if (err.message !== 'Unauthorized') {
      console.error('API Error:', err);
    }
    throw err;
  }
}

export const AuthAPI = {
  login: (email, password) => apiFetch('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  verifyMFA: (code, tempToken) => apiFetch('/auth/verify-mfa', { method: 'POST', body: JSON.stringify({ code, tempToken }) }),
  logout: () => apiFetch('/auth/logout', { method: 'POST' }),
  refresh: () => apiFetch('/auth/refresh', { method: 'POST' }),
  getMe: () => apiFetch('/auth/me')
};

export const LeadsAPI = {
  list: (params) => apiFetch(`/leads?${new URLSearchParams(params)}`),
  get: (id) => apiFetch(`/leads/${id}`),
  create: (data) => apiFetch('/leads', { method: 'POST', body: JSON.stringify(data) }),
  updateStage: (id, stage) => apiFetch(`/leads/${id}/stage`, { method: 'PUT', body: JSON.stringify({ stage }) }),
  logCall: (id, data) => apiFetch(`/leads/${id}/calls`, { method: 'POST', body: JSON.stringify(data) })
};

export const DashboardAPI = {
  getStats: () => apiFetch('/dashboard/stats'),
  getFunnelData: () => apiFetch('/dashboard/funnel'),
  getHeatmapData: () => apiFetch('/dashboard/heatmap')
};

export const TeamAPI = {
  getUsers: () => apiFetch('/team/users'),
  createUser: (data) => apiFetch('/team/users', { method: 'POST', body: JSON.stringify(data) }),
  toggleUserStatus: (id) => apiFetch(`/team/users/${id}/toggle-status`, { method: 'POST' }),
  deactivateUser: (id) => apiFetch(`/team/users/${id}/deactivate`, { method: 'POST' }),
  updateUserColor: (id, color) => apiFetch(`/team/users/${id}/color`, { method: 'PUT', body: JSON.stringify({ calendar_color: color }) })
};
