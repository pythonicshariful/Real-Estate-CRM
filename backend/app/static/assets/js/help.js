import { apiFetch } from './api.js';

document.addEventListener('DOMContentLoaded', () => {
    loadArticles();
});

async function loadArticles() {
    try {
        const data = await apiFetch('/help/articles');
        const container = document.getElementById('articles-container');
        if (!container) return;

        if (data.length === 0) {
            container.innerHTML = '<div class="text-sm text-slate-400">No articles published yet.</div>';
            return;
        }

        container.innerHTML = data.map(article => `
            <details class="bg-white/5 border border-white/10 rounded-xl p-4 cursor-pointer group">
              <summary class="text-sm font-semibold text-white outline-none flex items-center justify-between">
                <span>${article.title}</span>
                <span class="text-xs text-indigo-400 font-normal">${article.category}</span>
              </summary>
              <div class="mt-3 text-xs text-slate-400 leading-relaxed border-t border-white/10 pt-3">
                ${article.content}
              </div>
            </details>
        `).join('');
    } catch (e) {
        console.error('Failed to load articles', e);
    }
}
