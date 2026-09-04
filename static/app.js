// AeroThermal Incident & First Responder Engine (SIH26162)
let map = null;
let currentLayer = 'dark';
let darkTiles = null;
let satTiles = null;
let markersLayer = null;
let activeIncident = null;
let allIncidents = {};

document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    initMap();
    loadAllIncidents();
});

function initMap() {
    map = L.map('map', {
        center: [21.8540, 86.3520],
        zoom: 11,
        attributionControl: false
    });

    darkTiles = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 19 });
    satTiles = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 18 });

    darkTiles.addTo(map);
    markersLayer = L.layerGroup().addTo(map);
}

function toggleMapLayer() {
    const btn = document.getElementById('layerToggleBtn');
    if (currentLayer === 'dark') {
        map.removeLayer(darkTiles);
        satTiles.addTo(map);
        currentLayer = 'sat';
        btn.innerHTML = `<i data-lucide="layers" class="w-3.5 h-3.5"></i> Dark Map`;
    } else {
        map.removeLayer(satTiles);
        darkTiles.addTo(map);
        currentLayer = 'dark';
        btn.innerHTML = `<i data-lucide="layers" class="w-3.5 h-3.5"></i> Satellite View`;
    }
    lucide.createIcons();
}

// Switch between Control Room and First Responder View (The Winning Demo Loop!)
function switchView(viewName) {
    const btnControl = document.getElementById('btnViewControl');
    const btnResp = document.getElementById('btnViewResponder');
    const viewCtrl = document.getElementById('viewControlRoom');
    const viewRsp = document.getElementById('viewFirstResponder');

    if (viewName === 'control') {
        viewCtrl.classList.remove('hidden');
        viewRsp.classList.add('hidden');
        btnControl.className = "px-4 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-2 bg-gradient-to-r from-orange-600 to-amber-600 text-white shadow-md";
        btnResp.className = "px-4 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-2 text-slate-400 hover:text-slate-200";
        setTimeout(() => map.invalidateSize(), 150);
    } else {
        viewCtrl.classList.add('hidden');
        viewRsp.classList.remove('hidden');
        btnResp.className = "px-4 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-2 bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-md";
        btnControl.className = "px-4 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-2 text-slate-400 hover:text-slate-200";
        document.getElementById('responderPendingBadge').classList.add('hidden');
    }
    lucide.createIcons();
}

async function loadAllIncidents() {
    try {
        const resp = await fetch('/api/incidents');
        const data = await resp.json();
        data.incidents.forEach(inc => {
            allIncidents[inc.id] = inc;
        });
        selectIncident('INC-2026-0042');
    } catch (e) {
        console.error("Failed to fetch incidents:", e);
    }
}

async function selectIncident(incidentId) {
    try {
        const resp = await fetch(`/api/incident/${incidentId}`);
        const incident = await resp.json();
        activeIncident = incident;
        allIncidents[incident.id] = incident;
        renderIncident(incident);
    } catch (e) {
        console.error("Failed to select incident:", e);
    }
}

