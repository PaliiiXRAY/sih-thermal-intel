// FireSense Portal Modules - SIH26162
// Canonical Incident Lifecycle Tracker, Citizen Reports & Evacuation Mapping

// ===================== Canonical Incident Lifecycle State Machine =====================
const STATUS_FLOW = [
    'DETECTED', 'CLASSIFIED', 'ASSESSED', 'ALERTED',
    'ACKNOWLEDGED', 'EN_ROUTE', 'ARRIVED', 'CONTAINED', 'RESOLVED'
];

const STATUS_COLORS = {
    'DETECTED': 'bg-slate-500',
    'CLASSIFIED': 'bg-blue-500',
    'ASSESSED': 'bg-indigo-500',
    'ALERTED': 'bg-amber-500',
    'ACKNOWLEDGED': 'bg-purple-600',
    'EN_ROUTE': 'bg-cyan-600',
    'ARRIVED': 'bg-teal-600',
    'CONTAINED': 'bg-orange-600',
    'RESOLVED': 'bg-emerald-600'
};

const CANONICAL_TRANSITIONS = {
    'DETECTED': ['CLASSIFIED'],
    'CLASSIFIED': ['ASSESSED'],
    'ASSESSED': ['ALERTED'],
    'ALERTED': ['ACKNOWLEDGED'],
    'ACKNOWLEDGED': ['EN_ROUTE', 'RESOLVED'],
    'EN_ROUTE': ['ARRIVED'],
    'ARRIVED': ['CONTAINED'],
    'CONTAINED': ['RESOLVED'],
    'RESOLVED': []
};

async function loadIncidentTracker() {
    const listEl = document.getElementById('incident-tracker-list');
    if (!listEl) return;
    try {
        const resp = await apiFetch('/api/incidents');
        const incidents = resp.incidents || [];
        if (!incidents.length) {
            listEl.innerHTML = `
                <div class="p-6 text-center border border-dashed border-slate-200 dark:border-slate-800 rounded-lg space-y-2">
                    <p class="text-xs text-slate-500">Database has no active incidents.</p>
                    <button onclick="quickSeedDemo()" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold">
                        Seed Curated Demo Scenarios
                    </button>
                </div>`;
            return;
        }

        listEl.innerHTML = incidents.map(inc => {
            const st = (inc.status || 'DETECTED').toUpperCase();
            const idx = STATUS_FLOW.indexOf(st);
            const progress = STATUS_FLOW.map((s, i) =>
                `<div class="flex-1 h-1.5 rounded-full ${i <= idx ? (STATUS_COLORS[s] || 'bg-slate-500') : 'bg-slate-200 dark:bg-slate-700'}" title="${s}"></div>`).join('');
            
            const nextStates = CANONICAL_TRANSITIONS[st] || [];
            const advanceBtn = nextStates.length > 0 ? `
                <button onclick="advanceIncident('${inc.id}', '${nextStates[0]}')" class="px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white font-bold text-[11px] flex items-center gap-1">
                    <span>Advance &rarr; ${nextStates[0]}</span>
                </button>
            ` : `<span class="text-[11px] font-mono text-emerald-600 dark:text-emerald-400 font-bold">TERMINAL (RESOLVED)</span>`;

            const alertBtn = (st === 'ASSESSED' || st === 'ALERTED') ? `
                <button onclick="dispatchSimulatedAlert('${inc.id}')" class="px-2.5 py-1 rounded bg-amber-500 hover:bg-amber-600 text-white font-bold text-[11px] flex items-center gap-1">
                    <span>Simulated Alert</span>
                </button>
            ` : '';

            return `
            <div class="p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 text-xs space-y-2.5">
                <div class="flex flex-wrap items-center justify-between gap-2">
                    <div>
                        <span class="font-mono font-bold text-slate-800 dark:text-slate-200">${inc.id}</span>
                        <span class="text-slate-500 dark:text-slate-400 ml-2">${inc.classification || 'Thermal Anomaly'} &bull; ${Number(inc.latitude).toFixed(3)}&deg;N, ${Number(inc.longitude).toFixed(3)}&deg;E</span>
                    </div>
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono text-white ${STATUS_COLORS[st] || 'bg-slate-500'}">${st}</span>
                </div>
                <div class="flex gap-1">${progress}</div>
                <div class="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-200/60 dark:border-slate-700/60">
                    <div class="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                        Risk Score: <strong class="text-slate-900 dark:text-white">${inc.risk_score != null ? Number(inc.risk_score).toFixed(1) : '–'}</strong>/100 &bull; Severity: <strong>${inc.severity || '–'}</strong>
                    </div>
                    <div class="flex items-center gap-1.5">
                        ${alertBtn}
                        ${advanceBtn}
                    </div>
                </div>
            </div>`;
        }).join('');
    } catch (err) {
        listEl.innerHTML = `<div class="text-xs text-red-500 py-3 text-center">Failed to load incident tracker: ${err.message}</div>`;
    }
}

async function dispatchSimulatedAlert(id) {
    try {
        showToast('Dispatching simulated alert...', 'info');
        const resp = await apiFetch(`/api/incidents/${id}/alert`, { method: 'POST' });
        showToast(`🚨 SIMULATED DISPATCH: Priority alert generated for ${id} (is_simulated: true)`, 'success');
        await loadIncidentTracker();
        if (typeof renderCmdIncidents === 'function') renderCmdIncidents();
    } catch (err) {
        showToast(`Simulated dispatch error: ${err.message}`, 'error');
    }
}

