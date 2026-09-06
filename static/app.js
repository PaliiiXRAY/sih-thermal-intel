// FireSense Client Application - SIH26162
let currentPortal = 'command';
let currentNtroFilter = 'all';
let currentLanguage = 'en';

// Sample Data for NTRO Intelligence (Matching Figma)
const ntroIncidents = [
    {
        id: 'INC-2846', time: '03:55 UTC', location: 'Malkangiri, Odisha',
        category: 'wildfire', label: 'Wildfire', severity: 'HIGH',
        confidence: 91, coords: '18.92°N • 82.10°E',
        temp: '623°C', area: '12.8 km²', source: 'VIIRS',
        facility: 'Dense Forest Reserve', matchText: 'Dense Forest Reserve • Odisha Forest & Protected Land Database',
        wind: 'Surface Wind: NE at 18 km/h • Downwind Threat Corridor: 2.8 km (toward NH-326)'
    },
    {
        id: 'INC-2845', time: '03:41 UTC', location: 'Mehsana, Gujarat',
        category: 'gas-flare', label: 'Gas Flare', severity: 'ROUTINE',
        confidence: 99, coords: '23.60°N • 72.40°E',
        temp: '412°C', area: '0.4 km²', source: 'VIIRS',
        facility: 'ONGC Extraction Unit 4', matchText: 'Licensed Gas Flare Facility • Gujarat Industrial Development Corp',
        wind: 'Surface Wind: W at 9 km/h • Downwind Threat Corridor: 0.2 km (Enclosed Perimeter)'
    },
    {
        id: 'INC-2844', time: '02:18 UTC', location: 'Ropar, Punjab',
        category: 'crop-burning', label: 'Crop Burning', severity: 'MODERATE',
        confidence: 88, coords: '30.97°N • 76.53°E',
        temp: '350°C', area: '3.2 km²', source: 'MODIS',
        facility: 'Agricultural Farmland Block B', matchText: 'Farmland Cluster • Punjab Remote Sensing Centre (PRSC)',
        wind: 'Surface Wind: NW at 14 km/h • Downwind Threat Corridor: 1.5 km (Smoke plume over State Hwy)'
    },
    {
        id: 'INC-2843', time: '01:47 UTC', location: 'Faridabad, Haryana',
        category: 'illegal', label: 'Illegal', severity: 'ALERT',
        confidence: 84, coords: '28.41°N • 77.31°E',
        temp: '480°C', area: '0.8 km²', source: 'VIIRS',
        facility: 'Unauthorized Waste Dump', matchText: 'Municipal Buffer Zone • Haryana State Pollution Control Board',
        wind: 'Surface Wind: E at 11 km/h • Downwind Threat Corridor: 0.9 km (toward Residential Sector 58)'
    },
    {
        id: 'INC-2842', time: '01:12 UTC', location: 'Vadodara, Gujarat',
        category: 'industrial', label: 'Industrial', severity: 'HIGH',
        confidence: 93, coords: '22.31°N • 73.18°E',
        temp: '590°C', area: '4.5 km²', source: 'VIIRS',
        facility: 'Petrochemical Complex Gate 3', matchText: 'Petrochemical Refinement Facility • National Industrial Cadastre',
        wind: 'Surface Wind: SW at 16 km/h • Downwind Threat Corridor: 2.1 km (Industrial Corridor)'
    },
    {
        id: 'INC-2841', time: '00:29 UTC', location: 'Angul, Odisha',
        category: 'industrial', label: 'Industrial', severity: 'CRITICAL',
        confidence: 96, coords: '20.84°N • 85.10°E',
        temp: '710°C', area: '6.1 km²', source: 'VIIRS',
        facility: 'Thermal Power & Coal Storage', matchText: 'Thermal Plant Storage Yard • Odisha State Disaster Management',
        wind: 'Surface Wind: NE at 20 km/h • Downwind Threat Corridor: 3.4 km (Crossing toward NH-55)'
    }
];

