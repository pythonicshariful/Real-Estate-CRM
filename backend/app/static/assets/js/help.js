// assets/js/help.js

document.addEventListener('DOMContentLoaded', () => {
    loadArticles();
    handleDirectLink();
});

const ARTICLES = [
    {
        id: 'dashboard',
        title: 'Dashboard Overview',
        category: 'Command Center',
        content: `
            <p class="mb-2">The Dashboard is your central hub for tracking CRM performance. It provides high-level metrics, upcoming tasks, and recent activities.</p>
            <ul class="list-disc pl-4 space-y-1">
                <li><strong>KPIs:</strong> Track total leads, active clients, monthly sales, and unresolved tickets.</li>
                <li><strong>Pipeline:</strong> View a funnel of how leads progress from "New" to "Won" or "Lost".</li>
                <li><strong>Recent Activity:</strong> An audit trail of the latest actions taken by your team members.</li>
            </ul>
        `
    },
    {
        id: 'team',
        title: 'Team & User Management',
        category: 'Command Center',
        content: `
            <p class="mb-2">As an Admin, you can manage the CRM access for all team members from the Team page.</p>
            <ul class="list-disc pl-4 space-y-1">
                <li><strong>Roles:</strong> Assign roles such as System Admin, Lead Owner, Manager, or Executive.</li>
                <li><strong>Lead Capacity:</strong> Set the maximum number of leads an individual can handle at one time.</li>
                <li><strong>Password Resets:</strong> Securely reset a team member's password if they lose access.</li>
            </ul>
        `
    },
    {
        id: 'lead-owners',
        title: 'Managing Lead Owners & Schedules',
        category: 'Command Center',
        content: `
            <p class="mb-2">Lead Owners are users who directly interact with incoming leads (e.g. Sales Executives).</p>
            <ul class="list-disc pl-4 space-y-1">
                <li><strong>Auto-Assignment:</strong> Leads coming from Meta Webhooks automatically round-robin to active Lead Owners.</li>
                <li><strong>Scheduling:</strong> Click the "Schedule" button on a Lead Owner's profile to define the exact dates and times they are active to receive automated incoming leads.</li>
                <li><strong>Unassigned Leads:</strong> If no Lead Owner is scheduled during the time a lead arrives, it goes to "Pending" status for manual assignment.</li>
            </ul>
        `
    },
    {
        id: 'projects',
        title: 'Managing Real Estate Projects',
        category: 'Command Center',
        content: `
            <p class="mb-2">Projects define the properties or campaigns you are currently selling.</p>
            <p>You can create a project with a specific ID, which is used when tagging leads or tracking specific ad campaign performance. Assigning a project to a lead helps you organize and filter your sales pipeline by location or property type.</p>
        `
    },
    {
        id: 'leads',
        title: 'Lead Management & Pipelines',
        category: 'CRM & Data',
        content: `
            <p class="mb-2">The Leads page is the core of your sales operations.</p>
            <ul class="list-disc pl-4 space-y-1">
                <li><strong>Pipeline Stages:</strong> Move leads through stages: New &rarr; Contacted &rarr; Qualified &rarr; Proposal &rarr; Won/Lost.</li>
                <li><strong>Temperatures:</strong> Tag leads as Hot, Warm, or Cold based on their buying intent.</li>
                <li><strong>Bulk Assignment:</strong> Admins can select multiple leads using checkboxes and use the "Bulk Assign" button to redistribute leads across the team.</li>
                <li><strong>Converting:</strong> Once a lead is "Won", they can be converted into a Client for long-term relationship management.</li>
            </ul>
        `
    },
    {
        id: 'clients',
        title: 'Client Management',
        category: 'CRM & Data',
        content: `
            <p class="mb-2">Clients are leads that have successfully converted into paying customers or long-term relationships.</p>
            <p>From the Clients page, you can log ongoing notes, track past purchase history (Sales), and maintain their contact information. Use this area for after-sales support and retention.</p>
        `
    },
    {
        id: 'events',
        title: 'Events & Calendar Scheduling',
        category: 'CRM & Data',
        content: `
            <p class="mb-2">Use the Events calendar to schedule client meetings, property viewings, and follow-up calls.</p>
            <ul class="list-disc pl-4 space-y-1">
                <li><strong>Creating Events:</strong> Click on any date to schedule a new event. You can link the event directly to a specific Lead or Client.</li>
                <li><strong>Reminders:</strong> Setting a time for the event ensures it appears on your daily agenda on the Dashboard.</li>
            </ul>
        `
    },
    {
        id: 'tasks',
        title: 'Task Tracking',
        category: 'CRM & Data',
        content: `
            <p class="mb-2">Keep your day organized by tracking actionable Tasks.</p>
            <p>Tasks can be assigned to yourself or to other team members. You can set due dates, priority levels, and link them to specific leads to ensure nothing falls through the cracks.</p>
        `
    },
    {
        id: 'activity-log',
        title: 'Activity Log',
        category: 'CRM & Data',
        content: `
            <p class="mb-2">The Activity Log provides a chronological timeline of interactions.</p>
            <p>Every time you call a lead, send an email, or have a meeting, it should be logged here. This creates a transparent history so any team member can pick up the relationship exactly where you left off.</p>
        `
    },
    {
        id: 'sales',
        title: 'Sales & Invoicing',
        category: 'Operations',
        content: `
            <p class="mb-2">The Sales page allows you to track revenue and closed deals.</p>
            <p>When a property is sold or a deal is finalized, record the transaction here. You can generate invoices, track payment status (Paid, Pending, Overdue), and attribute the sale to a specific Lead Owner for commission tracking.</p>
        `
    },
    {
        id: 'expenses',
        title: 'Expense Management',
        category: 'Operations',
        content: `
            <p class="mb-2">Track your operational costs, marketing spend, and travel expenses.</p>
            <p>Logging your expenses allows the CRM to calculate your net ROI against the revenue tracked in the Sales module. You can categorize expenses to see exactly where your budget is going.</p>
        `
    },
    {
        id: 'tickets',
        title: 'Support Tickets',
        category: 'Operations',
        content: `
            <p class="mb-2">Manage customer complaints, maintenance requests, or after-sales support.</p>
            <p>Tickets can be assigned a priority and status (Open, In Progress, Resolved). Keeping communication inside the ticket ensures that your support team handles client issues efficiently without cluttering the sales pipeline.</p>
        `
    },
    {
        id: 'messages',
        title: 'Internal Team Messaging',
        category: 'Operations',
        content: `
            <p class="mb-2">Communicate with your team in real-time without leaving the CRM.</p>
            <p>Select a team member from the left sidebar to start a chat. Unread messages will display a notification badge on the sidebar icon so you never miss an important update.</p>
        `
    },
    {
        id: 'notes',
        title: 'Personal Notes',
        category: 'Operations',
        content: `
            <p class="mb-2">A private scratchpad for your own personal use.</p>
            <p>Notes created here are visible only to you. Use this to jot down quick reminders, draft emails, or keep track of internal to-do lists that don't belong in the public CRM records.</p>
        `
    },
    {
        id: 'reports',
        title: 'Analytics & Reports',
        category: 'System',
        content: `
            <p class="mb-2">Generate deep insights into your business performance.</p>
            <ul class="list-disc pl-4 space-y-1">
                <li><strong>Lead Sources:</strong> See which marketing channels (Facebook, Google, Referrals) are generating the most leads.</li>
                <li><strong>Team Performance:</strong> Track which Lead Owners have the highest conversion rates.</li>
                <li><strong>Financials:</strong> Export your Sales and Expenses data for accounting purposes.</li>
            </ul>
        `
    },
    {
        id: 'settings',
        title: 'System Settings & Webhooks',
        category: 'System',
        content: `
            <p class="mb-2">Global configuration options for System Administrators.</p>
            <ul class="list-disc pl-4 space-y-1">
                <li><strong>Meta Webhooks:</strong> Configure your Facebook App ID, Secret, and Page Access Token to automatically receive leads from Facebook Lead Ads.</li>
                <li><strong>SMTP Email:</strong> Set up your email gateway to enable Two-Factor Authentication (OTP) and system notifications.</li>
                <li><strong>SLA Timers:</strong> Configure how many minutes a Lead Owner has to contact a new lead before the system sends a warning or escalates the lead to management.</li>
                <li><strong>Backblaze B2:</strong> Link your B2 cloud storage bucket to automatically upload and store call recordings via S3 API.</li>
            </ul>
        `
    }
];