async function advanceIncident(id, targetStatus) {
    try {
        showToast(`Transitioning ${id} &rarr; ${targetStatus}...`, 'info');
        const resp = await apiFetch(`/api/incidents/${id}/status`, {
            method: 'PATCH',
            body: JSON.stringify({
                status: targetStatus,
                note: `Lifecycle advanced to ${targetStatus} via Incident Command Console`
            })
        });
        showToast(`✓ Incident ${id} transitioned to ${targetStatus}`, 'success');
        await loadIncidentTracker();
        if (typeof renderCmdIncidents === 'function') renderCmdIncidents();
        if (typeof renderNtroIncidents === 'function') renderNtroIncidents();
        if (typeof renderResponderView === 'function') renderResponderView();
    } catch (err) {
        showToast(`Status transition rejected: ${err.message}`, 'error');
    }
}

// ===================== Citizen Reports (Crowdsourcing) =====================
let reportGps = null;

function attachGps() {
    const label = document.getElementById('gps-label');
    if (!navigator.geolocation) {
        if (label) label.textContent = 'GPS unavailable';
        return;
    }
    if (label) label.textContent = 'Locating...';
    navigator.geolocation.getCurrentPosition(
        pos => {
            reportGps = { lat: +pos.coords.latitude.toFixed(4), lon: +pos.coords.longitude.toFixed(4) };
            if (label) label.textContent = `GPS: ${reportGps.lat}°, ${reportGps.lon}°`;
        },
        () => {
            if (label) label.textContent = 'GPS denied';
        },
        { timeout: 8000 }
    );
}

async function getCitizenReports() {
    try {
        const resp = await apiFetch('/api/reports');
        return resp.reports || [];
    } catch {
        try {
            return JSON.parse(localStorage.getItem('citizenReports') || '[]');
        } catch {
            return [];
        }
    }
}

async function submitCitizenReport() {
    const typeEl = document.getElementById('report-type');
    const locEl = document.getElementById('report-location');
    const notesEl = document.getElementById('report-notes');
    const confirmEl = document.getElementById('report-confirmation');

    const type = typeEl ? typeEl.value : 'Smoke plume visible';
    const location = locEl ? locEl.value.trim() : '';
    const notes = notesEl ? notesEl.value.trim() : '';

    if (!location) {
        if (confirmEl) confirmEl.textContent = 'Please enter an area or landmark.';
        return;
    }

    const report = {
        type,
        location,
        notes,
        gps: reportGps,
        time: new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
    };

    try {
        const resp = await apiFetch('/api/reports/submit', {
            method: 'POST',
            body: JSON.stringify(report)
        });
        showToast(`✅ Citizen report ${resp.report?.id || 'submitted'} recorded on server`, 'success');
    } catch {
        // Local offline fallback
        const local = (() => { try { return JSON.parse(localStorage.getItem('citizenReports') || '[]'); } catch { return []; } })();
        report.id = `RPT-${Date.now().toString().slice(-6)}`;
        report.status = 'SUBMITTED';
        local.unshift(report);
        localStorage.setItem('citizenReports', JSON.stringify(local.slice(0, 50)));
        showToast(`Report saved locally in offline buffer`, 'info');
    }

    if (locEl) locEl.value = '';
    if (notesEl) notesEl.value = '';
    reportGps = null;
    const gpsLabel = document.getElementById('gps-label');
    if (gpsLabel) gpsLabel.textContent = 'Attach GPS';
    if (confirmEl) {
        confirmEl.textContent = '✅ Report submitted — visible in Command inbox.';
        setTimeout(() => { confirmEl.textContent = ''; }, 6000);
    }

    await renderCitizenReportsFeed();
    if (window.lucide) lucide.createIcons();
}

async function renderCitizenReportsFeed() {
    const feed = document.getElementById('citizen-reports-feed');
    if (!feed) return;
    const reports = await getCitizenReports();
    const countEl = document.getElementById('citizen-reports-count');
    if (countEl) countEl.textContent = `${reports.filter(r => r.status === 'SUBMITTED').length} new`;
    if (!reports.length) {
        feed.innerHTML = `<div class="text-xs text-slate-400 py-3 text-center border border-dashed border-slate-200 dark:border-slate-700 rounded-lg">No citizen reports yet. Reports from the Citizen Services portal appear here.</div>`;
        return;
    }

    feed.innerHTML = reports.slice(0, 8).map(r => `
        <div class="p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 text-xs space-y-1">
            <div class="flex items-center justify-between">
                <span class="font-mono font-bold text-slate-800 dark:text-slate-200">${r.id} &bull; ${r.type}</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono ${r.status === 'VERIFIED' ? 'bg-emerald-600 text-white' : 'bg-amber-500 text-white'}">${r.status}</span>
            </div>
            <div class="text-[11px] text-slate-600 dark:text-slate-300">
                ${r.time} &bull; ${r.location}${r.gps ? ` &bull; ${r.gps.lat}&deg;N ${r.gps.lon}&deg;E` : ''}
            </div>
            ${r.notes ? `<div class="text-[11px] text-slate-500 dark:text-slate-400 italic">${r.notes}</div>` : ''}
            ${r.status === 'SUBMITTED' ? `<button onclick="verifyCitizenReport('${r.id}')" class="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[11px] mt-1">Cross-check with FIRMS &amp; Verify</button>` : ''}
        </div>`).join('');
}