// Sample Data for Government Command (Matching Figma)
const cmdZones = [
    {
        id: 'angul', name: 'Angul, Odisha', type: 'Industrial', severity: 'CRITICAL',
        deployedText: '3/4 teams deployed', pop: '82K', teamsCount: '3 / 4',
        deployedNum: 3, maxTeams: 4, ndrfPercent: 60
    },
    {
        id: 'malkangiri', name: 'Malkangiri, Odisha', type: 'Wildfire', severity: 'HIGH',
        deployedText: '2/6 teams deployed', pop: '14K', teamsCount: '2 / 6',
        deployedNum: 2, maxTeams: 6, ndrfPercent: 50
    },
    {
        id: 'vadodara', name: 'Vadodara, Gujarat', type: 'Industrial', severity: 'HIGH',
        deployedText: '3/3 teams deployed', pop: '45K', teamsCount: '3 / 3',
        deployedNum: 3, maxTeams: 3, ndrfPercent: 65
    },
    {
        id: 'faridabad', name: 'Faridabad, Haryana', type: 'Illegal', severity: 'ALERT',
        deployedText: '1/2 teams deployed', pop: '18K', teamsCount: '1 / 2',
        deployedNum: 1, maxTeams: 2, ndrfPercent: 45
    },
    {
        id: 'ropar', name: 'Ropar, Punjab', type: 'Crop Burning', severity: 'MODERATE',
        deployedText: '0/1 teams deployed', pop: '16K', teamsCount: '0 / 1',
        deployedNum: 0, maxTeams: 1, ndrfPercent: 40
    }
];

let selectedZoneId = 'angul';
let selectedNtroId = 'INC-2846';