function loadArticles() {
    const container = document.getElementById('articles-container');
    if (!container) return;

    if (ARTICLES.length === 0) {
        container.innerHTML = '<div class="text-sm text-slate-400">No articles published yet.</div>';
        return;
    }

    container.innerHTML = ARTICLES.map(article => `
        <details id="manual-${article.id}" class="bg-white/5 border border-white/10 rounded-xl p-4 cursor-pointer group transition-colors hover:bg-white/10">
            <summary class="text-sm font-semibold text-white outline-none flex items-center justify-between">
            <span>${article.title}</span>
            <span class="text-xs text-indigo-400 font-normal">${article.category}</span>
            </summary>
            <div class="mt-3 text-xs text-slate-400 leading-relaxed border-t border-white/10 pt-3">
            ${article.content}
            </div>
        </details>
    `).join('');
}

function handleDirectLink() {
    // If there is a ?topic=... query param, automatically open that accordion item
    const urlParams = new URLSearchParams(window.location.search);
    const topic = urlParams.get('topic');
    if (topic) {
        // Normalize the topic name from the sidebar labels
        let normalizedTopic = topic.replace(/^my-/, '');
        if (normalizedTopic === 'activities') normalizedTopic = 'activity-log';
        if (normalizedTopic === 'help-support') return; // Skip since they are already on the help page

        const detailEl = document.getElementById(`manual-${normalizedTopic}`);
        if (detailEl) {
            detailEl.open = true;
            setTimeout(() => {
                detailEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                detailEl.classList.add('ring-2', 'ring-indigo-500');
                setTimeout(() => detailEl.classList.remove('ring-2', 'ring-indigo-500'), 3000);
            }, 500);
        }
    }
}