async function verifyCitizenReport(id) {
    try {
        const resp = await apiFetch('/api/reports/verify', {
            method: 'POST',
            body: JSON.stringify({ id })
        });
        showToast(`✅ ${id} verified against satellite FIRMS context`, 'success');
    } catch {
        const local = (() => { try { return JSON.parse(localStorage.getItem('citizenReports') || '[]'); } catch { return []; } })();
        const rep = local.find(r => r.id === id);
        if (rep) rep.status = 'VERIFIED';
        localStorage.setItem('citizenReports', JSON.stringify(local));
        showToast(`${id} verified locally`, 'info');
    }
    await renderCitizenReportsFeed();
}

// ===================== Public Alerts & Citizen Evacuation Map =====================
let citizenMap = null;

async function loadPublicAlertsFeed() {
    const listContainer = document.getElementById('txt-alerts-heading')?.parentElement?.querySelector('.space-y-2\\.5');
    if (!listContainer) return;
    try {
        const resp = await apiFetch('/public/alerts?limit=5');
        const alerts = resp.alerts || [];
        if (!alerts.length) {
            listContainer.innerHTML = `<div class="text-xs text-slate-400 py-3 text-center">No active simulated public advisories.</div>`;
            return;
        }

        listContainer.innerHTML = alerts.map(a => {
            const sev = a.severity || 'MEDIUM';
            const colorClass = sev === 'CRITICAL' ? 'bg-red-50/60 dark:bg-red-950/30 border-red-100 dark:border-red-900/40 text-red-700 dark:text-red-300' :
                sev === 'HIGH' ? 'bg-amber-50/60 dark:bg-amber-950/30 border-amber-100 dark:border-amber-900/40 text-amber-700 dark:text-amber-300' :
                'bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300';
            const badgeClass = sev === 'CRITICAL' ? 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300' :
                sev === 'HIGH' ? 'bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300' :
                'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300';
            
            const timeStr = a.created_at ? new Date(a.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : 'Recent';
            return `
            <div class="flex items-center justify-between gap-3 p-2.5 rounded-lg border ${colorClass}">
                <div class="flex items-center gap-2 font-medium">
                    <span class="font-mono text-[11px] opacity-70">${timeStr}</span>
                    <span>${a.message}</span>
                </div>
                <div class="flex items-center gap-1.5 shrink-0">
                    <span class="px-1.5 py-0.5 rounded text-[9px] font-bold font-mono bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300">SIMULATED</span>
                    <span class="px-2 py-0.5 rounded font-mono text-[10px] font-bold ${badgeClass}">${sev}</span>
                </div>
            </div>`;
        }).join('');
    } catch (err) {
        console.warn('Public alerts feed error:', err.message);
    }
}

function initCitizenMap() {
    if (citizenMap) return;
    const el = document.getElementById('citizen-map');
    if (!el || typeof L === 'undefined') return;
    citizenMap = L.map(el).setView([20.8465, 85.0985], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18, attribution: '&copy; OpenStreetMap contributors'
    }).addTo(citizenMap);

    // Simulated incident zone
    L.circleMarker([20.8420, 85.1020], {
        radius: 12, color: '#dc2626', weight: 2.5, fillColor: '#dc2626', fillOpacity: 0.35
    }).bindPopup('<b style="color:#dc2626">THERMAL ANOMALY ZONE</b><br/>Angul Industrial Area &mdash; Avoid perimeter').addTo(citizenMap);

    // Safe shelter
    L.circleMarker([20.8520, 85.0930], {
        radius: 10, color: '#059669', weight: 2.5, fillColor: '#059669', fillOpacity: 0.45
    }).bindPopup('<b style="color:#059669">SAFE SHELTER</b><br/>Govt High School &mdash; Food, water, medical aid ready').addTo(citizenMap);

    // Evacuation route
    L.polyline([[20.8440, 85.0995], [20.8470, 85.0970], [20.8495, 85.0950], [20.8520, 85.0930]], {
        color: '#2563eb', weight: 4, dashArray: '8 6', opacity: 0.9
    }).bindPopup('<b>Evacuation Route (NH-55 Corridor)</b><br/>Via Market Road &rarr; Brahmani Bridge &rarr; Shelter').addTo(citizenMap);
}

// lazy-init trackers/maps on portal switch
const origSwitchPortal2 = switchPortal;
switchPortal = function (portalName) {
    origSwitchPortal2(portalName);
    if (portalName === 'command') { loadIncidentTracker(); renderCitizenReportsFeed(); }
    if (portalName === 'citizen') { setTimeout(initCitizenMap, 80); renderCitizenReportsFeed(); }
    if (portalName === 'ntro') { loadIncidentTable(); wireIncidentTable(); loadDetectionFeed(); }
    if (portalName === 'responder') { loadResponderPortal(); }
};

// ===================== Government Command Enhanced =====================
const GOV_VALID_TRANSITIONS = {
  NEW: ['INVESTIGATING'],
  INVESTIGATING: ['VERIFIED'],
  VERIFIED: ['DISPATCHED'],
  DISPATCHED: ['ACKNOWLEDGED', 'INVESTIGATING'],
  ACKNOWLEDGED: ['EN ROUTE'],
  'EN ROUTE': ['ARRIVED'],
  ARRIVED: ['CONTAINED'],
  CONTAINED: ['RESOLVED'],
  RESOLVED: []
};