function renderIncident(inc) {
    // 1. Highlight Top Queue Cards
    document.querySelectorAll('.incident-card').forEach(card => {
        card.classList.remove('ring-2', 'ring-cyan-400');
    });
    const activeCard = document.getElementById(`card-${inc.id}`);
    if (activeCard) activeCard.classList.add('ring-2', 'ring-cyan-400');

    // 2. Control Room Banner
    document.getElementById('incIdBadge').textContent = `#${inc.id}`;
    document.getElementById('incTitle').textContent = inc.title;
    document.getElementById('incLocation').textContent = `${inc.location_name} • ${inc.timestamp}`;
    
    const riskBadge = document.getElementById('incRiskBadge');
    riskBadge.textContent = `RISK SCORE: ${inc.risk_score}/100 (${inc.risk_label})`;
    riskBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-bold font-mono uppercase border " +
        (inc.risk_score >= 75 ? 'bg-red-950 text-red-400 border-red-800' :
         inc.risk_score >= 50 ? 'bg-amber-950 text-amber-400 border-amber-800' :
         'bg-slate-800 text-slate-300 border-slate-700');

    // 3. Lifecycle Stepper
    updateLifecycleStepper(inc.status);

    // 4. Map and Downwind Corridor
    renderMap(inc);

    // 5. Assets at Risk Table (Module 4)
    renderAssetsAtRisk(inc.assets_at_risk);

    // 6. Authority Routing
    document.getElementById('authName').textContent = inc.assigned_authority.name;
    document.getElementById('authEta').textContent = `${inc.assigned_authority.distance_km} km • ETA ${inc.assigned_authority.eta_mins} mins`;
    document.getElementById('authJurisdiction').textContent = inc.assigned_authority.jurisdiction;
    document.getElementById('authSecondary').textContent = inc.assigned_authority.secondary_agency;

    // 7. Explain Classification ("Why?")
    const evList = document.getElementById('explainEvidenceList');
    evList.innerHTML = '';
    inc.explain_classification.evidence.forEach(item => {
        const li = document.createElement('li');
        li.textContent = item;
        evList.appendChild(li);
    });

    const counterList = document.getElementById('explainCounterList');
    counterList.innerHTML = '';
    inc.explain_classification.counter_evidence.forEach(item => {
        const li = document.createElement('li');
        li.textContent = item;
        counterList.appendChild(li);
    });

    // 8. Historical Local Baseline
    document.getElementById('basePasses').textContent = `${inc.local_baseline.location_history_passes} passes in 60 days`;
    document.getElementById('baseRange').textContent = inc.local_baseline.normal_seasonal_range;
    document.getElementById('baseRatio').textContent = inc.local_baseline.anomaly_ratio;
    document.getElementById('baseVerdict').textContent = inc.local_baseline.verdict;

    // 9. Synchronize First Responder View
    renderResponderView(inc);

    lucide.createIcons();
}

function updateLifecycleStepper(status) {
    const steps = ['NEW', 'INVESTIGATING', 'VERIFIED', 'DISPATCHED', 'CONTAINED', 'RESOLVED'];
    const idx = steps.indexOf(status);

    steps.forEach((s, i) => {
        const el = document.getElementById(`step-${s}`);
        if (el) {
            if (i <= idx) {
                el.className = "font-bold text-cyan-400";
            } else {
                el.className = "text-slate-500";
            }
        }
    });

    const progressPct = Math.max(16, ((idx + 1) / steps.length) * 100);
    document.getElementById('lifecycleProgressBar').style.width = `${progressPct}%`;
}

function renderMap(inc) {
    markersLayer.clearLayers();
    map.setView([inc.coordinates.lat, inc.coordinates.lon], 11);

    // Fire Anomaly Circle
    const circle = L.circleMarker([inc.coordinates.lat, inc.coordinates.lon], {
        radius: Math.max(10, Math.min(30, inc.frp_mw / 4)),
        fillColor: inc.risk_score >= 75 ? '#ef4444' : '#f97316',
        color: '#ffffff',
        weight: 2,
        opacity: 0.9,
        fillOpacity: 0.75,
        className: 'thermal-flare-icon'
    }).addTo(markersLayer);

    circle.bindPopup(`
        <div class="text-xs space-y-1 font-mono">
            <div class="font-bold text-orange-400 border-b border-slate-700 pb-1">${inc.id}: ${inc.classification}</div>
            <div><strong>FRP:</strong> ${inc.frp_mw} MW</div>
            <div><strong>Temp:</strong> ${inc.brightness_c}°C</div>
            <div><strong>Status:</strong> ${inc.status}</div>
            <div><strong>Location:</strong> ${inc.location_name}</div>
        </div>
    `);

    // Downwind Impact Corridor Cone (Directional approximation)
    document.getElementById('corridorText').textContent = inc.wind_corridor.description;

    // Render Assets at Risk on Map
    inc.assets_at_risk.forEach(asset => {
        const offsetLat = inc.coordinates.lat + (Math.random() - 0.5) * 0.04;
        const offsetLon = inc.coordinates.lon + (Math.random() - 0.5) * 0.04;

        const assetPin = L.circleMarker([offsetLat, offsetLon], {
            radius: 5,
            fillColor: asset.color === 'red' ? '#ef4444' : asset.color === 'orange' ? '#f97316' : '#10b981',
            color: '#000000',
            weight: 1,
            fillOpacity: 0.85
        }).addTo(markersLayer);

        assetPin.bindPopup(`<strong>${asset.asset}</strong><br>Distance: ${asset.distance_km} km<br>Exposure: ${asset.population}`);
    });
}

