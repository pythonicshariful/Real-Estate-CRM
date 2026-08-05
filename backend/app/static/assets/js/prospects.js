// prospects.js
import { apiFetch } from './api.js';

document.addEventListener('DOMContentLoaded', () => {
    loadProposals();
    loadEstimates();

    // Set up basic navigation
    const tabs = document.querySelectorAll('.glass-dark.border-b button');
    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            tabs.forEach(t => {
                t.classList.remove('border-indigo-500', 'text-white');
                t.classList.add('border-transparent', 'text-slate-400');
            });
            e.target.classList.remove('border-transparent', 'text-slate-400');
            e.target.classList.add('border-indigo-500', 'text-white');
            
            // Simple tab switching logic could go here
            if (e.target.textContent.includes('Proposals')) {
                document.getElementById('estimates-table').classList.add('hidden');
                document.getElementById('proposals-table').classList.remove('hidden');
            } else {
                document.getElementById('proposals-table').classList.add('hidden');
                document.getElementById('estimates-table').classList.remove('hidden');
            }
        });
    });
});

async function loadProposals() {
    try {
        const data = await apiFetch('/prospects/proposals');
        const tbody = document.querySelector('#proposals-table tbody');
        if (!tbody) return;
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-slate-500 py-4">No proposals found</td></tr>';
            return;
        }

        tbody.innerHTML = data.map(p => `
            <tr>
                <td class="font-mono text-violet-400">PROP-${p.id}</td>
                <td class="text-white font-medium">${p.title}</td>
                <td>${p.contact_name}</td>
                <td class="text-emerald-400 font-semibold">৳${p.total_value.toLocaleString()}</td>
                <td><span class="badge badge-${p.status === 'DRAFT' ? 'pending' : (p.status === 'ACCEPTED' ? 'won' : 'active')}">${p.status}</span></td>
            </tr>
        `).join('');
    } catch (e) {
        console.error('Failed to load proposals', e);
    }
}

async function loadEstimates() {
    try {
        const data = await apiFetch('/prospects/estimates');
        const tbody = document.querySelector('#estimates-table tbody');
        if (!tbody) return;
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-slate-500 py-4">No estimates found</td></tr>';
            return;
        }

        tbody.innerHTML = data.map(e => `
            <tr>
                <td class="font-mono text-indigo-400">EST-${e.id}</td>
                <td class="text-white font-medium">${e.contact_name}</td>
                <td>${e.details || 'N/A'}</td>
                <td class="text-amber-400 font-semibold">৳${e.estimated_amount.toLocaleString()}</td>
                <td>${new Date(e.created_at).toLocaleDateString()}</td>
            </tr>
        `).join('');
    } catch (e) {
        console.error('Failed to load estimates', e);
    }
}