// Translations for Citizen Services
const translations = {
    en: {
        title: "Disaster Help Services",
        subtitle: "Find shelter, food, evacuation routes and emergency contacts near you.",
        sosBtn: "SOS — I Need Help Now",
        alertsHeading: "Active Alerts Near You",
        alert1: "Industrial fire in Angul — stay indoors, close windows",
        alert2: "Wildfire moving NE from Malkangiri forest zone",
        alert3: "Stubble burning alert — avoid outdoor activity today",
        servicesHeading: "Services Available",
        shelter: "Nearest Shelter",
        hospital: "Emergency Hospital",
        food: "Food & Water",
        bus: "Evacuation Bus",
        fuel: "Fuel Station",
        helpline: "Emergency Helpline",
        routeHeading: "Evacuation Route",
        step1: "🚶 Head to NH-55 via Market Road — avoid Thermal Plant area",
        step2: "🌉 Cross Brahmani river bridge — open and clear",
        step3: "🏫 Reach Govt High School — shelter, food, first aid ready",
        btnMap: "Open Live Map",
        numHeading: "Emergency Numbers"
    },
    hi: {
        title: "आपदा सहायता सेवाएं",
        subtitle: "अपने निकटतम राहत शिविर, भोजन, सुरक्षित निकासी मार्ग और आपातकालीन संपर्क प्राप्त करें।",
        sosBtn: "🆘 आपातकाल (SOS) — तुरंत सहायता चाहिए",
        alertsHeading: "आपके क्षेत्र में सक्रिय अलर्ट",
        alert1: "अंगुल में औद्योगिक आग — कृपया घरों के अंदर रहें, खिड़कियां बंद रखें",
        alert2: "मलकानगिरी वन क्षेत्र से उत्तर-पूर्व की ओर फैल रही दावानल",
        alert3: "पराली दहन चेतावनी — आज बाहरी गतिविधियों से बचें",
        servicesHeading: "उपलब्ध आपातकालीन सेवाएं",
        shelter: "निकटतम राहत शिविर",
        hospital: "आपातकालीन अस्पताल",
        food: "भोजन एवं पेयजल केंद्र",
        bus: "निकासी बस सेवा",
        fuel: "ईंधन / पेट्रोल पंप",
        helpline: "आपातकालीन हेल्पलाइन",
        routeHeading: "सुरक्षित निकासी मार्ग",
        step1: "🚶 मार्केट रोड से राष्ट्रीय राजमार्ग 55 की ओर जाएं — थर्मल प्लांट क्षेत्र से बचें",
        step2: "🌉 ब्राह्मणी नदी पुल पार करें — मार्ग खुला एवं सुरक्षित है",
        step3: "🏫 शासकीय उच्च विद्यालय पहुंचें — आश्रय, भोजन एवं प्राथमिक चिकित्सा तैयार है",
        btnMap: "लाइव नक्शा खोलें",
        numHeading: "आपातकालीन नंबर"
    },
    od: {
        title: "ବିପର୍ଯ୍ୟୟ ସହାୟତା ସେବା",
        subtitle: "ଆପଣଙ୍କ ନିକଟସ୍ଥ ଆଶ୍ରୟସ୍ଥଳୀ, ଖାଦ୍ୟ, ନିରାପଦ ନିଷ୍କ୍ରମଣ ପଥ ଏବଂ ଜରୁରୀକାଳୀନ ଯୋଗାଯୋଗ ଖୋଜନ୍ତୁ।",
        sosBtn: "🆘 ଜରୁରୀ ସହାୟତା (SOS) — ମୋତେ ତୁରନ୍ତ ସାହାଯ୍ୟ ଦରକାର",
        alertsHeading: "ଆପଣଙ୍କ ନିକଟରେ ସକ୍ରିୟ ଚେତାବନୀ",
        alert1: "ଅନୁଗୁଳରେ ଶିଳ୍ପାଞ୍ଚଳ ଅଗ୍ନିକାଣ୍ଡ — ଘରେ ରୁହନ୍ତୁ, ଝରକା ବନ୍ଦ ରଖନ୍ତୁ",
        alert2: "ମାଲକାନଗିରି ଜଙ୍ଗଲରୁ ଉତ୍ତର-ପୂର୍ବ ଦିଗକୁ ବ୍ୟାପୁଥିବା ନିଆଁ",
        alert3: "ନଡ଼ା ଜଳିବା ସତର୍କତା — ବାହାରକୁ ଯିବାରୁ ନିବୃତ୍ତ ରୁହନ୍ତୁ",
        servicesHeading: "ଉପଲବ୍ଧ ସେବାସମୂହ",
        shelter: "ନିକଟସ୍ଥ ଆଶ୍ରୟସ୍ଥଳୀ",
        hospital: "ଜରୁରୀକାଳୀନ ଚିକିତ୍ସାଳୟ",
        food: "ଖାଦ୍ୟ ଓ ପାନୀୟ ଜଳ",
        bus: "ସ୍ଥାନାନ୍ତର ବସ୍",
        fuel: "ପେଟ୍ରୋଲ ପମ୍ପ",
        helpline: "ଜରୁରୀକାଳୀନ ହେଲ୍ପଲାଇନ୍",
        routeHeading: "ସୁରକ୍ଷିତ ନିଷ୍କ୍ରମଣ ମାର୍ଗ",
        step1: "🚶 ମାର୍କେଟ ରୋଡ୍ ଦେଇ NH-55 କୁ ଯାଆନ୍ତୁ — ଥର୍ମାଲ ପ୍ଲାଣ୍ଟ ଅଞ୍ଚଳ ଏଡ଼ାନ୍ତୁ",
        step2: "🌉 ବ୍ରାହ୍ମଣୀ ନଦୀ ପୋଲ ପାର ହୁଅନ୍ତୁ — ମାର୍ଗ ଖୋଲା ଏବଂ ସୁରକ୍ଷିତ",
        step3: "🏫 ସରକାରୀ ହାଇସ୍କୁଲରେ ପହଞ୍ଚନ୍ତୁ — ଆଶ୍ରୟ, ଖାଦ୍ୟ ଏବଂ ପ୍ରାଥମିକ ଚିକିତ୍ସା ପ୍ରସ୍ତୁତ",
        btnMap: "ଲାଇଭ ମ୍ୟାପ୍ ଖୋଲନ୍ତୁ",
        numHeading: "ଜରୁରୀକାଳୀନ ନମ୍ବର"
    }
};

document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    renderNtroIncidents();
    renderCmdZones();
    selectZone('angul');
    selectNtroIncident('INC-2846');
});