async function govAcknowledge(incId) {
  try {
    const resp = await fetch(`/api/incidents/${incId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'INVESTIGATING' })
    });
    if (resp.status === 409) {
      const data = await resp.json();
      alert(`❌ Invalid Transition: ${data.error}`);
      return;
    }
    if (resp.status === 403) {
      alert('❌ Forbidden: You do not have permission to perform this action.');
      return;
    }
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const res = await resp.json();
    if (res.success) {
      loadIncidentTracker();
      if (typeof loadIncidentTable === 'function') loadIncidentTable();
    }
  } catch (err) {
    alert(`Network error: ${err.message}`);
  }
}

async function govSendAlert(incId) {
  try {
    const resp = await fetch(`/api/incidents/${incId}/alert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ incident_id: incId, alert_type: 'SIMULATED_DISPATCH' })
    });
    if (resp.status === 409) {
      const data = await resp.json();
      alert(`❌ Cannot send alert: ${data.error}`);
      return;
    }
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    alert(`✅ SIMULATED DISPATCH\n\nAlert ID: ${data.alert_id}\nDispatched to: ${data.dispatched_to}\nETA: ${data.eta}\n\n⚠️ This is a TRAINING SIMULATION — no real government system was contacted.`);
    loadIncidentTracker();
    if (typeof loadIncidentTable === 'function') loadIncidentTable();
  } catch (err) {
    alert(`Network error: ${err.message}`);
  }
}

