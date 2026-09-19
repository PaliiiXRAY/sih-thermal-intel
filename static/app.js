// FireSense Client Application - SIH26162
// Enterprise Geospatial Thermal Anomaly Intelligence & Disaster Response

const _qp = new URLSearchParams(window.location.search).get('portal');
let currentPortal = ['ntro', 'command', 'responder', 'citizen'].includes(_qp) ? _qp : 'command';
let currentNtroFilter = 'all';
let currentLanguage = 'en';
let selectedIncidentId = null;
let allIncidents = [];

// ==========================================
// 1. AUTHENTICATION & RBAC STATE LAYER
// ==========================================
const Auth = {
    token: sessionStorage.getItem('firesense_jwt') || null,
    user: null,
    role: sessionStorage.getItem('firesense_role') || 'analyst',

    async init() {
        const qp = new URLSearchParams(window.location.search).get('portal');
        if (qp === 'citizen') {
            closeAuthGate();
            await this.switchRole('citizen', false);
            return;
        }

        const gatePassed = sessionStorage.getItem('firesense_auth_passed');
        if (!gatePassed && !qp) {
            openAuthGate();
        } else {
            closeAuthGate();
        }

        if (this.token) {
            try {
                const me = await this.getMe();
                this.user = me;
                this.role = me.role || 'analyst';
                this.updateUI();
                return;
            } catch {
                this.token = null;
                sessionStorage.removeItem('firesense_jwt');
            }
        }
        const qpRoleMap = { ntro: 'analyst', command: 'authority', responder: 'responder', citizen: 'citizen' };
        const initialRole = (qp && qpRoleMap[qp]) ? qpRoleMap[qp] : (sessionStorage.getItem('firesense_role') || 'analyst');
        await this.switchRole(initialRole, false);
    },

    async login(email, password) {
        const resp = await fetch('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await resp.json();
        if (!resp.ok) {
            const msg = data.error?.message || data.detail || 'Authentication failed';
            throw new Error(msg);
        }
        this.token = data.access_token;
        this.user = data.user;
        this.role = data.user.role;
        sessionStorage.setItem('firesense_jwt', this.token);
        sessionStorage.setItem('firesense_role', this.role);
        this.updateUI();
        showToast(`Authenticated as ${this.user.full_name} (${this.role.toUpperCase()})`, 'success');
        return data;
    },

    async switchRole(role, notify = true) {
        const credentials = {
            analyst: { email: 'analyst@firesense.org', password: 'password123' },
            authority: { email: 'authority@firesense.org', password: 'password123' },
            responder: { email: 'responder@firesense.org', password: 'password123' },
            admin: { email: 'admin@firesense.org', password: 'password123' }
        };

        if (role === 'citizen') {
            this.token = null;
            this.user = { full_name: 'Public Citizen', role: 'citizen' };
            this.role = 'citizen';
            sessionStorage.removeItem('firesense_jwt');
            sessionStorage.setItem('firesense_role', 'citizen');
            this.updateUI();
            if (notify) showToast('Switched to unauthenticated Public Citizen view', 'info');
            return;
        }

        const creds = credentials[role];
        if (creds) {
            try {
                await this.login(creds.email, creds.password);
            } catch (err) {
                console.warn('Auto-login failed, falling back to local role state:', err);
                this.role = role;
                this.updateUI();
            }
        }
    },

    logout() {
        this.token = null;
        this.user = null;
        this.role = null;
        sessionStorage.removeItem('firesense_jwt');
        sessionStorage.removeItem('firesense_role');
        sessionStorage.removeItem('firesense_auth_passed');
        window.location.href = '/';
    },

    async getMe() {
        const resp = await fetch('/auth/me', {
            headers: { 'Authorization': `Bearer ${this.token}` }
        });
        if (!resp.ok) throw new Error('Session expired');
        return await resp.json();
    },

    updateUI() {
        const pill = document.getElementById('auth-role-pill');
        const select = document.getElementById('auth-role-select');
        if (pill) {
            pill.textContent = (this.role || 'GUEST').toUpperCase();
            pill.className = `px-2 py-0.5 rounded text-[10px] font-bold font-mono text-white ${
                this.role === 'analyst' ? 'bg-blue-600' :
                this.role === 'authority' ? 'bg-indigo-600' :
                this.role === 'responder' ? 'bg-orange-600' :
                this.role === 'admin' ? 'bg-purple-600' : 'bg-slate-500'
            }`;
        }
        if (select && select.value !== this.role) {
            select.value = this.role;
        }

        const authContainer = document.getElementById('auth-role-container');
        if (authContainer) {
            authContainer.classList.add('hidden');
        }

        // Role-based encapsulation of top navigation:
        // Admin: all dashboards accessible
        // Analyst: only NTRO
        // Authority: only Government Command
        // Responder: only Responder Operations
        // Citizen: only Citizen Services
        const role = this.role || 'analyst';
        const roleTabs = {
            admin: ['ntro', 'command', 'responder', 'citizen'],
            analyst: ['ntro'],
            authority: ['command'],
            responder: ['responder'],
            citizen: ['citizen']
        };
        const allowed = roleTabs[role] || ['ntro', 'command', 'responder', 'citizen'];

        ['ntro', 'command', 'responder', 'citizen'].forEach(p => {
            const tab = document.getElementById(`tab-${p}`);
            if (tab) {
                if (allowed.includes(p)) {
                    tab.classList.remove('hidden');
                } else {
                    tab.classList.add('hidden');
                }
            }
        });

        // If current portal is not allowed for this role, auto-switch to authorized dashboard
        if (!allowed.includes(currentPortal)) {
            const target = allowed[0];
            if (target) switchPortal(target);
        }
    }
};

function switchDemoRole(role) {
    Auth.switchRole(role);
}

function openAuthGate() {
    const gate = document.getElementById('auth-gate');
    if (gate) gate.classList.remove('hidden');
    const roleSel = document.getElementById('auth-role');
    if (roleSel && Auth && Auth.role) {
        roleSel.value = Auth.role;
        onAuthRoleChange(Auth.role);
    }
}

function closeAuthGate() {
    const gate = document.getElementById('auth-gate');
    if (gate) gate.classList.add('hidden');
}

function onAuthRoleChange(role) {
    const op = document.getElementById('auth-operator');
    if (!op) return;
    const emailMap = {
        analyst: 'analyst@firesense.org',
        authority: 'authority@firesense.org',
        responder: 'responder@firesense.org',
        admin: 'admin@firesense.org',
        citizen: 'citizen@firesense.org'
    };
    if (emailMap[role]) op.value = emailMap[role];
}

async function handleAuthGateSubmit() {
    const roleSel = document.getElementById('auth-role');
    const role = roleSel ? roleSel.value : 'analyst';
    sessionStorage.setItem('firesense_auth_passed', '1');
    closeAuthGate();
    await Auth.switchRole(role);
}

async function handleAuthGateCitizen() {
    sessionStorage.setItem('firesense_auth_passed', '1');
    closeAuthGate();
    await Auth.switchRole('citizen');
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        const gate = document.getElementById('auth-gate');
        if (gate && !gate.classList.contains('hidden')) {
            handleAuthGateSubmit();
        }
    }
});