// Portal Switching
function switchPortal(portalName) {
    currentPortal = portalName;
    const portals = ['ntro', 'command', 'citizen'];
    portals.forEach(p => {
        const el = document.getElementById(`portal-${p}`);
        const tab = document.getElementById(`tab-${p}`);
        if (p === portalName) {
            el.classList.remove('hidden');
            tab.className = "flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-sm border border-slate-200/80 dark:border-slate-700 transition-all font-bold";
        } else {
            el.classList.add('hidden');
            tab.className = "flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-all font-semibold";
        }
    });

    const footerLabel = document.getElementById('txt-footer-portal-label');
    if (portalName === 'ntro') footerLabel.textContent = "NTRO Intelligence Portal";
    else if (portalName === 'command') footerLabel.textContent = "Government Command Dashboard";
    else footerLabel.textContent = "Citizen Services Portal";

    lucide.createIcons();
}

// Theme Switching
function setTheme(mode) {
    const html = document.documentElement;
    const btnLight = document.getElementById('theme-light');
    const btnDark = document.getElementById('theme-dark');
    const btnSystem = document.getElementById('theme-system');

    [btnLight, btnDark, btnSystem].forEach(b => {
        b.className = "px-2 py-0.5 rounded flex items-center gap-1 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white";
    });

    if (mode === 'dark') {
        html.classList.add('dark');
        btnDark.className = "px-2 py-0.5 rounded flex items-center gap-1 bg-slate-700 text-white font-semibold";
    } else if (mode === 'light') {
        html.classList.remove('dark');
        btnLight.className = "px-2 py-0.5 rounded flex items-center gap-1 bg-white shadow-xs text-slate-900 font-semibold";
    } else {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (prefersDark) html.classList.add('dark');
        else html.classList.remove('dark');
        btnSystem.className = "px-2 py-0.5 rounded flex items-center gap-1 bg-slate-200 dark:bg-slate-700 text-slate-900 dark:text-white font-semibold";
    }
}

// Language Switching
function setLanguage(lang) {
    currentLanguage = lang;
    ['en', 'hi', 'od'].forEach(l => {
        const btn = document.getElementById(`lang-${l}`);
        if (l === lang) {
            btn.className = "px-2.5 py-1 rounded bg-white text-slate-900 font-bold shadow-xs";
        } else {
            btn.className = "px-2.5 py-1 rounded text-slate-300 hover:text-white";
        }
    });

    const t = translations[lang];
    if (!t) return;

    document.getElementById('txt-citizen-title').textContent = t.title;
    document.getElementById('txt-citizen-subtitle').textContent = t.subtitle;
    document.getElementById('txt-sos-btn').textContent = t.sosBtn;
    document.getElementById('txt-alerts-heading').textContent = t.alertsHeading;
    document.getElementById('txt-alert-1').textContent = t.alert1;
    document.getElementById('txt-alert-2').textContent = t.alert2;
    document.getElementById('txt-alert-3').textContent = t.alert3;
    document.getElementById('txt-services-heading').textContent = t.servicesHeading;
    document.getElementById('txt-srv-shelter').textContent = t.shelter;
    document.getElementById('txt-srv-hospital').textContent = t.hospital;
    document.getElementById('txt-srv-food').textContent = t.food;
    document.getElementById('txt-srv-bus').textContent = t.bus;
    document.getElementById('txt-srv-fuel').textContent = t.fuel;
    document.getElementById('txt-srv-helpline').textContent = t.helpline;
    document.getElementById('txt-route-heading').textContent = t.routeHeading;
    document.getElementById('txt-step-1').innerHTML = t.step1;
    document.getElementById('txt-step-2').innerHTML = t.step2;
    document.getElementById('txt-step-3').innerHTML = t.step3;
    document.getElementById('txt-btn-map').textContent = t.btnMap;
    document.getElementById('txt-num-heading').textContent = t.numHeading;
}