function renderAssetsAtRisk(assets) {
    const tbody = document.getElementById('assetsTableBody');
    tbody.innerHTML = '';

    assets.forEach(a => {
        const badgeColor = a.color === 'red' ? 'bg-red-950 text-red-400 border-red-800' :
                           a.color === 'orange' ? 'bg-orange-950 text-orange-400 border-orange-800' :
                           a.color === 'yellow' ? 'bg-amber-950 text-amber-400 border-amber-800' :
                           'bg-emerald-950 text-emerald-400 border-emerald-800';

        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-900/60 transition-colors';
        tr.innerHTML = `
            <td class="py-2 px-2 font-medium text-slate-200">${a.asset}</td>
            <td class="py-2 px-2 text-cyan-300">${a.distance_km} km</td>
            <td class="py-2 px-2 text-slate-400">${a.population}</td>
            <td class="py-2 px-2"><span class="px-1.5 py-0.5 rounded text-[10px] font-bold border ${badgeColor}">${a.risk_tier}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// Module 5: Simulate Ground Alert Dispatch (The Big Stage Trigger)
async function dispatchGroundAlert() {
    if (!activeIncident) return;

    const btn = document.getElementById('btnDispatchAlert');
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> TRANSMITTING ENCRYPTED ALERT...`;
    lucide.createIcons();

    try {
        const resp = await fetch(`/api/incident/${activeIncident.id}/dispatch`, { method: 'POST' });
        const res = await resp.json();

        // Update local state
        activeIncident.status = 'DISPATCHED';
        allIncidents[activeIncident.id].status = 'DISPATCHED';
        updateLifecycleStepper('DISPATCHED');

        // Alert Feedback Box
        const alertBox = document.getElementById('dispatchAlertBox');
        alertBox.className = "p-3 rounded-lg border border-emerald-500/50 bg-emerald-950/30 text-xs flex items-center gap-3";
        document.getElementById('dispatchIcon').className = "w-4 h-4 text-emerald-400";
        document.getElementById('dispatchStatusText').innerHTML = 
            `<strong>ALERT TRANSMITTED:</strong> ${res.dispatched_to} (ETA: ${res.eta}) &bull; Simulated emergency dispatch acknowledged.`;

        // Flash badge on First Responder view tab
        document.getElementById('responderPendingBadge').classList.remove('hidden');

        // Update First Responder screen
        renderResponderView(activeIncident);

    } catch (e) {
        console.error(e);
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="check" class="w-4 h-4"></i> DISPATCHED // ALERT CONFIRMED`;
        lucide.createIcons();
    }
}

// Render the First Responder Field Screen
function renderResponderView(inc) {
    document.getElementById('frIncId').textContent = `#${inc.id}`;
    document.getElementById('frIncTitle').textContent = inc.title;
    document.getElementById('frIncCoords').textContent = `Location: ${inc.coordinates.lat.toFixed(4)}°N, ${inc.coordinates.lon.toFixed(4)}°E • Distance: ${inc.assigned_authority.distance_km} km • ETA: ${inc.assigned_authority.eta_mins} mins`;

    const statusBadge = document.getElementById('frCurrentStatusBadge');
    statusBadge.textContent = inc.status;
    statusBadge.className = "text-sm font-mono font-bold px-3 py-1 rounded-full uppercase border " +
        (inc.status === 'RESOLVED' ? 'bg-emerald-950 text-emerald-400 border-emerald-800' :
         inc.status === 'CONTAINED' ? 'bg-purple-950 text-purple-400 border-purple-800' :
         inc.status === 'EN ROUTE' || inc.status === 'ARRIVED' ? 'bg-amber-950 text-amber-400 border-amber-800' :
         'bg-cyan-950 text-cyan-400 border-cyan-800');

    document.getElementById('frFrp').textContent = `${inc.frp_mw} MegaWatts`;
    document.getElementById('frHabitation').textContent = inc.assets_at_risk[0] ? inc.assets_at_risk[0].asset : 'No nearby village';
    document.getElementById('frWind').textContent = `${inc.wind_corridor.direction} at ${inc.wind_corridor.speed_kmh} km/h`;

    // Highlight active state button
    const states = ['ACKNOWLEDGED', 'EN ROUTE', 'ARRIVED', 'CONTAINED', 'RESOLVED'];
    states.forEach(st => {
        const btn = document.getElementById(`btnStat-${st}`);
        if (btn) {
            if (inc.status === st) {
                btn.classList.add('ring-2', 'ring-white', 'bg-cyan-600');
            } else {
                btn.classList.remove('ring-2', 'ring-white', 'bg-cyan-600');
            }
        }
    });
}

// State Machine Button Handlers in First Responder View
async function updateResponderStatus(newStatus) {
    if (!activeIncident) return;

    try {
        const resp = await fetch(`/api/incident/${activeIncident.id}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        const res = await resp.json();

        // Update local object
        activeIncident.status = newStatus;
        allIncidents[activeIncident.id].status = newStatus;

        // Re-render both views
        updateLifecycleStepper(newStatus);
        renderResponderView(activeIncident);

        // If contained or resolved, update control room banner
        if (newStatus === 'RESOLVED') {
            document.getElementById('dispatchStatusText').innerHTML = 
                `<strong class="text-emerald-400">MISSION RESOLVED:</strong> Ground crew verified fire extinguished. Verified ground truth stored in database.`;
        }

    } catch (e) {
        console.error(e);
    }
}

// Export GeoJSON
function exportGeoJson() {
    if (!activeIncident) return;
    const geojson = {
        type: "FeatureCollection",
        features: [
            {
                type: "Feature",
                geometry: { type: "Point", coordinates: [activeIncident.coordinates.lon, activeIncident.coordinates.lat] },
                properties: {
                    incident_id: activeIncident.id,
                    title: activeIncident.title,
                    classification: activeIncident.classification,
                    risk_score: activeIncident.risk_score,
                    frp_mw: activeIncident.frp_mw,
                    status: activeIncident.status
                }
            }
        ]
    };
    const blob = new Blob([JSON.stringify(geojson, null, 2)], { type: 'application/geo+json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${activeIncident.id}_Dossier.geojson`;
    a.click();
    URL.revokeObjectURL(url);
}

// Export Official PDF Incident Dossier
function exportDossierPdf() {
    if (!activeIncident) return;
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    const inc = activeIncident;

    // Header Banner
    doc.setFillColor(15, 23, 42);
    doc.rect(0, 0, 210, 32, 'F');
    doc.setTextColor(249, 115, 22);
    doc.setFontSize(18);
    doc.setFont('helvetica', 'bold');
    doc.text("AEROTHERMAL | INCIDENT DOSSIER", 14, 15);
    doc.setFontSize(9);
    doc.setTextColor(148, 163, 184);
    doc.text(`Incident ID: ${inc.id} | Status: ${inc.status} | Generated: ${new Date().toUTCString()}`, 14, 23);

    // Risk Banner
    doc.setFillColor(239, 68, 68);
    doc.roundedRect(14, 38, 182, 14, 2, 2, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(11);
    doc.text(`INCIDENT: ${inc.classification} (Risk Score: ${inc.risk_score}/100 - ${inc.risk_label})`, 20, 47);

    // Metadata Table
    doc.autoTable({
        startY: 56,
        head: [['Field', 'Operational Value']],
        body: [
            ['Incident Title', inc.title],
            ['Coordinates', `${inc.coordinates.lat}°N, ${inc.coordinates.lon}°E`],
            ['Fire Radiative Power', `${inc.frp_mw} MegaWatts`],
            ['Brightness Temp', `${inc.brightness_c} °C`],
            ['Assigned Authority', `${inc.assigned_authority.name} (${inc.assigned_authority.distance_km} km, ETA: ${inc.assigned_authority.eta_mins} mins)`],
            ['Downwind Impact Corridor', inc.wind_corridor.description],
            ['Historical Local Baseline', inc.local_baseline.anomaly_ratio]
        ],
        theme: 'grid',
        headStyles: { fillColor: [30, 41, 59] },
        styles: { fontSize: 8 }
    });

    // Assets at Risk Table
    const assetRows = inc.assets_at_risk.map(a => [a.asset, `${a.distance_km} km`, a.population, a.risk_tier]);
    doc.setFontSize(11);
    doc.setTextColor(15, 23, 42);
    doc.text("Assets-at-Risk & Population Exposure", 14, doc.lastAutoTable.finalY + 12);

    doc.autoTable({
        startY: doc.lastAutoTable.finalY + 16,
        head: [['Asset', 'Distance', 'Exposure / Population', 'Risk Level']],
        body: assetRows,
        theme: 'grid',
        headStyles: { fillColor: [249, 115, 22] },
        styles: { fontSize: 8 }
    });

    doc.save(`${inc.id}_Incident_Dossier.pdf`);
}