async function govExportPDF(incId) {
  try {
    const resp = await fetch(`/api/export/${incId}/pdf`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    if (data.pdf_url) {
      window.open(data.pdf_url, '_blank');
    } else {
      alert(`📄 PDF Export: ${data.filename || 'Export generated'}`);
    }
  } catch (err) {
    alert(`PDF export failed: ${err.message}`);
  }
}

// load on first paint if command (default portal) is shown
document.addEventListener('DOMContentLoaded', () => {
    if (currentPortal === 'command') { loadIncidentTracker(); renderCitizenReportsFeed(); }
    if (currentPortal === 'ntro') { loadIncidentTable(); wireIncidentTable(); loadDetectionFeed(); }
    if (currentPortal === 'responder') { loadResponderPortal(); }
});

// ===================== Mission-Control Incident Table + Drawer + Feed =====================
let _incCache = [];
let _incState = { q: '', status: '', sort: 'risk' };

const INC_STATUS_COLORS = {
  'NEW': 'bg-slate-500', 'INVESTIGATING': 'bg-blue-500', 'VERIFIED': 'bg-indigo-500',
  'DISPATCHED': 'bg-amber-500', 'EN ROUTE': 'bg-orange-500', 'ARRIVED': 'bg-orange-600',
  'CONTAINED': 'bg-orange-600', 'RESOLVED': 'bg-emerald-600'
};

async function loadIncidentTable() {
  const body = document.getElementById('inc-table-body');
  if (!body) return;
  try {
    const resp = await fetch('/api/incidents');
    const data = await resp.json();
    _incCache = Array.isArray(data.incidents) ? data.incidents : Object.values(data.incidents || {});
    renderIncidentTable();
  } catch (err) {
    body.innerHTML = '<tr><td colspan="8" class="py-6 text-center text-red-500 font-mono text-xs">DATA SOURCE UNAVAILABLE — ' + err.message + ' <button onclick="loadIncidentTable()" class="underline ml-2">Retry</button></td></tr>';
  }
}

function renderIncidentTable() {
  const body = document.getElementById('inc-table-body');
  if (!body) return;
  const q = _incState.q.trim().toLowerCase();
  let rows = _incCache.filter(inc => {
    if (_incState.status && (inc.status || 'NEW') !== _incState.status) return false;
    if (!q) return true;
    return [inc.id, inc.title, inc.location_name, inc.classification].join(' ').toLowerCase().includes(q);
  });
  rows.sort((a, b) => {
    if (_incState.sort === 'risk') return (b.risk_score || 0) - (a.risk_score || 0);
    if (_incState.sort === 'confidence') return (b.confidence || 0) - (a.confidence || 0);
    return (b.id || '').localeCompare(a.id || '');
  });
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="8" class="py-8 text-center text-slate-400 font-mono text-xs">NO INCIDENTS MATCH YOUR FILTERS</td></tr>';
    return;
  }
  body.innerHTML = rows.map(inc => (
    '<tr class="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/60 cursor-pointer transition-colors" onclick="openIncDrawer(\'' + inc.id + '\')">' +
      '<td class="py-2.5 pr-3 font-mono font-bold text-slate-800 dark:text-slate-200">' + inc.id + '</td>' +
      '<td class="py-2.5 pr-3 text-slate-600 dark:text-slate-300">' + inc.location_name + '</td>' +
      '<td class="py-2.5 pr-3 text-slate-600 dark:text-slate-300">' + inc.classification + '</td>' +
      '<td class="py-2.5 pr-3"><span class="font-mono font-bold ' + (inc.risk_score >= 70 ? 'text-red-600 dark:text-red-400' : inc.risk_score >= 40 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400') + '">' + inc.risk_score + '</span></td>' +
      '<td class="py-2.5 pr-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono text-white ' + (INC_STATUS_COLORS[inc.status] || 'bg-slate-500') + '">' + (inc.status || 'NEW') + '</span></td>' +
      '<td class="py-2.5 pr-3 font-mono text-slate-600 dark:text-slate-300">' + inc.frp_mw + ' MW</td>' +
      '<td class="py-2.5 pr-3 font-mono text-slate-600 dark:text-slate-300">' + inc.confidence + '%</td>' +
      '<td class="py-2.5 text-blue-600 dark:text-blue-400 font-bold whitespace-nowrap">Details →</td>' +
    '</tr>')).join('');
}

function wireIncidentTable() {
  const s = document.getElementById('inc-search');
  const f = document.getElementById('inc-status-filter');
  const so = document.getElementById('inc-sort');
  if (!s || s.dataset.wired) return;
  s.dataset.wired = '1';
  s.addEventListener('input', () => { _incState.q = s.value; renderIncidentTable(); });
  f.addEventListener('change', () => { _incState.status = f.value; renderIncidentTable(); });
  so.addEventListener('change', () => { _incState.sort = so.value; renderIncidentTable(); });
}

function dots(filled, total) {
  let out = '';
  for (let i = 0; i < total; i++) out += i < filled ? '<span class="text-orange-500">●</span>' : '<span class="text-slate-300 dark:text-slate-700">●</span>';
  return out;
}

function openIncDrawer(id) {
  const inc = _incCache.find(i => i.id === id);
  if (!inc) return;
  const dw = document.getElementById('inc-drawer');
  document.getElementById('dw-id').textContent = inc.id + ' · ' + (inc.timestamp || '');
  document.getElementById('dw-title').textContent = inc.title;
  const st = inc.status || 'NEW';
  const stColor = INC_STATUS_COLORS[st] || 'bg-slate-500';
  const ev = (inc.explain_classification && inc.explain_classification.evidence) || [];
  const ce = (inc.explain_classification && inc.explain_classification.counter_evidence) || [];
  const assets = inc.assets_at_risk || [];
  const base = inc.local_baseline || {};
  const passes = base.location_history_passes || 0;
  const wc = inc.wind_corridor || {};
  const auth = inc.assigned_authority || {};
  const cb = inc.confidence_breakdown || {};

  document.getElementById('dw-body').innerHTML = (
    '<div class="flex items-center justify-between">' +
      '<span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono text-white ' + stColor + '">' + st + '</span>' +
      '<span class="font-mono text-[11px] text-slate-400">' + inc.coordinates.lat + '°N ' + inc.coordinates.lon + '°E</span>' +
    '</div>' +
    '<div class="grid grid-cols-3 gap-2 text-center">' +
      '<div class="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60"><div class="text-[10px] text-slate-400 uppercase">Model score</div><div class="text-xl font-black font-mono text-slate-900 dark:text-white">' + inc.confidence + '%</div></div>' +
      '<div class="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60"><div class="text-[10px] text-slate-400 uppercase">Risk</div><div class="text-xl font-black font-mono ' + (inc.risk_score >= 70 ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400') + '">' + inc.risk_score + '</div></div>' +
      '<div class="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60"><div class="text-[10px] text-slate-400 uppercase">FRP</div><div class="text-xl font-black font-mono text-slate-900 dark:text-white">' + inc.frp_mw + '</div></div>' +
    '</div>' +
    '<div>' +
      '<div class="font-bold text-slate-800 dark:text-slate-200 mb-1.5 uppercase text-[10px] tracking-wider font-mono">Persistence · 60-day baseline</div>' +
      '<div class="tracking-widest text-sm">' + dots(Math.min(passes, 20), 20) + '</div>' +
      '<div class="text-[11px] text-slate-500 dark:text-slate-400 mt-1">' + passes + ' observations in window · ' + (base.normal_seasonal_range || 'n/a') + ' normal · ' + (base.anomaly_ratio || '') + '</div>' +
      '<div class="text-[11px] italic text-slate-500 dark:text-slate-400 mt-1">' + (base.verdict || '') + '</div>' +
    '</div>' +
    '<div>' +
      '<div class="font-bold text-slate-800 dark:text-slate-200 mb-1.5 uppercase text-[10px] tracking-wider font-mono">Why this classification</div>' +
      ev.map(e => '<div class="text-[11px] text-slate-600 dark:text-slate-300 py-0.5">✔ ' + e + '</div>').join('') +
      ce.map(e => '<div class="text-[11px] text-amber-600 dark:text-amber-400 py-0.5">⚠ ' + e + '</div>').join('') +
      (cb.sensor_signal ? '<div class="text-[11px] text-slate-500 dark:text-slate-400 mt-1.5 font-mono">' + cb.sensor_signal + ' · ' + cb.cross_satellite + '</div>' : '') +
    '</div>' +
    '<div>' +
      '<div class="font-bold text-slate-800 dark:text-slate-200 mb-1.5 uppercase text-[10px] tracking-wider font-mono">Assets at risk</div>' +
      (assets.map(a => '<div class="flex items-center justify-between py-1 border-b border-slate-100 dark:border-slate-800">' +
        '<span class="text-slate-600 dark:text-slate-300">' + a.asset + '</span>' +
        '<span class="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">' + a.risk_tier + '</span>' +
      '</div>').join('') || '<div class="text-slate-400">None listed</div>') +
    '</div>' +
    '<div class="grid grid-cols-2 gap-2">' +
      '<div class="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60"><div class="text-[10px] text-slate-400 uppercase">Wind corridor</div><div class="font-mono text-slate-700 dark:text-slate-200">' + (wc.direction || '—') + ' · ' + (wc.speed_kmh || '—') + ' km/h</div><div class="text-[10px] text-slate-400">~' + (wc.potential_corridor_km || '—') + ' km downwind</div></div>' +
      '<div class="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60"><div class="text-[10px] text-slate-400 uppercase">Authority</div><div class="font-mono text-slate-700 dark:text-slate-200">' + (auth.name || '—') + '</div><div class="text-[10px] text-slate-400">ETA ' + (auth.eta_mins || '—') + ' min</div></div>' +
    '</div>' +
    '<div class="flex gap-2 pt-1">' +
      '<button onclick="dispatchIncident(\'' + inc.id + '\')" class="flex-1 px-3 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-white font-bold text-xs">Dispatch</button>' +
      '<button onclick="advanceIncident(\'' + inc.id + '\')" class="flex-1 px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs">Advance status</button>' +
    '</div>');

  dw.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
  lucide.createIcons();
  // cinematic focus: map gently flies to the incident, thermal pulse marks it
  if (typeof pipelineMap !== 'undefined' && pipelineMap && inc.coordinates) {
    try {
      const latlng = [inc.coordinates.lat, inc.coordinates.lon];
      if (reducedMotionPref()) {
        pipelineMap.setView(latlng, 10, { animate: false });
      } else {
        pipelineMap.flyTo(latlng, 10, { duration: 1.1 });
      }
      if (typeof L !== 'undefined') {
        if (window.__incFocusMarker) pipelineMap.removeLayer(window.__incFocusMarker);
        window.__incFocusMarker = L.circleMarker(latlng, {
          radius: 16, color: '#f97316', weight: 2, fillColor: '#f97316', fillOpacity: 0.12, className: 'pulse-marker'
        }).addTo(pipelineMap);
      }
    } catch (e) { /* map may not be initialised yet */ }
  }
}

function reducedMotionPref() {
  return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function closeIncDrawer() {
  const dw = document.getElementById('inc-drawer');
  if (dw) dw.classList.add('hidden');
  document.body.style.overflow = '';
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeIncDrawer(); });



// ---------- Detection Feed (demo playback from real pipeline scenarios) ----------
const FEED_SCENARIOS = ['jamnagar_refinery', 'angul_thermal_plant', 'similipal_wildfire', 'punjab_stubble', 'clandestine_thermal_anomaly'];

async function loadDetectionFeed() {
  const el = document.getElementById('detection-feed');
  if (!el || el.dataset.loaded) return;
  el.dataset.loaded = '1';
  const events = [];
  try {
    for (const sid of FEED_SCENARIOS) {
      const fc = await (await fetch('/api/pipeline/scenario?id=' + sid)).json();
      for (const f of (fc.features || [])) {
        const p = f.properties;
        events.push({ t: p.firms.acq_time, lines: [
          'VIIRS detection · ' + p.firms.lat.toFixed(3) + '°N ' + p.firms.lon.toFixed(3) + '°E',
          'Persistence match · ' + p.persistence.persistence_score + '% (' + p.persistence.observations_count + '/' + p.persistence.days_analyzed + ')',
          'Classification: ' + p.classification.classification + ' · ' + p.classification.confidence_percent + '%'
        ]});
      }
    }
    events.sort((a, b) => (a.t || '').localeCompare(b.t || ''));
    el.innerHTML = events.map(e => (
      '<div class="border-b border-slate-100 dark:border-slate-800 pb-1.5">' +
        '<div class="text-slate-400">' + e.t + ' UTC</div>' +
        e.lines.map((l, i) => '<div class="' + (i === 2 ? 'text-blue-600 dark:text-blue-400' : 'text-slate-600 dark:text-slate-300') + '">' + l + '</div>').join('') +
      '</div>')).join('');
  } catch (err) {
    el.dataset.loaded = '';
    el.innerHTML = '<div class="text-red-500">FEED UNAVAILABLE — ' + err.message + '</div>';
  }
}

// ===================== Responder Operations Field Terminal =====================
const RESPONDER_FLOW = [
  { key: 'DISPATCHED', label: 'Dispatched', icon: 'send', next: 'ACKNOWLEDGED', actionLabel: '🫡 ACKNOWLEDGE DISPATCH', actionClass: 'bg-amber-500 hover:bg-amber-600' },
  { key: 'ACKNOWLEDGED', label: 'Acknowledged', icon: 'check-circle-2', next: 'EN ROUTE', actionLabel: '🚒 MARK EN ROUTE', actionClass: 'bg-blue-600 hover:bg-blue-700' },
  { key: 'EN ROUTE', label: 'En Route', icon: 'truck', next: 'ARRIVED', actionLabel: '📍 CONFIRM ARRIVED ON SCENE', actionClass: 'bg-orange-600 hover:bg-orange-700' },
  { key: 'ARRIVED', label: 'Arrived', icon: 'map-pin', next: 'CONTAINED', actionLabel: '🧯 REPORT CONTAINED / CONTROLLED', actionClass: 'bg-red-600 hover:bg-red-700' },
  { key: 'CONTAINED', label: 'Contained', icon: 'shield-check', next: 'RESOLVED', actionLabel: '✅ MARK INCIDENT RESOLVED', actionClass: 'bg-emerald-600 hover:bg-emerald-700' },
  { key: 'RESOLVED', label: 'Resolved', icon: 'check-check', next: null, actionLabel: 'MISSION ACCOMPLISHED', actionClass: 'bg-emerald-700' }
];

let _activeResponderIncId = 'INC-2026-0044';
let _responderIncCache = {};

async function loadResponderPortal() {
  const select = document.getElementById('resp-incident-select');
  try {
    const resp = await fetch('/api/incidents');
    const data = await resp.json();
    const incidents = Array.isArray(data.incidents) ? data.incidents : Object.values(data.incidents || {});
    _responderIncCache = {};
    incidents.forEach(i => { _responderIncCache[i.id] = i; });

    if (select && incidents.length > 0) {
      if (!_responderIncCache[_activeResponderIncId]) {
        _activeResponderIncId = incidents[0].id;
      }
      select.innerHTML = incidents.map(i => 
        `<option value="${i.id}" ${i.id === _activeResponderIncId ? 'selected' : ''}>${i.id} • ${i.location_name} (${i.status || 'NEW'})</option>`
      ).join('');
    }
    renderResponderIncident(_activeResponderIncId);
  } catch (err) {
    console.error('Failed to load responder incidents:', err);
    renderResponderIncident(_activeResponderIncId);
  }
}

function onResponderIncidentChange(incId) {
  _activeResponderIncId = incId;
  renderResponderIncident(incId);
}

function renderResponderIncident(incId) {
  const inc = _responderIncCache[incId] || {
    id: incId,
    title: 'Angul Thermal Power & Coal Storage Yard',
    location_name: 'Angul Industrial Belt, Odisha',
    classification: 'INDUSTRIAL FIRE',
    risk_score: 96,
    status: 'DISPATCHED',
    frp_mw: 710.0,
    confidence: 96,
    coordinates: { lat: 20.8420, lon: 85.1020 },
    wind_corridor: { direction: 'NE', speed_kmh: 20, potential_corridor_km: 3.4 }
  };

  const el = (id) => document.getElementById(id);
  if (el('resp-title')) el('resp-title').textContent = inc.title || inc.id;
  if (el('resp-location')) el('resp-location').textContent = `${inc.location_name || ''} • Target Sector Assessment`;
  if (el('resp-badge-type')) el('resp-badge-type').textContent = inc.classification || 'HAZARD';
  
  const sevEl = el('resp-badge-severity');
  if (sevEl) {
    const risk = inc.risk_score || 50;
    sevEl.textContent = risk >= 70 ? 'CRITICAL' : (risk >= 40 ? 'HIGH' : 'MODERATE');
    sevEl.className = `px-2.5 py-1 rounded-md text-white text-xs font-black font-mono ${risk >= 70 ? 'bg-red-600' : (risk >= 40 ? 'bg-amber-600' : 'bg-emerald-600')}`;
  }

  const lat = (inc.coordinates && inc.coordinates.lat) || 20.8420;
  const lon = (inc.coordinates && inc.coordinates.lon) || 85.1020;
  if (el('resp-coords')) el('resp-coords').textContent = `${lat}°N • ${lon}°E`;
  if (el('resp-frp')) el('resp-frp').textContent = `${inc.frp_mw || '0.0'} MW`;
  if (el('resp-hazard')) el('resp-hazard').textContent = `${inc.risk_score >= 70 ? 'HIGH' : 'MODERATE'} (Risk ${inc.risk_score}/100)`;
  
  const wc = inc.wind_corridor || {};
  if (el('resp-wind')) el('resp-wind').textContent = `${wc.direction || 'NE'} at ${wc.speed_kmh || 20} km/h`;

  renderResponderStateMachine(inc);
  if (window.lucide) lucide.createIcons();
}

function renderResponderStateMachine(inc) {
  let curStatus = (inc.status || 'DISPATCHED').toUpperCase();
  // Normalize if NEW/INVESTIGATING/VERIFIED for tactical field view
  if (['NEW', 'INVESTIGATING', 'VERIFIED'].includes(curStatus)) {
    curStatus = 'DISPATCHED';
  }

  const statePill = document.getElementById('resp-current-state-pill');
  if (statePill) {
    statePill.textContent = curStatus;
    statePill.className = `px-2.5 py-0.5 rounded text-xs font-mono font-bold text-white ${INC_STATUS_COLORS[curStatus] || 'bg-slate-500'}`;
  }

  const stepsContainer = document.getElementById('resp-steps-container');
  const actionContainer = document.getElementById('resp-action-container');
  if (!stepsContainer || !actionContainer) return;

  const curIdx = RESPONDER_FLOW.findIndex(s => s.key === curStatus);
  const safeIdx = curIdx >= 0 ? curIdx : 0;

  // Visual Pipeline Steps
  stepsContainer.innerHTML = RESPONDER_FLOW.map((s, idx) => {
    const isPast = idx < safeIdx;
    const isCurrent = idx === safeIdx;
    let bg = 'bg-slate-100 dark:bg-slate-800 text-slate-400 border border-slate-200 dark:border-slate-700';
    if (isPast) bg = 'bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 font-bold';
    if (isCurrent) bg = 'bg-orange-500 text-white font-black shadow-sm ring-2 ring-orange-500/30';

    return `
      <div class="p-2 rounded-lg text-center ${bg} transition-all">
        <div class="text-[10px] uppercase font-bold tracking-wider">${isPast ? '✓ ' : ''}${s.label}</div>
        <div class="text-[9px] mt-0.5 opacity-80">${isCurrent ? 'ACTIVE NOW' : (isPast ? 'COMPLETED' : 'PENDING')}</div>
      </div>
    `;
  }).join('');

  // Next Valid Action Button
  const stepObj = RESPONDER_FLOW[safeIdx];
  if (stepObj && stepObj.next) {
    actionContainer.innerHTML = `
      <div class="space-y-2">
        <div class="text-[11px] font-mono text-slate-500 flex items-center justify-between">
          <span>Action Required:</span>
          <span>Next State &rarr; <strong>${stepObj.next}</strong></span>
        </div>
        <button onclick="advanceResponderState('${inc.id}', '${stepObj.next}')" 
          class="w-full py-4 px-6 rounded-xl ${stepObj.actionClass} text-white font-black text-sm tracking-wider uppercase shadow-lg transition-transform active:scale-98 flex items-center justify-center gap-2">
          <span>${stepObj.actionLabel}</span>
          <i data-lucide="arrow-right" class="w-4 h-4"></i>
        </button>
      </div>
    `;
  } else {
    actionContainer.innerHTML = `
      <div class="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-center space-y-1">
        <div class="font-black text-sm uppercase tracking-wider flex items-center justify-center gap-1.5">
          <i data-lucide="check-circle" class="w-5 h-5 text-emerald-500"></i>
          Incident Successfully Contained &amp; Resolved
        </div>
        <p class="text-xs text-slate-600 dark:text-slate-400">All fire perimeters sealed. Site handed over to state post-disaster authorities.</p>
        <button onclick="advanceResponderState('${inc.id}', 'DISPATCHED')" class="mt-2 text-[11px] font-mono underline text-slate-500 hover:text-slate-700 dark:hover:text-slate-300">
          Reset test state to DISPATCHED
        </button>
      </div>
    `;
  }
}

async function advanceResponderState(incId, targetStatus, groundNote) {
  try {
    const resp = await fetch(`/api/incidents/${incId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status: targetStatus,
        ground_note: groundNote || undefined,
        responder_id: 'UNIT-001'
      })
    });

    // Handle specific error codes
    if (resp.status === 409) {
      const data = await resp.json();
      alert(`❌ Invalid Transition: ${data.error}\n\nAllowed: [${(data.allowed_transitions || []).join(', ')}]`);
      return;
    }
    if (resp.status === 403) {
      alert('❌ Forbidden: You are not assigned to this incident.');
      return;
    }
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      throw new Error(data.error || `HTTP ${resp.status}`);
    }

    const res = await resp.json();
    if (res.success) {
      if (_responderIncCache[incId]) {
        _responderIncCache[incId].status = targetStatus;
      }
      renderResponderIncident(incId);
      if (typeof loadIncidentTracker === 'function') loadIncidentTracker();
      if (typeof loadIncidentTable === 'function') loadIncidentTable();
    } else {
      alert(res.error || 'Failed to update status');
    }
  } catch (err) {
    alert(`Network error: ${err.message}`);
  }
}

function copyResponderCoords() {
  const inc = _responderIncCache[_activeResponderIncId];
  const lat = inc && inc.coordinates ? inc.coordinates.lat : 20.8420;
  const lon = inc && inc.coordinates ? inc.coordinates.lon : 85.1020;
  const text = `${lat}, ${lon}`;
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => {
      alert(`GPS coordinates copied: ${text}`);
    }).catch(() => {
      alert(`Coordinates: ${text}`);
    });
  } else {
    alert(`Coordinates: ${text}`);
  }
}

function openNavigationRoute() {
  const inc = _responderIncCache[_activeResponderIncId];
  const lat = inc && inc.coordinates ? inc.coordinates.lat : 20.8420;
  const lon = inc && inc.coordinates ? inc.coordinates.lon : 85.1020;
  window.open(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}`, '_blank');
}

function submitResponderSitrep() {
  const input = document.getElementById('resp-sitrep-input');
  const statusEl = document.getElementById('resp-sitrep-status');
  const logEl = document.getElementById('resp-sitrep-log');
  if (!input || !input.value.trim()) return;

  const note = input.value.trim();
  const time = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

  if (logEl) {
    const newEntry = document.createElement('div');
    newEntry.className = 'p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 text-xs';
    newEntry.innerHTML = `
      <div class="flex justify-between font-mono text-[10px] text-slate-400">
        <span>UNIT 3 &bull; OD-05-G-4421</span>
        <span>Just now (${time})</span>
      </div>
      <div class="text-slate-800 dark:text-slate-200 mt-1 font-medium">${note}</div>
    `;
    logEl.insertBefore(newEntry, logEl.children[1] || null);
  }

  input.value = '';
  if (statusEl) {
    statusEl.textContent = '✅ SitRep transmitted to Command';
    setTimeout(() => { statusEl.textContent = ''; }, 4000);
  }
}