// Render NTRO Incidents
function renderNtroIncidents() {
    const list = document.getElementById('ntro-incident-list');
    list.innerHTML = '';

    const filtered = currentNtroFilter === 'all' ? ntroIncidents : ntroIncidents.filter(i => i.category === currentNtroFilter);
    document.getElementById('ntro-log-count').textContent = `${filtered.length} events`;

    filtered.forEach(inc => {
        const isSelected = inc.id === selectedNtroId;
        const div = document.createElement('div');
        div.className = `p-3 rounded-lg border text-xs cursor-pointer transition-all ${isSelected ? 'border-blue-500 bg-blue-50/40 dark:bg-blue-950/20' : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'}`;
        div.onclick = () => selectNtroIncident(inc.id);

        const sevBadge = inc.severity === 'CRITICAL' ? 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300' :
                         inc.severity === 'HIGH' ? 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300' :
                         inc.severity === 'ALERT' ? 'bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300' :
                         inc.severity === 'MODERATE' ? 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300' :
                         'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300';

        div.innerHTML = `
            <div class="flex items-center justify-between font-mono text-[11px] text-slate-400">
                <span>${inc.id} &bull; ${inc.time}</span>
                <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${sevBadge}">${inc.severity}</span>
            </div>
            <div class="text-xs font-bold text-slate-900 dark:text-white mt-1">${inc.location}</div>
            <div class="flex items-center justify-between text-[11px] mt-0.5">
                <span class="text-blue-600 dark:text-blue-400 font-medium">${inc.label}</span>
                <span class="text-slate-400 font-mono">${inc.confidence}% confidence</span>
            </div>
        `;
        list.appendChild(div);
    });
}

function selectNtroIncident(id) {
    selectedNtroId = id;
    const inc = ntroIncidents.find(i => i.id === id);
    if (!inc) return;

    renderNtroIncidents();

    document.getElementById('ntro-facility-tag').textContent = inc.facility;
    document.getElementById('ntro-detail-title').textContent = inc.location;
    document.getElementById('ntro-detail-coords').textContent = inc.coords;
    document.getElementById('ntro-detail-severity').textContent = inc.severity;
    document.getElementById('ntro-detail-class').textContent = inc.label;
    document.getElementById('ntro-detail-confidence').textContent = `${inc.confidence}%`;
    document.getElementById('ntro-detail-temp').textContent = inc.temp;
    document.getElementById('ntro-detail-area').textContent = inc.area;
    document.getElementById('ntro-detail-source').textContent = inc.source;
    document.getElementById('ntro-detail-match').textContent = inc.matchText;
}

function filterNtro(cat) {
    currentNtroFilter = cat;
    ['all', 'industrial', 'wildfire', 'gas-flare', 'crop-burning', 'illegal'].forEach(c => {
        const btn = document.getElementById(`btn-ntro-${c}`);
        if (c === cat) {
            btn.className = "px-3 py-1 rounded-md bg-blue-600 text-white shadow-xs font-semibold";
        } else {
            btn.className = "px-3 py-1 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 font-semibold";
        }
    });
    renderNtroIncidents();
}

// Render Government Command Zones
function renderCmdZones() {
    const list = document.getElementById('cmd-zone-list');
    list.innerHTML = '';

    cmdZones.forEach(z => {
        const isSelected = z.id === selectedZoneId;
        const div = document.createElement('div');
        div.className = `p-3 rounded-lg border text-xs cursor-pointer transition-all ${isSelected ? 'border-blue-500 bg-blue-50/40 dark:bg-blue-950/20' : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'}`;
        div.onclick = () => selectZone(z.id);

        const sevBadge = z.severity === 'CRITICAL' ? 'text-red-600 dark:text-red-400 font-bold' :
                         z.severity === 'HIGH' ? 'text-amber-600 dark:text-amber-400 font-bold' :
                         z.severity === 'ALERT' ? 'text-orange-600 dark:text-orange-400 font-bold' :
                         'text-blue-600 dark:text-blue-400 font-bold';

        div.innerHTML = `
            <div class="flex items-center justify-between">
                <span class="font-bold text-slate-900 dark:text-white text-xs">${z.name}</span>
                <span class="font-mono text-[10px] uppercase ${sevBadge}">${z.severity}</span>
            </div>
            <div class="flex items-center justify-between text-[11px] mt-1 text-slate-500">
                <span class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium">${z.type}</span>
                <span class="font-mono">${z.deployedText}</span>
            </div>
        `;
        list.appendChild(div);
    });
}