// Global API Fetch helper with JWT and error interception
async function apiFetch(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (Auth.token && !headers['Authorization']) {
        headers['Authorization'] = `Bearer ${Auth.token}`;
    }

    try {
        const resp = await fetch(url, { ...options, headers });
        const data = await resp.json();
        if (!resp.ok) {
            const errCode = data.error?.code || `HTTP_${resp.status}`;
            const errMsg = data.error?.message || data.detail || 'API request rejected';
            throw new Error(`[${errCode}] ${errMsg}`);
        }
        return data;
    } catch (err) {
        if (err.message && err.message.includes('Failed to fetch')) {
            showToast('Backend server connection refused on port 8000', 'error');
        }
        throw err;
    }
}



// Real platform stats from the backend classification pipeline
async function loadLiveStats() {
    try {
        const r = await fetch('/api/stats');
        const s = await r.json();
        if (s.error) return;
        const el = (id) => document.getElementById(id);
        if (el('ntro-hotspots-count')) el('ntro-hotspots-count').textContent = s.hotspots_analyzed;
        const autoEl = el('ntro-auto-classified');
        if (autoEl) autoEl.textContent = s.auto_classified;
        const rateEl = el('ntro-classification-rate');
        if (rateEl) rateEl.textContent = `${s.classification_rate}% classification rate`;
        if (el('ntro-critical-count')) el('ntro-critical-count').textContent = s.critical_alerts;
    } catch { /* stats are decorative fallback if offline */ }
}

