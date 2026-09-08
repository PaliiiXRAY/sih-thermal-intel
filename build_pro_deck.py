"""
AeroThermal SIH26162 — Professional Deck Builder
Design system: "Mission Control" — deep navy + ember orange, consistent type scale,
real live-product screenshots. 16:9.
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(BASE, "assets", "screenshots")

# ---- palette ----
NAVY      = RGBColor(0x0B, 0x1B, 0x33)
NAVY_2    = RGBColor(0x10, 0x2A, 0x4C)
INK       = RGBColor(0x1E, 0x29, 0x3B)
SLATE     = RGBColor(0x64, 0x74, 0x8B)
MIST      = RGBColor(0xF1, 0xF5, 0xF9)
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
EMBER     = RGBColor(0xF9, 0x73, 0x16)
AMBER     = RGBColor(0xFB, 0xBF, 0x24)
RED       = RGBColor(0xDC, 0x26, 0x26)
BLUE      = RGBColor(0x25, 0x63, 0xEB)
GREEN     = RGBColor(0x05, 0x96, 0x69)

FONT = "Segoe UI"
MONO = "Consolas"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
W, H = prs.slide_width, prs.slide_height

def slide():
    return prs.slides.add_slide(BLANK)

def rect(s, x, y, w, h, fill, line=None, shadow=False, round_=False):
    shp = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if round_ else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h))
    if round_:
        try: shp.adjustments[0] = 0.08
        except Exception: pass
    shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line: shp.line.color.rgb = line; shp.line.width = Pt(1)
    else: shp.line.fill.background()
    shp.shadow.inherit = False
    return shp

def txt(s, x, y, w, h, text, size=14, color=INK, bold=False, font=FONT,
        align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line_spacing=1.0, wrap=True):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        r = p.add_run(); r.text = ln
        r.font.size = Pt(size); r.font.bold = bold; r.font.name = font
        r.font.color.rgb = color
    return tb

def bullets(s, x, y, w, items, size=13, color=INK, gap=6, marker="•", mcolor=EMBER, bold_first=False):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(0.4 + 0.32 * len(items)))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        r1 = p.add_run(); r1.text = marker + "  "
        r1.font.size = Pt(size); r1.font.color.rgb = mcolor; r1.font.bold = True; r1.font.name = FONT
        r2 = p.add_run(); r2.text = it
        r2.font.size = Pt(size); r2.font.color.rgb = color; r2.font.name = FONT
    return tb

def header(s, kicker, title, n):
    """Standard light slide header with page number."""
    rect(s, 0, 0, 13.333, 0.10, EMBER)
    txt(s, 0.6, 0.38, 9.5, 0.3, kicker.upper(), size=11, color=EMBER, bold=True, font=MONO)
    txt(s, 0.6, 0.68, 11.5, 0.65, title, size=26, color=NAVY, bold=True)
    txt(s, 12.35, 0.42, 0.6, 0.3, f"{n:02d}", size=12, color=SLATE, bold=True, font=MONO, align=PP_ALIGN.RIGHT)
    rect(s, 0.6, 1.52, 1.1, 0.045, EMBER)

def chip(s, x, y, w, label, fill, tcolor=WHITE, size=10.5, h=0.34):
    rect(s, x, y, w, h, fill, round_=True)
    txt(s, x, y + (h - 0.22) / 2, w, 0.24, label, size=size, color=tcolor, bold=True,
        font=MONO, align=PP_ALIGN.CENTER, wrap=False)

def shot_card(s, path, x, y, w, caption):
    """Screenshot in a framed card with a caption bar."""
    cap_h = 0.42
    border = 0.05
    img_h = w * 0.5625  # 1600x900 screenshots
    total_h = img_h + cap_h + border * 2
    rect(s, x - 0.06, y - 0.06, w + 0.12, total_h + 0.12, WHITE, line=RGBColor(0xE2, 0xE8, 0xF0), round_=True)
    s.shapes.add_picture(path, Inches(x), Inches(y), width=Inches(w))
    rect(s, x, y + img_h + border, w, cap_h, NAVY)
    txt(s, x + 0.15, y + img_h + border + 0.09, w - 0.3, 0.26, caption, size=10.5, color=WHITE, bold=True, font=MONO)
    return total_h

# ================= SLIDE 1 — TITLE =================
s = slide()
rect(s, 0, 0, 13.333, 7.5, NAVY)
rect(s, 0, 0, 13.333, 7.5, NAVY_2)  # subtle two-tone
rect(s, 0, 7.34, 13.333, 0.16, EMBER)
# faint grid dots suggestion: a few thin lines
for i in range(6):
    rect(s, 0.7 + i * 2.2, 0.55, 0.012, 0.5, RGBColor(0x1E, 0x3A, 0x5F))
txt(s, 0.7, 0.55, 9.0, 0.35, "SMART INDIA HACKATHON 2026  •  NTRO  •  PROBLEM STATEMENT SIH26162",
    size=12, color=EMBER, bold=True, font=MONO)
txt(s, 0.7, 1.65, 11.9, 1.9, "AeroThermal", size=72, color=WHITE, bold=True)
txt(s, 0.7, 3.05, 11.5, 1.0,
    "AI-Based Detection & Classification of Industrial Fires and\nPersistent Thermal Sources",
    size=24, color=RGBColor(0xCB, 0xD5, 0xE1), line_spacing=1.15)
chip(s, 0.7, 4.45, 2.35, "NASA FIRMS", RGBColor(0x1E, 0x3A, 0x5F), tcolor=WHITE)
chip(s, 3.20, 4.45, 2.35, "OSM + WORLDCOVER", RGBColor(0x1E, 0x3A, 0x5F), tcolor=WHITE)
chip(s, 5.70, 4.45, 2.35, "TEMPORAL AI", RGBColor(0x1E, 0x3A, 0x5F), tcolor=WHITE)
chip(s, 8.20, 4.45, 2.35, "GIS OVERLAY", RGBColor(0x1E, 0x3A, 0x5F), tcolor=WHITE)
rect(s, 0.7, 5.35, 12.0, 0.012, RGBColor(0x1E, 0x3A, 0x5F))
txt(s, 0.7, 5.6, 6.6, 1.2,
    "Team Name: [Your Team]\n1. [Lead] Full-Stack & Geospatial   2. [Name] ML / Classification\n3. [Name] GIS & Mapping   4. [Name] Backend & APIs\n5. [Name] Frontend & UX   6. [Name] Pitch & Research",
    size=12.5, color=RGBColor(0x94, 0xA3, 0xB8), line_spacing=1.25)
txt(s, 8.2, 5.6, 4.4, 1.2,
    "LIVE PLATFORM\nsih-thermal-intel.vercel.app",
    size=13, color=WHITE, bold=True, font=MONO, align=PP_ALIGN.RIGHT, line_spacing=1.4)

# ================= SLIDE 2 — PROBLEM =================
s = slide()
header(s, "The Operational Gap", "To a satellite, every fire is just a glowing pixel", 2)
# left: problem narrative card
rect(s, 0.6, 1.75, 6.0, 4.9, MIST, round_=True)
txt(s, 0.95, 2.05, 5.3, 0.4, "WHAT FIRMS GIVES US TODAY", size=12, color=NAVY, bold=True, font=MONO)
bullets(s, 0.95, 2.55, 5.35, [
    "NASA FIRMS detects thousands of thermal anomalies across India daily (VIIRS 375m / MODIS 1km).",
    "It reports WHERE and HOW HOT — never WHAT: a refinery flare, a stubble fire, a wildfire, or an illegal kiln look identical.",
    "Responders waste hours on false alarms; clandestine industrial activity goes unnoticed.",
    "No industrial-vs-natural segregation exists in any current open system — this is the exact PS 26162 gap.",
], size=13.5, color=INK, gap=10)
# right: consequence stack
cards = [
    ("WILDFIRE?", RED, "Misclassified → delayed NDRF response, forest loss"),
    ("GAS FLARE?", EMBER, "False industrial alarm → wasted inspection crews"),
    ("STUBBLE BURN?", BLUE, "Seasonal smoke → city air-quality crisis misattributed"),
    ("CLANDESTINE?", RGBColor(0x7C, 0x2D, 0x12), "Unregistered plant → national-security blind spot"),
]
y = 1.75
for label, c, desc in cards:
    rect(s, 7.0, y, 5.75, 1.06, WHITE, line=RGBColor(0xE2, 0xE8, 0xF0), round_=True)
    rect(s, 7.0, y, 0.09, 1.06, c)
    txt(s, 7.3, y + 0.13, 1.9, 0.3, label, size=13, color=c, bold=True, font=MONO)
    txt(s, 9.05, y + 0.13, 3.6, 0.85, desc, size=11, color=SLATE, line_spacing=1.1)
    txt(s, 7.3, y + 0.5, 1.75, 0.4, "same pixel", size=10.5, color=SLATE, font=MONO, wrap=False)
    y += 1.24
txt(s, 7.0, y + 0.02, 5.75, 0.4, "One thermal signature. Four completely different responses.",
    size=13, color=NAVY, bold=True, align=PP_ALIGN.CENTER)

# ================= SLIDE 3 — SOLUTION =================
s = slide()
header(s, "Proposed Solution", "From ambiguous heat pixels to action", 3)
cols = [
    ("1. DETECT & INGEST", BLUE, [
        "NASA FIRMS NRT feed: VIIRS SNPP / NOAA-20 (375m), MODIS (1km)",
        "FRP, brightness temperature, confidence, pass timestamps",
        "Live-key ingestion + curated scenario replay",
    ]),
    ("2. CONTEXTUALIZE", EMBER, [
        "OpenStreetMap Overpass: refineries, flare stacks, power, mining",
        "ESA WorldCover land-cover class per hotspot pixel",
        "60-day persistence baseline for the exact 375m cell",
    ]),
    ("3. CLASSIFY & EXPLAIN", RED, [
        "7-class taxonomy with confidence % and evidence panel",
        "Persistence separates stationary flares from transient fires",
        "Counter-evidence shown honestly for analyst review",
    ]),
    ("4. ACT & TRACK", GREEN, [
        "GIS overlay with evidence dossiers per hotspot",
        "Risk engine: population, highways, hospitals, downwind zone",
        "Incident lifecycle → agency dispatch → resolution tracking",
    ]),
]
x = 0.6
for title, c, items in cols:
    rect(s, x, 1.85, 2.95, 3.5, WHITE, line=RGBColor(0xE2, 0xE8, 0xF0), round_=True)
    rect(s, x, 1.85, 2.95, 0.5, c, round_=True)
    txt(s, x + 0.18, 1.96, 2.6, 0.3, title, size=12.5, color=WHITE, bold=True, font=MONO)
    bullets(s, x + 0.22, 2.6, 2.55, items, size=13, color=INK, gap=14, marker="—", mcolor=c)
    x += 3.11

# ================= SLIDE 4 — ARCHITECTURE =================
s = slide()
header(s, "Technical Architecture", "End-to-end pipeline — all free & open data", 4)
nodes = [
    ("NASA FIRMS\nVIIRS/MODIS NRT", BLUE),
    ("OSM OVERPASS\nfacilities & land-use", EMBER),
    ("ESA WORLDCOVER\nland-cover class", GREEN),
    ("PERSISTENCE ENGINE\n60-day recurrence", AMBER),
    ("AI CLASSIFIER\n7 classes + evidence", RED),
    ("GIS OVERLAY\nLeaflet + dispatch", NAVY_2),
]
x = 0.55
y = 2.3
for i, (label, c) in enumerate(nodes):
    rect(s, x, y, 1.85, 1.25, WHITE, line=c, round_=True)
    rect(s, x, y, 1.85, 0.14, c, round_=False)
    txt(s, x + 0.08, y + 0.3, 1.7, 0.85, label, size=11, color=INK, bold=True, align=PP_ALIGN.CENTER, line_spacing=1.12)
    if i < len(nodes) - 1:
        ar = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + 1.87), Inches(y + 0.5), Inches(0.28), Inches(0.26))
        ar.fill.solid(); ar.fill.fore_color.rgb = SLATE; ar.line.fill.background(); ar.shadow.inherit = False
    x += 2.11
# data-flow strip below
rect(s, 0.55, 4.15, 12.25, 1.55, MIST, round_=True)
txt(s, 0.85, 4.35, 4.0, 0.3, "EVERY HOTSPOT CARRIES A FULL DOSSIER", size=11.5, color=NAVY, bold=True, font=MONO)
txt(s, 0.85, 4.72, 11.7, 0.9,
    "FIRMS metrics (FRP 88.4 MW • 85°C • 22.358°N 69.831°E)  +  facility match (Jamnagar Refinery, 120 m)  +  persistence (80%, 48/60 passes)  +  land-cover (Built-up)  →  CLASSIFICATION: INDUSTRIAL GAS FLARE, 94% confidence, with recommended action routed to the right agency.",
    size=12, color=INK, line_spacing=1.25)
txt(s, 0.85, 5.95, 11.7, 0.9,
    "Stack: Python stdlib server + REST API  •  Vercel serverless  •  Leaflet GIS  •  GeoJSON export  •  Zero paid services, zero API keys required for demo mode.",
    size=12, color=SLATE, line_spacing=1.25)

# ================= SLIDE 5 — LIVE PRODUCT: NTRO =================
s = slide()
header(s, "Live Product — NTRO Intelligence Portal", "GIS overlay with evidence dossiers — live", 5)
h = shot_card(s, os.path.join(SHOTS, "ntro_pipeline.png"), 0.6, 1.8, 7.6,
              "LIVE: Jamnagar refinery flare auto-classified, 94% confidence")
bullets(s, 8.55, 1.95, 4.2, [
    "Real Leaflet map: hotspots colored by class with pop-up evidence",
    "Pipeline runs FIRMS → OSM → persistence → WorldCover → class",
    "Evidence dossier: facility match, distance, persistence %, land-cover",
    "Live OSM toggle queries Overpass API in real time",
    "5 operational Indian scenarios + live FIRMS-key mode",
], size=12.5, color=INK, gap=9)

# ================= SLIDE 6 — TAXONOMY =================
s = slide()
header(s, "Classification Taxonomy", "Seven classes — persistence × context, not guesswork", 6)
classes = [
    ("INDUSTRIAL GAS FLARE", EMBER, "Persistent + inside refinery boundary", "MoEFCC emission log", 94),
    ("POWER PLANT / COAL FIRE", AMBER, "Persistent + power-station tag", "Plant safety + utility", 94),
    ("STEEL / SMELTER", AMBER, "Persistent + metallurgical facility", "Pollution control board", 94),
    ("MINING / COAL STOCKYARD", AMBER, "Persistent + quarry land-cover", "Indian Bureau of Mines", 94),
    ("WILDFIRE", RED, "High FRP + tree cover + episodic spread", "Forest Dept + NDRF", 91),
    ("STUBBLE BURNING", BLUE, "Transient cluster + cropland + season", "CAQM / CPCB alert", 88),
    ("CLANDESTINE ANOMALY", RGBColor(0x7C, 0x2D, 0x12), "High persistence + NO registered facility", "NTRO / UAV recon", 88),
]
y = 1.78
for name, c, logic, route, conf in classes:
    rect(s, 0.6, y, 12.15, 0.6, WHITE, line=RGBColor(0xE2, 0xE8, 0xF0), round_=True)
    rect(s, 0.6, y, 0.09, 0.6, c)
    txt(s, 0.85, y + 0.16, 3.1, 0.3, name, size=12, color=c, bold=True, font=MONO, wrap=False)
    txt(s, 4.05, y + 0.17, 4.1, 0.3, logic, size=11.5, color=INK, wrap=False)
    txt(s, 8.25, y + 0.17, 3.1, 0.3, "→ " + route, size=11.5, color=SLATE, wrap=False)
    txt(s, 11.6, y + 0.16, 1.0, 0.3, f"{conf}%", size=12, color=c, bold=True, font=MONO, align=PP_ALIGN.RIGHT, wrap=False)
    y += 0.7

# ================= SLIDE 7 — COMMAND PORTAL =================
s = slide()
header(s, "Live Product — Government Command", "Incident lifecycle state machine & dispatch", 7)
h = shot_card(s, os.path.join(SHOTS, "command_tracker_crop.png"), 0.6, 1.8, 6.3,
              "LIVE: incidents NEW → INVESTIGATING → … → RESOLVED with authority routing")
bullets(s, 8.55, 1.95, 4.2, [
    "Six-stage state machine backed by REST API + server persistence",
    "One-click dispatch routes to the correct jurisdiction (fire, GPCB, NDRF, DM)",
    "Assets-at-risk engine: population, NH corridors, hospitals, downwind corridor",
    "Citizen Reports Inbox: crowd reports cross-checked vs FIRMS before acting",
], size=12.5, color=INK, gap=9)

# ================= SLIDE 8 — CITIZEN LOOP =================
s = slide()
header(s, "Live Product — Citizen Services", "Citizen eyes + satellite brain", 8)
h = shot_card(s, os.path.join(SHOTS, "citizen_map.png"), 0.6, 1.8, 7.6,
              "LIVE: evacuation map — incident zone, safe shelter, NH-55 route")
bullets(s, 8.55, 1.95, 4.2, [
    "Multilingual portal (English / Hindi / Odia) with SOS escalation",
    "Crowdsourced smoke/fire reports with GPS attach",
    "Reports land in the Command inbox for FIRMS cross-check",
    "Offline SMS fallback: HELP <PINCODE> → 1078 (zero-data ready)",
], size=12.5, color=INK, gap=9)

# ================= SLIDE 9 — IMPACT =================
s = slide()
header(s, "National Impact", "Value for every PS stakeholder", 9)
imp = [
    ("NTRO & DEFENCE", NAVY, [
        "Clandestine thermal facility flagging in non-industrial zones",
        "Persistent-source monitoring grid for critical infrastructure",
    ]),
    ("DISASTER MGMT (NDRF/SDMA)", RED, [
        "Wildfire alerts within one satellite pass (~15 min)",
        "Assets-at-risk + downwind corridor pre-computed for responders",
    ]),
    ("AIR QUALITY (CAQM/CPCB)", BLUE, [
        "Stubble-burn clusters separated from industrial flares — no false industrial blame",
        "Season-adjusted seasonal burning statistics",
    ]),
    ("ENVIRONMENT (MoEFCC)", GREEN, [
        "Automatic flare-recurrence logs vs permits for every registered plant",
        "Audit-ready evidence trail from satellite to action",
    ]),
]
x = 0.6
for title, c, items in imp:
    rect(s, x, 1.85, 2.95, 3.1, WHITE, line=RGBColor(0xE2, 0xE8, 0xF0), round_=True)
    rect(s, x, 1.85, 2.95, 0.09, c)
    txt(s, x + 0.2, 2.1, 2.55, 0.6, title, size=12, color=c, bold=True, font=MONO)
    bullets(s, x + 0.2, 2.75, 2.55, items, size=13, color=INK, gap=16, marker="—", mcolor=c)
    x += 3.11
rect(s, 0.6, 6.7, 12.15, 0.5, MIST, round_=True)
txt(s, 0.6, 6.81, 12.15, 0.3, "Zero-cost open data  •  Deploys anywhere  •  Works today at sih-thermal-intel.vercel.app",
    size=12.5, color=NAVY, bold=True, align=PP_ALIGN.CENTER)

# ================= SLIDE 10 — HONEST LIMITATIONS =================
s = slide()
header(s, "Scientific Rigor", "What we prove — and what we honestly cannot", 10)
rect(s, 0.6, 1.8, 6.0, 4.9, RGBColor(0xEC, 0xFD, 0xF5), round_=True)
txt(s, 0.95, 2.05, 5.3, 0.4, "✔  SCIENTIFICALLY PROVEN", size=12.5, color=GREEN, bold=True, font=MONO)
bullets(s, 0.95, 2.55, 5.35, [
    "Temporal persistence cleanly separates stationary flares from transient fires (48/60 vs 1-2/60 passes).",
    "Facility + land-cover context resolves flare vs kiln vs wildfire at district scale.",
    "Every classification ships with evidence AND counter-evidence for analyst verification.",
    "Deterministic, explainable rules — no black box, auditable by NTRO.",
], size=12.5, color=INK, gap=10, marker="✔", mcolor=GREEN)
rect(s, 7.0, 1.8, 5.75, 4.9, RGBColor(0xFF, 0xF7, 0xED), round_=True)
txt(s, 7.35, 2.05, 5.1, 0.4, "⚠  HONEST LIMITATIONS", size=12.5, color=EMBER, bold=True, font=MONO)
bullets(s, 7.35, 2.55, 5.1, [
    "VIIRS resolution ceiling (375m–1km): exact facility attribution is probabilistic in dense industrial clusters.",
    "Ground-truth labels are scarce; land-cover is used as validation proxy.",
    "Fires co-locating with normal flares (refinery fire vs routine flare) need optical confirmation (Sentinel-2 on roadmap).",
    "Demo data: curated scenarios + live FIRMS; persistence archive grows with each pass.",
], size=12.5, color=INK, gap=10, marker="⚠", mcolor=EMBER)

# ================= SLIDE 11 — ROADMAP =================
s = slide()
header(s, "Deployment Roadmap", "From working MVP today to national grid", 11)
phases = [
    ("PHASE 1 — DONE TODAY", GREEN, [
        "Full classification pipeline + 7-class taxonomy (live)",
        "3-portal platform on Vercel with server persistence",
        "Live FIRMS key ingestion + Overpass + WorldCover",
        "Incident lifecycle, dispatch, citizen reporting loop",
    ]),
    ("PHASE 2 — 6 MONTHS", EMBER, [
        "Sentinel-2 20m SWIR optical validation layer",
        "UAV reconnaissance tasking for clandestine flags",
        "PostGIS storage + multi-tenant agency accounts",
        "WhatsApp/SMS alert gateway for district officers",
    ]),
    ("PHASE 3 — NATIONAL", NAVY, [
        "24×7 national thermal defence surveillance grid",
        "Direct integration: NDRF, FSI, CPCB, state SDMA",
        "Predictive fire-risk modelling from persistence trends",
        "On-prem deployment for NTRO classified networks",
    ]),
]
x = 0.6
for title, c, items in phases:
    rect(s, x, 1.85, 3.95, 3.7, WHITE, line=RGBColor(0xE2, 0xE8, 0xF0), round_=True)
    rect(s, x, 1.85, 3.95, 0.5, c, round_=True)
    txt(s, x + 0.2, 1.96, 3.5, 0.3, title, size=12.5, color=WHITE, bold=True, font=MONO)
    bullets(s, x + 0.22, 2.6, 3.5, items, size=11.5, color=INK, gap=9, marker="—", mcolor=c)
    x += 4.12

# ================= SLIDE 12 — CLOSE =================
s = slide()
rect(s, 0, 0, 13.333, 7.5, NAVY)
rect(s, 0, 7.34, 13.333, 0.16, EMBER)
txt(s, 0.7, 1.0, 11.9, 0.4, "WHY AEROTHERMAL WINS", size=13, color=EMBER, bold=True, font=MONO)
txt(s, 0.7, 1.55, 11.9, 1.6,
    "Not a slide-ware prototype.\nA working national platform — live now.",
    size=36, color=WHITE, bold=True, line_spacing=1.15)
points = [
    ("DELIVERABLE 1", "Industrial fires segregated from forest/agricultural fires with explainable evidence — exactly as the PS demands."),
    ("DELIVERABLE 2", "GIS solution: classified hotspots as a live map overlay, with storage, dispatch and monitoring built in."),
    ("THE KILLER FEATURE", "Persistence-based clandestine detection — thermal infrastructure that doesn't officially exist, flagged for NTRO."),
]
y = 3.65
for k, v in points:
    txt(s, 0.7, y, 2.6, 0.35, k, size=12, color=EMBER, bold=True, font=MONO)
    txt(s, 3.5, y, 9.0, 0.7, v, size=15, color=RGBColor(0xCB, 0xD5, 0xE1), line_spacing=1.15)
    y += 0.95
rect(s, 0.7, 6.45, 12.0, 0.012, RGBColor(0x1E, 0x3A, 0x5F))
txt(s, 0.7, 6.65, 12.0, 0.4, "Live demo:  sih-thermal-intel.vercel.app   •   NASA FIRMS   •   OpenStreetMap   •   ESA WorldCover",
    size=13, color=WHITE, bold=True, font=MONO)

out = os.path.join(BASE, "AeroThermal_SIH26162_Pro_Design.pptx")
prs.save(out)
print("saved:", out, "| slides:", len(prs.slides.__iter__.__self__._sldIdLst))