function selectZone(id) {
    selectedZoneId = id;
    const z = cmdZones.find(item => item.id === id);
    if (!z) return;

    renderCmdZones();

    document.getElementById('cmd-sel-name').textContent = z.name;
    document.getElementById('cmd-sel-type-pill').textContent = z.type;
    document.getElementById('cmd-sel-severity-pill').textContent = z.severity;
    document.getElementById('cmd-sel-pop').textContent = z.pop;
    document.getElementById('cmd-sel-teams').textContent = z.teamsCount;
    document.getElementById('cmd-sel-type').textContent = z.type;
    document.getElementById('res-ndrf-bar').style.width = `${z.ndrfPercent}%`;
}

function dispatchTeam() {
    const z = cmdZones.find(item => item.id === selectedZoneId);
    if (!z) return;

    if (z.deployedNum < z.maxTeams) {
        z.deployedNum++;
        z.teamsCount = `${z.deployedNum} / ${z.maxTeams}`;
        z.deployedText = `${z.deployedNum}/${z.maxTeams} teams deployed`;
        z.ndrfPercent = Math.min(100, z.ndrfPercent + 15);

        // Update overall teams counter
        const teamsEl = document.getElementById('cmd-stat-teams');
        const currentTotal = parseInt(teamsEl.textContent, 10);
        teamsEl.textContent = currentTotal + 1;

        selectZone(selectedZoneId);

        const btn = document.getElementById('btn-dispatch');
        btn.innerHTML = `<i data-lucide="check" class="w-3.5 h-3.5"></i> <span>Dispatched!</span>`;
        btn.className = "px-5 py-2 bg-emerald-600 text-white rounded-lg font-bold text-xs shadow-sm transition-all flex items-center gap-1.5";
        lucide.createIcons();

        setTimeout(() => {
            btn.innerHTML = `<i data-lucide="send" class="w-3.5 h-3.5"></i> <span>Dispatch Team</span>`;
            btn.className = "px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold text-xs shadow-sm transition-all flex items-center gap-1.5";
            lucide.createIcons();
        }, 2000);

        alert(`✅ Unit Dispatched: NDRF Team #${z.deployedNum} successfully dispatched to ${z.name}!`);
    } else {
        alert(`Maximum allocated teams (${z.maxTeams}) already deployed to ${z.name}!`);
    }
}

function triggerQuickAction(msg) {
    alert(`⚡ ACTION EXECUTED: ${msg}`);
}

// SOS Modal logic
function openSosModal() {
    document.getElementById('sos-form').classList.remove('hidden');
    document.getElementById('sos-success').classList.add('hidden');
    document.getElementById('sosModal').classList.remove('hidden');
    lucide.createIcons();
}

function closeSosModal() {
    document.getElementById('sosModal').classList.add('hidden');
}

let selectedSosTypeStr = '';
function selectSosType(btn, type) {
    selectedSosTypeStr = type;
    document.querySelectorAll('.sos-opt-btn').forEach(b => {
        b.className = "sos-opt-btn p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-left font-semibold text-slate-700 dark:text-slate-200 hover:border-red-500 flex items-center gap-2";
    });
    btn.className = "sos-opt-btn p-2.5 rounded-lg border-2 border-red-500 bg-red-50/50 dark:bg-red-950/40 text-left font-bold text-red-600 dark:text-red-400 flex items-center gap-2";
}

function submitSos() {
    document.getElementById('sos-form').classList.add('hidden');
    document.getElementById('sos-success').classList.remove('hidden');
}

// Cross-Portal Simulation
function triggerSatellitePass() {
    const alertPill = document.getElementById('cmd-active-alert-pill');
    alertPill.textContent = "4 Critical Incidents Active";
    alertPill.className = "text-red-600 dark:text-red-400 font-bold animate-pulse";

    document.getElementById('ntro-hotspots-count').textContent = "248";
    document.getElementById('ntro-critical-count').textContent = "4";

    alert("🛰️ NASA FIRMS Pass Completed:\nNew Thermal Anomaly Ingested: INC-2847 in Similipal Reserve (710°C).\nCommand Center alert counter updated!");
}