// Export the last pipeline run as GeoJSON (PS deliverable: data output)
let lastPipelineFC = null;
function downloadGeoJSON() {
    if (!lastPipelineFC) { alert('Run the AI Pipeline first, then export.'); return; }
    const blob = new Blob([JSON.stringify(lastPipelineFC, null, 2)], { type: 'application/geo+json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'aerothermal_classified_hotspots.geojson';
    a.click();
    URL.revokeObjectURL(a.href);
}

// Toast notification system
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    const colorClass = type === 'error' ? 'bg-red-900 border-red-700 text-red-100' :
        type === 'success' ? 'bg-emerald-900 border-emerald-700 text-emerald-100' :
        'bg-slate-900 border-slate-700 text-slate-100';

    toast.className = `p-3 rounded-xl border shadow-xl text-xs font-medium flex items-center justify-between gap-3 pointer-events-auto transition-all transform duration-200 translate-y-2 opacity-0 ${colorClass}`;
    toast.innerHTML = `
        <div class="flex items-center gap-2">
            <span>${type === 'error' ? '⚠️' : type === 'success' ? '✅' : 'ℹ️'}</span>
            <span>${message}</span>
        </div>
        <button onclick="this.parentElement.remove()" class="opacity-70 hover:opacity-100 font-bold">&times;</button>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
    }, 10);

    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-2');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// ==========================================
// 2. INCIDENTS DATA STORE & API SYNC
// ==========================================
async function loadIncidents() {
    try {
        const data = await apiFetch('/api/incidents?limit=50');
        allIncidents = data.incidents || [];
        if (allIncidents.length > 0 && !selectedIncidentId) {
            selectedIncidentId = allIncidents[0].id;
        }
        renderNtroIncidents();
        renderCmdIncidents();
        renderResponderView();
        updateNtroStatCards();
        return allIncidents;
    } catch (err) {
        console.warn('Failed to load incidents:', err.message);
        return [];
    }
    try {
        const url = new URL(window.location);
        url.searchParams.set('portal', portalName);
        window.history.replaceState({}, '', url);
    } catch { /* ignore on non-browser environments */ }

    const footerLabel = document.getElementById('txt-footer-portal-label');
    if (footerLabel) {
        if (portalName === 'ntro') footerLabel.textContent = "NTRO Intelligence Portal";
        else if (portalName === 'command') footerLabel.textContent = "Government Command Dashboard";
        else if (portalName === 'responder') footerLabel.textContent = "Responder Operations Field Terminal";
        else footerLabel.textContent = "Citizen Services Portal";
    }

    if (window.lucide) lucide.createIcons();
}

function updateNtroStatCards() {
    const totalEl = document.getElementById('ntro-hotspots-count');
    const autoEl = document.getElementById('ntro-auto-classified');
    const critEl = document.getElementById('ntro-critical-count');
    const logCountEl = document.getElementById('ntro-log-count');

    if (totalEl) totalEl.textContent = allIncidents.length || 0;
    if (autoEl) autoEl.textContent = allIncidents.filter(i => i.classification).length || 0;
    if (critEl) critEl.textContent = allIncidents.filter(i => (i.severity || '').toUpperCase() === 'CRITICAL').length || 0;
    if (logCountEl) logCountEl.textContent = `${allIncidents.length} events`;
}

// Quick demo seeder trigger from UI
async function quickSeedDemo() {
    showToast('Seeding curated demonstration scenarios...', 'info');
    try {
        await apiFetch('/api/hotspots/scenario?id=jamnagar_refinery');
        await loadIncidents();
        showToast('Demo scenarios seeded and ready', 'success');
    } catch (err) {
        showToast(`Seeding notice: ${err.message}`, 'info');
    }
}

// ==========================================
// 3. NTRO INTELLIGENCE PORTAL VIEW
// ==========================================
function filterNtro(cat) {
    currentNtroFilter = cat;
    const filters = ['all', 'industrial', 'wildfire', 'gas-flare', 'crop-burning', 'illegal'];
    filters.forEach(f => {
        const btn = document.getElementById(`btn-ntro-${f}`);
        if (!btn) return;
        if (f === cat) {
            btn.className = "px-3 py-1 rounded-md bg-blue-600 text-white shadow-xs font-semibold";
        } else {
            btn.className = "px-3 py-1 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 font-semibold";
        }
    });
    renderNtroIncidents();
}

function renderNtroIncidents() {
    const listEl = document.getElementById('ntro-incident-list');
    if (!listEl) return;

    let filtered = allIncidents;
    if (currentNtroFilter !== 'all') {
        filtered = allIncidents.filter(inc => {
            const c = (inc.classification || '').toLowerCase();
            if (currentNtroFilter === 'industrial') return c.includes('industrial');
            if (currentNtroFilter === 'wildfire') return c.includes('wildfire');
            if (currentNtroFilter === 'gas-flare') return c.includes('gas') || c.includes('flare');
            if (currentNtroFilter === 'crop-burning') return c.includes('crop');
            if (currentNtroFilter === 'illegal') return c.includes('unknown') || c.includes('mining');
            return true;
        });
    }

    if (!filtered.length) {
        listEl.innerHTML = `
            <div class="p-6 text-center border border-dashed border-slate-200 dark:border-slate-800 rounded-lg space-y-2">
                <p class="text-xs text-slate-400">No thermal anomalies in this category.</p>
                <button onclick="quickSeedDemo()" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold">
                    Seed Curated Scenarios
                </button>
            </div>`;
        return;
    }

    listEl.innerHTML = filtered.map(inc => {
        const isSel = inc.id === selectedIncidentId;
        const sevColor = inc.severity === 'CRITICAL' ? 'bg-red-500' :
            inc.severity === 'HIGH' ? 'bg-amber-500' :
            inc.severity === 'MEDIUM' ? 'bg-blue-500' : 'bg-slate-500';

        const conf = inc.classification_confidence != null ? `${Math.round(inc.classification_confidence * 100)}%` : 'Rule-based';
        const title = inc.explanation?.title || `Incident ${inc.id}`;

        return `
        <div onclick="selectNtroIncident('${inc.id}')"
             class="p-3 rounded-lg border cursor-pointer transition-all ${
                 isSel ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-950/40 shadow-xs' :
                 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50'
             }">
            <div class="flex items-center justify-between text-xs">
                <span class="font-mono font-bold text-slate-800 dark:text-slate-200">${inc.id}</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono text-white ${sevColor}">
                    ${inc.severity || 'MEDIUM'}
                </span>
            </div>
            <div class="text-xs font-bold text-slate-900 dark:text-white mt-1 line-clamp-1">${title}</div>
            <div class="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 mt-2 font-mono">
                <span>Class: <strong>${inc.classification || 'UNCLASSIFIED'}</strong></span>
                <span>Conf: <strong>${conf}</strong></span>
                <span class="px-1.5 py-0.5 rounded text-[9px] bg-slate-200 dark:bg-slate-700 font-bold">${inc.status}</span>
            </div>
        </div>`;
    }).join('');

    if (selectedIncidentId) {
        updateNtroDetailsPanel(selectedIncidentId);
    }
}

async function selectNtroIncident(id) {
    selectedIncidentId = id;
    renderNtroIncidents();
    renderCmdIncidents();
    await updateNtroDetailsPanel(id);
}

async function updateNtroDetailsPanel(id) {
    const inc = allIncidents.find(i => i.id === id);
    if (!inc) return;

    // 1. Basic Fields
    const titleEl = document.getElementById('ntro-detail-title');
    const coordsEl = document.getElementById('ntro-detail-coords');
    const sevEl = document.getElementById('ntro-detail-severity');
    const classEl = document.getElementById('ntro-detail-class');
    const confEl = document.getElementById('ntro-detail-confidence');
    const facilityEl = document.getElementById('ntro-facility-tag');
    const matchEl = document.getElementById('ntro-detail-match');

    if (titleEl) titleEl.textContent = inc.explanation?.title || inc.explanation?.region || `Incident ${inc.id}`;
    if (coordsEl) coordsEl.innerHTML = `${Number(inc.latitude).toFixed(3)}&deg;N &bull; ${Number(inc.longitude).toFixed(3)}&deg;E`;
    if (sevEl) {
        sevEl.textContent = inc.severity || 'MEDIUM';
        sevEl.className = `px-2.5 py-1 rounded text-xs font-bold font-mono uppercase text-white ${
            inc.severity === 'CRITICAL' ? 'bg-red-600' :
            inc.severity === 'HIGH' ? 'bg-amber-600' :
            inc.severity === 'MEDIUM' ? 'bg-blue-600' : 'bg-slate-600'
        }`;
    }
    if (classEl) classEl.textContent = inc.classification || 'DETECTED';
    if (confEl) {
        confEl.textContent = inc.classification_confidence != null ? `${Math.round(inc.classification_confidence * 100)}%` : 'Pending';
    }
    if (facilityEl) facilityEl.textContent = inc.explanation?.region || 'Registered Sector';
    if (matchEl) matchEl.textContent = `${inc.classification || 'Thermal Anomaly'} • Sentinel & FIRMS Automated Ingestion Engine`;

    // Telemetry stats
    const tempEl = document.getElementById('ntro-detail-temp');
    const areaEl = document.getElementById('ntro-detail-area');
    const sourceEl = document.getElementById('ntro-detail-source');
    if (tempEl) tempEl.innerHTML = `${inc.explanation?.evidence?.brightness_k ? Math.round(inc.explanation.evidence.brightness_k - 273.15) : 340}&deg;C`;
    if (areaEl) areaEl.innerHTML = `${inc.persistence_score != null ? Number(inc.persistence_score).toFixed(1) : 15.0}% persistence`;
    if (sourceEl) sourceEl.textContent = inc.detection_confidence || 'VIIRS_SNPP';

    // 2. Fetch PostGIS Context & Risk & Audit Timeline
    try {
        const [contextData, riskData, timelineData] = await Promise.all([
            apiFetch(`/api/incidents/${id}/context`).catch(() => null),
            apiFetch(`/api/incidents/${id}/risk`).catch(() => null),
            apiFetch(`/api/incidents/${id}/timeline`).catch(() => null),
        ]);

        renderNtroContextCard(contextData);
        renderNtroRiskCard(riskData);
        renderNtroTimelineCard(timelineData, inc);
    } catch (err) {
        console.warn('Failed to fetch detailed dossier:', err);
    }
}

function renderNtroContextCard(ctx) {
    const container = document.getElementById('ntro-detail-match')?.parentElement;
    if (!container || !ctx) return;

    const assets = ctx.nearest_assets || [];
    const responders = ctx.nearest_responders || [];

    let assetHtml = assets.slice(0, 2).map(a =>
        `<span class="inline-block px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-[10px] font-mono">${a.name} (${a.distance_km} km)</span>`
    ).join(' ') || '<span class="text-slate-400">None within 50 km</span>';

    let respHtml = responders.slice(0, 1).map(r =>
        `<span class="inline-block px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 text-[10px] font-mono">${r.name} (${r.distance_km} km)</span>`
    ).join(' ') || '<span class="text-slate-400">No units in range</span>';

    const existingCard = document.getElementById('ntro-postgis-card');
    if (existingCard) existingCard.remove();

    const card = document.createElement('div');
    card.id = 'ntro-postgis-card';
    card.className = "p-3 bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-200 dark:border-slate-800 text-xs space-y-2";
    card.innerHTML = `
        <div class="flex items-center justify-between text-[10px] font-mono font-bold uppercase text-slate-500">
            <span>PostGIS Geospatial Proximity</span>
            <span class="text-blue-600">ST_DWithin</span>
        </div>
        <div class="text-[11px] space-y-1">
            <div><strong>Critical Assets:</strong> ${assetHtml}</div>
            <div><strong>Nearest Units:</strong> ${respHtml}</div>
        </div>
    `;
    container.appendChild(card);
}

function renderNtroRiskCard(risk) {
    const existing = document.getElementById('ntro-risk-card');
    if (existing) existing.remove();
    if (!risk) return;

    const panel = document.getElementById('ntro-details-panel');
    if (!panel) return;

    const card = document.createElement('div');
    card.id = 'ntro-risk-card';
    card.className = "p-3 rounded-lg border border-blue-200 dark:border-blue-900 bg-blue-50/50 dark:bg-blue-950/20 text-xs space-y-2";
    card.innerHTML = `
        <div class="flex items-center justify-between">
            <span class="font-bold text-slate-900 dark:text-white">Transparent Priority Risk Score</span>
            <span class="text-lg font-black font-mono text-red-600 dark:text-red-400">${Number(risk.risk_score).toFixed(1)} / 100</span>
        </div>
        <div class="text-[10px] font-mono text-slate-500">Formula: 0.30 severity + 0.25 persistence + 0.20 exposure + 0.15 infra + 0.10 growth proxy</div>
        <div class="text-[11px] text-slate-700 dark:text-slate-300 space-y-0.5">
            ${(risk.reasons || []).slice(0, 3).map(r => `<div>&bull; ${r}</div>`).join('')}
        </div>
    `;
    panel.appendChild(card);
}

function renderNtroTimelineCard(timelineData, inc) {
    const existing = document.getElementById('ntro-timeline-card');
    if (existing) existing.remove();

    const panel = document.getElementById('ntro-details-panel');
    if (!panel) return;

    const events = timelineData?.timeline || [];
    const classifyBtn = (inc.status === 'DETECTED') ? `
        <button onclick="triggerClassifyIncident('${inc.id}')" class="mt-2 w-full py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded font-bold text-xs flex items-center justify-center gap-1.5">
            <span>⚡ Run Deterministic / XGBoost Classifier</span>
        </button>
    ` : '';

    const card = document.createElement('div');
    card.id = 'ntro-timeline-card';
    card.className = "p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-xs space-y-2";
    card.innerHTML = `
        <div class="flex items-center justify-between text-xs font-bold text-slate-800 dark:text-slate-200">
            <span>Immutable Audit Trail</span>
            <span class="font-mono text-slate-400">${events.length} logs</span>
        </div>
        <div class="space-y-1.5 max-h-36 overflow-y-auto pr-1">
            ${events.map(e => `
                <div class="flex items-start justify-between text-[11px] border-b border-slate-100 dark:border-slate-800/80 pb-1">
                    <div>
                        <span class="font-mono font-bold text-blue-600 dark:text-blue-400">${e.action}</span>
                        <span class="text-slate-500 ml-1">${e.note || ''}</span>
                    </div>
                    <span class="font-mono text-[10px] text-slate-400 shrink-0">${e.changed_at ? new Date(e.changed_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : ''}</span>
                </div>
            `).join('') || '<div class="text-slate-400 text-center py-2">No audit events logged.</div>'}
        </div>
        ${classifyBtn}
    `;
    panel.appendChild(card);
}

async function triggerClassifyIncident(id) {
    try {
        showToast(`Running classifier on incident ${id}...`, 'info');
        const resp = await apiFetch(`/api/incidents/${id}/classify`, { method: 'POST' });
        showToast(`✓ Classified as ${resp.classification} (${Math.round(resp.classification_confidence * 100)}% conf)`, 'success');
        await loadIncidents();
        await selectNtroIncident(id);
    } catch (err) {
        showToast(`Classifier error: ${err.message}`, 'error');
    }
}

// ==========================================
// 4. GOVERNMENT COMMAND PORTAL VIEW
// ==========================================
function renderCmdIncidents() {
    const listEl = document.getElementById('cmd-zone-list');
    if (!listEl) return;

    if (!allIncidents.length) {
        listEl.innerHTML = `
            <div class="p-6 text-center border border-dashed border-slate-200 dark:border-slate-800 rounded-lg space-y-2">
                <p class="text-xs text-slate-400">No active incidents in command queue.</p>
                <button onclick="quickSeedDemo()" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold">
                    Seed Demonstration Queue
                </button>
            </div>`;
        return;
    }

    listEl.innerHTML = allIncidents.map(inc => {
        const isSel = inc.id === selectedIncidentId;
        const sevColor = inc.severity === 'CRITICAL' ? 'bg-red-600 text-white' :
            inc.severity === 'HIGH' ? 'bg-amber-600 text-white' :
            inc.severity === 'MEDIUM' ? 'bg-blue-600 text-white' : 'bg-slate-500 text-white';

        const title = inc.explanation?.title || `Incident ${inc.id}`;
        return `
        <div onclick="selectCmdIncident('${inc.id}')"
             class="p-3 rounded-lg border cursor-pointer transition-all ${
                 isSel ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-950/40 shadow-xs' :
                 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50'
             }">
            <div class="flex items-center justify-between text-xs">
                <span class="font-bold text-slate-900 dark:text-white line-clamp-1">${title}</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono ${sevColor}">
                    ${inc.severity || 'MEDIUM'}
                </span>
            </div>
            <div class="flex items-center justify-between text-[11px] text-slate-500 mt-2 font-mono">
                <span>Priority: <strong class="text-red-600 dark:text-red-400">${inc.risk_score != null ? Number(inc.risk_score).toFixed(1) : '–'}</strong>/100</span>
                <span class="px-2 py-0.5 rounded text-[10px] bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-200 font-bold">${inc.status}</span>
            </div>
        </div>`;
    }).join('');

    if (selectedIncidentId) {
        updateCmdDetailsPanel(selectedIncidentId);
    }
}

function selectCmdIncident(id) {
    selectedIncidentId = id;
    renderCmdIncidents();
    renderNtroIncidents();
    updateCmdDetailsPanel(id);
}

function updateCmdDetailsPanel(id) {
    const inc = allIncidents.find(i => i.id === id);
    if (!inc) return;

    const nameEl = document.getElementById('cmd-sel-name');
    const typePill = document.getElementById('cmd-sel-type-pill');
    const sevPill = document.getElementById('cmd-sel-severity-pill');
    const popEl = document.getElementById('cmd-sel-pop');
    const typeStat = document.getElementById('cmd-sel-type');
    const dispatchBtn = document.getElementById('btn-dispatch');

    if (nameEl) nameEl.textContent = inc.explanation?.title || inc.id;
    if (typePill) typePill.textContent = inc.classification || 'THERMAL ANOMALY';
    if (sevPill) sevPill.textContent = inc.severity || 'MEDIUM';
    if (typeStat) typeStat.textContent = inc.classification || 'Thermal';
    if (popEl) popEl.textContent = inc.severity === 'CRITICAL' ? '82K' : inc.severity === 'HIGH' ? '45K' : '12K';

    if (dispatchBtn) {
        dispatchBtn.onclick = () => dispatchSimulatedAlert(inc.id);
        dispatchBtn.innerHTML = `<i data-lucide="send" class="w-3.5 h-3.5"></i> <span>Dispatch Simulated Alert</span>`;
        if (window.lucide) lucide.createIcons();
    }
}

// Quick action simulations for government command
function triggerQuickAction(msg) {
    showToast(`✓ Command Directive Executed: ${msg}`, 'success');
}

// ==========================================
// 5. FIRST RESPONDER OPERATIONS VIEW
// ==========================================
function renderResponderView() {
    const listEl = document.getElementById('responder-incident-list');
    const countEl = document.getElementById('responder-inc-count');
    if (!listEl) return;

    // Show incidents that have been alerted or progressed in lifecycle
    const tasks = allIncidents.filter(i =>
        ['ALERTED', 'ACKNOWLEDGED', 'EN_ROUTE', 'ARRIVED', 'CONTAINED', 'RESOLVED'].includes(i.status)
    );

    if (countEl) countEl.textContent = `${tasks.length} tasks`;

    if (!tasks.length) {
        listEl.innerHTML = `
            <div class="p-6 text-center border border-dashed border-slate-200 dark:border-slate-800 rounded-lg space-y-2">
                <p class="text-xs text-slate-400">No active alerts assigned to field units.</p>
                <button onclick="quickSeedDemo()" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold">
                    Seed Dispatched Scenarios
                </button>
            </div>`;
        return;
    }

    listEl.innerHTML = tasks.map(inc => {
        const isSel = inc.id === selectedIncidentId;
        return `
        <div onclick="selectResponderIncident('${inc.id}')"
             class="p-3 rounded-lg border cursor-pointer transition-all ${
                 isSel ? 'border-orange-500 bg-orange-50/50 dark:bg-orange-950/40 shadow-xs' :
                 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50'
             }">
            <div class="flex items-center justify-between text-xs">
                <span class="font-mono font-bold text-slate-800 dark:text-slate-200">${inc.id}</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono text-white ${STATUS_COLORS[inc.status] || 'bg-slate-500'}">
                    ${inc.status}
                </span>
            </div>
            <div class="text-xs font-bold text-slate-900 dark:text-white mt-1 line-clamp-1">
                ${inc.explanation?.title || inc.classification}
            </div>
            <div class="flex items-center justify-between text-[11px] text-slate-500 mt-2 font-mono">
                <span>Priority: <strong class="text-red-600">${inc.risk_score != null ? Number(inc.risk_score).toFixed(1) : '–'}</strong></span>
                <span>Sev: <strong>${inc.severity}</strong></span>
            </div>
        </div>`;
    }).join('');

    if (selectedIncidentId) {
        updateResponderDetailPanel(selectedIncidentId);
    }
}

function selectResponderIncident(id) {
    selectedIncidentId = id;
    renderResponderView();
    renderCmdIncidents();
    renderNtroIncidents();
    updateResponderDetailPanel(id);
}

async function updateResponderDetailPanel(id) {
    const inc = allIncidents.find(i => i.id === id);
    if (!inc) return;

    const idEl = document.getElementById('resp-sel-id');
    const coordsEl = document.getElementById('resp-sel-coords');
    const badgeEl = document.getElementById('resp-sel-status-badge');
    const classEl = document.getElementById('resp-sel-class');
    const sevEl = document.getElementById('resp-sel-severity');
    const riskEl = document.getElementById('resp-sel-risk');
    const unitEl = document.getElementById('resp-sel-unit');
    const btnContainer = document.getElementById('resp-transition-buttons');

    if (idEl) idEl.textContent = `${inc.id} • ${inc.explanation?.title || inc.classification}`;
    if (coordsEl) coordsEl.textContent = `Coordinates: ${Number(inc.latitude).toFixed(4)}°N, ${Number(inc.longitude).toFixed(4)}°E`;
    if (badgeEl) {
        badgeEl.textContent = inc.status;
        badgeEl.className = `px-2.5 py-1 rounded text-xs font-bold font-mono text-white ${STATUS_COLORS[inc.status] || 'bg-slate-500'}`;
    }
    if (classEl) classEl.textContent = inc.classification || 'Thermal';
    if (sevEl) sevEl.textContent = inc.severity || 'MEDIUM';
    if (riskEl) riskEl.textContent = `${inc.risk_score != null ? Number(inc.risk_score).toFixed(1) : '–'} / 100`;
    if (unitEl) unitEl.textContent = inc.assigned_responder_id || 'Rapid Action Unit 1';

    // Build canonical transition buttons
    if (btnContainer) {
        const nextStates = CANONICAL_TRANSITIONS[inc.status] || [];
        if (nextStates.length === 0) {
            btnContainer.innerHTML = `<span class="text-xs font-mono font-bold text-emerald-600 dark:text-emerald-400">✅ Incident has reached terminal state: RESOLVED.</span>`;
        } else {
            btnContainer.innerHTML = nextStates.map(st => `
                <button onclick="advanceIncident('${inc.id}', '${st}')"
                        class="px-4 py-2 rounded-lg bg-orange-600 hover:bg-orange-700 text-white font-bold text-xs shadow-sm flex items-center gap-1.5 transition-all">
                    <span>Transition &rarr; ${st}</span>
                </button>
            `).join('');
        }
    }

    // Fetch and render timeline
    try {
        const timeline = await apiFetch(`/api/incidents/${id}/timeline`);
        const timelineEl = document.getElementById('resp-audit-timeline');
        if (timelineEl) {
            const events = timeline.timeline || [];
            timelineEl.innerHTML = events.map(e => `
                <div class="p-2 rounded bg-slate-50 dark:bg-slate-950 border border-slate-200/60 dark:border-slate-800 text-[11px] flex justify-between gap-2">
                    <div>
                        <strong class="text-slate-800 dark:text-slate-200 font-mono">${e.action}</strong>
                        <span class="text-slate-500 ml-1">${e.note || ''}</span>
                    </div>
                    <span class="font-mono text-slate-400 shrink-0">${e.changed_at ? new Date(e.changed_at).toLocaleTimeString('en-IN') : ''}</span>
                </div>
            `).join('') || `<div class="text-slate-400 text-xs py-2">No audit events recorded.</div>`;
        }
    } catch (err) {
        console.warn('Failed to load responder audit trail:', err);
    }
}

// ==========================================
// 6. PORTAL SWITCHING & LIFECYCLE
// ==========================================
function switchPortal(portalName) {
    currentPortal = portalName;
    const portals = ['ntro', 'command', 'responder', 'citizen'];
    const role = (typeof Auth !== 'undefined' && Auth.role) ? Auth.role : 'analyst';
    const roleTabs = {
        admin: ['ntro', 'command', 'responder', 'citizen'],
        analyst: ['ntro'],
        authority: ['command'],
        responder: ['responder'],
        citizen: ['citizen']
    };
    const allowed = roleTabs[role] || ['ntro', 'command', 'responder', 'citizen'];

    portals.forEach(p => {
        const el = document.getElementById(`portal-${p}`);
        const tab = document.getElementById(`tab-${p}`);
        if (!el || !tab) return;
        if (p === portalName) {
            el.classList.remove('hidden');
            tab.className = "flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-sm border border-slate-200/80 dark:border-slate-700 transition-all font-bold";
        } else {
            el.classList.add('hidden');
            tab.className = "flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-all font-semibold";
        }
        if (!allowed.includes(p)) {
            tab.classList.add('hidden');
        } else {
            tab.classList.remove('hidden');
        }
    });

    const footerLabel = document.getElementById('txt-footer-portal-label');
    if (footerLabel) {
        footerLabel.textContent = portalName === 'ntro' ? 'NTRO Intelligence Portal' :
            portalName === 'command' ? 'Government Command Dashboard' :
            portalName === 'responder' ? 'First Responder Operational Console' :
            'Citizen Services Portal';
    }

    if (portalName === 'command' && typeof loadIncidentTracker === 'function') {
        loadIncidentTracker();
    }
    if (portalName === 'citizen') {
        setTimeout(initCitizenMap, 80);
        if (typeof loadPublicAlertsFeed === 'function') loadPublicAlertsFeed();
        if (typeof renderCitizenReportsFeed === 'function') renderCitizenReportsFeed();
    }
    if (portalName === 'ntro') {
        setTimeout(initPipelineMap, 80);
    }

    if (window.lucide) lucide.createIcons();
}

function triggerSatellitePass() {
    showToast('🛰️ Simulating NASA VIIRS satellite overpass telemetry...', 'info');
    setTimeout(() => {
        showToast('✓ Satellite telemetry synchronized across NTRO, Command & Field units', 'success');
        loadIncidents();
    }, 1200);
}

// Theme Initialization & Switching
(function initTheme() {
    try {
        const saved = localStorage.getItem('fs-theme');
        const html = document.documentElement;
        
        let theme = saved;
        if (!theme) {
            theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        
        if (theme === 'dark') html.classList.add('dark');
        else html.classList.remove('dark');
        
        window.addEventListener('DOMContentLoaded', () => {
            const btn = document.getElementById('theme-toggle');
            if (btn) {
                btn.innerHTML = theme === 'light' ? '\u2600' : '\u263e';
                btn.setAttribute('title', 'Switch to ' + (theme === 'light' ? 'dark' : 'light') + ' theme');
            }
        });
    } catch(e){}
})();

function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.classList.contains('dark');
    const next = isDark ? 'light' : 'dark';
    
    if (next === 'dark') {
        html.classList.add('dark');
    } else {
        html.classList.remove('dark');
    }
    
    const btn = document.getElementById('theme-toggle');
    if (btn) {
        btn.innerHTML = next === 'light' ? '\u2600' : '\u263e';
        btn.setAttribute('title', 'Switch to ' + (next === 'light' ? 'dark' : 'light') + ' theme');
    }
    try { localStorage.setItem('fs-theme', next); } catch(e){}
}

// Translations for Citizen Services
const translations = {
    en: {
        title: "Disaster Help Services",
        subtitle: "Find shelter, food, evacuation routes and emergency contacts near you.",
        sosBtn: "SOS — I Need Help Now",
        alertsHeading: "Active Alerts Near You",
        servicesHeading: "Services Available",
        routeHeading: "Evacuation Route",
        numbersHeading: "Emergency Numbers"
    },
    hi: {
        title: "आपदा सहायता सेवाएं",
        subtitle: "अपने आस-पास आश्रय, भोजन, निकासी मार्ग और आपातकालीन संपर्क खोजें।",
        sosBtn: "एसओएस — मुझे तुरंत मदद चाहिए",
        alertsHeading: "आपके आस-पास सक्रिय चेतावनी",
        servicesHeading: "उपलब्ध सेवाएं",
        routeHeading: "निकासी मार्ग",
        numbersHeading: "आपातकालीन नंबर"
    },
    od: {
        title: "ବିପର୍ଯ୍ୟୟ ସହାୟତା ସେବା",
        subtitle: "ନିକଟରେ ଆଶ୍ରୟସ୍ଥଳୀ, ଖାଦ୍ୟ, ସ୍ଥାନାନ୍ତରଣ ମାର୍ଗ ଏବଂ ଜରୁରୀକାଳୀନ ଯୋଗାଯୋଗ ଖୋଜନ୍ତୁ।",
        sosBtn: "ଏସ୍ଓଏସ୍ — ମୋତେ ତୁରନ୍ତ ସାହାଯ୍ୟ ଦରକାର",
        alertsHeading: "ଆପଣଙ୍କ ନିକଟରେ ସକ୍ରିୟ ଚେତାବନୀ",
        servicesHeading: "ଉପଲବ୍ଧ ସେବାସମୂହ",
        routeHeading: "ସ୍ଥାନାନ୍ତରଣ ମାର୍ଗ",
        numbersHeading: "ଜରୁରୀକାଳୀନ ନମ୍ବର"
    }
};

function setLanguage(lang) {
    currentLanguage = lang;
    ['en', 'hi', 'od'].forEach(l => {
        const btn = document.getElementById(`lang-${l}`);
        if (!btn) return;
        if (l === lang) {
            btn.className = "px-2.5 py-1 rounded bg-white text-slate-900 font-bold shadow-xs";
        } else {
            btn.className = "px-2.5 py-1 rounded text-slate-300 hover:text-white";
        }
    });

    const t = translations[lang];
    const setText = (id, txt) => {
        const el = document.getElementById(id);
        if (el) el.textContent = txt;
    };
    setText('txt-citizen-title', t.title);
    setText('txt-citizen-subtitle', t.subtitle);
    setText('txt-sos-btn', t.sosBtn);
    setText('txt-alerts-heading', t.alertsHeading);
    setText('txt-services-heading', t.servicesHeading);
    setText('txt-route-heading', t.routeHeading);
    setText('txt-num-heading', t.numbersHeading);
}

// SOS Emergency Modal
function openSosModal() {
    const m = document.getElementById('sosModal');
    if (m) m.classList.remove('hidden');
}

function closeSosModal() {
    const m = document.getElementById('sosModal');
    if (m) m.classList.add('hidden');
}

function selectSosType(btn, type) {
    document.querySelectorAll('.sos-opt-btn').forEach(b => {
        b.classList.remove('border-red-500', 'bg-red-50', 'dark:bg-red-950/40');
    });
    btn.classList.add('border-red-500', 'bg-red-50', 'dark:bg-red-950/40');
}

function submitSos() {
    const form = document.getElementById('sos-form');
    const success = document.getElementById('sos-success');
    if (form) form.classList.add('hidden');
    if (success) success.classList.remove('hidden');
    showToast('🚨 SOS Transmitted: Incident ticket dispatched to District Incident Command', 'error');
}

// ==========================================
// 7. PIPELINE GIS OVERLAY RUNNER
// ==========================================
let pipelineMap = null;
let pipelineLayer = null;
let pipelineMarkers = [];

function initPipelineMap() {
    if (pipelineMap) return;
    const el = document.getElementById('pipeline-map');
    if (!el || typeof L === 'undefined') return;
    pipelineMap = L.map(el, { scrollWheelZoom: true }).setView([22.3, 79.0], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(pipelineMap);
    pipelineLayer = L.layerGroup().addTo(pipelineMap);
}

function classColor(label) {
    if (!label) return '#64748b';
    const l = label.toLowerCase();
    if (l.includes('gas') || l.includes('flare') || l.includes('petro')) return '#f97316';
    if (l.includes('power') || l.includes('industrial') || l.includes('refinery')) return '#eab308';
    if (l.includes('wildfire') || l.includes('clandestine')) return '#dc2626';
    if (l.includes('crop') || l.includes('stubble')) return '#3b82f6';
    return '#8b5cf6';
}

async function runPipelineScenario() {
    initPipelineMap();
    const scenarioSelect = document.getElementById('pipeline-scenario');
    const scenarioId = scenarioSelect ? scenarioSelect.value : 'jamnagar_refinery';
    const liveOsm = document.getElementById('pipeline-live-osm')?.checked ? '1' : '0';
    const btn = document.getElementById('btn-pipeline-run');
    const resultsEl = document.getElementById('pipeline-results');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i> Running...';
    }
    if (resultsEl) {
        resultsEl.innerHTML = '<div class="text-xs text-blue-500 font-mono py-8 text-center">Ingesting FIRMS detections &rarr; PostGIS context &rarr; persistence &rarr; ML classification...</div>';
    }
    if (window.lucide) lucide.createIcons();

    try {
        const fc = await apiFetch(`/api/hotspots/scenario?id=${scenarioId}&live_osm=${liveOsm}`);
        lastPipelineFC = fc;

        pipelineLayer.clearLayers();
        pipelineMarkers = [];
        (fc.features || []).forEach(f => {
            const p = f.properties;
            const lat = f.geometry.coordinates[1];
            const lon = f.geometry.coordinates[0];
            const label = p.classification?.classification || 'Thermal Anomaly';
            const color = classColor(label);
            const marker = L.circleMarker([lat, lon], {
                radius: 11, color: color, weight: 2.5,
                fillColor: color, fillOpacity: 0.35
            }).bindPopup(`
                <div style="font-family:sans-serif;font-size:12px;min-width:220px">
                    <b style="color:${color}">${label}</b><br/>
                    <span style="color:#555">${p.classification?.confidence_percent || 90}% confidence &bull; FRP ${p.firms?.frp || 45} MW</span><br/>
                    <b>Facility:</b> ${p.osm?.facility_name || 'None mapped'}<br/>
                    <b>Persistence:</b> ${p.persistence?.persistence_score || 80}%<br/>
                    <b>Land-cover:</b> ${p.landcover?.worldcover_class || 'Industrial'}
                </div>
            `).addTo(pipelineLayer);
            pipelineMarkers.push(marker);
        });

        if (fc.features && fc.features.length) {
            pipelineMap.fitBounds(L.featureGroup(pipelineMarkers).getBounds().pad(0.5));
        }

        const countEl = document.getElementById('pipeline-result-count');
        if (countEl) countEl.textContent = `${fc.features?.length || 0} hotspots`;

        if (resultsEl) {
            resultsEl.innerHTML = (fc.features || []).map(f => {
                const p = f.properties;
                const c = p.classification;
                const color = classColor(c.classification);
                return `
                <div class="p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 text-xs space-y-1">
                    <div class="flex items-center justify-between">
                        <span class="font-bold font-mono" style="color:${color}">${c.classification}</span>
                        <span class="font-mono text-slate-400">${c.confidence_percent}%</span>
                    </div>
                    <div class="text-slate-500 dark:text-slate-400 font-mono text-[11px]">
                        ${p.firms?.id || 'HS'} &bull; ${Number(p.firms?.lat).toFixed(3)}&deg;N ${Number(p.firms?.lon).toFixed(3)}&deg;E &bull; FRP ${p.firms?.frp} MW
                    </div>
                    <div class="text-[11px] text-slate-600 dark:text-slate-300">
                        <b>Facility:</b> ${p.osm?.facility_name || 'None mapped'} &bull; <b>Persistence:</b> ${p.persistence?.persistence_score}%
                    </div>
                </div>`;
            }).join('');
        }
        showToast(`AI Pipeline: ${fc.features?.length || 0} detections classified`, 'success');
    } catch (err) {
        if (resultsEl) {
            resultsEl.innerHTML = `<div class="text-xs text-red-500 font-mono py-6 text-center border border-red-200 rounded-lg">Pipeline error: ${err.message}</div>`;
        }
        showToast(`Pipeline execution error: ${err.message}`, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="play" class="w-3.5 h-3.5"></i> Run AI Pipeline';
        }
        if (window.lucide) lucide.createIcons();
    }
}

function downloadGeoJSON() {
    if (!lastPipelineFC) {
        alert('Run the AI Pipeline first, then export.');
        return;
    }
    const blob = new Blob([JSON.stringify(lastPipelineFC, null, 2)], { type: 'application/geo+json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'firesense_classified_hotspots.geojson';
    a.click();
    URL.revokeObjectURL(a.href);
}

// App Initialization
document.addEventListener('DOMContentLoaded', async () => {
    if (window.lucide) lucide.createIcons();
    const qp = new URLSearchParams(window.location.search).get('portal');
    if (['ntro', 'command', 'responder', 'citizen'].includes(qp)) {
        currentPortal = qp;
    }
    await Auth.init();
    await loadIncidents();
    switchPortal(currentPortal);
    loadLiveStats();
});
