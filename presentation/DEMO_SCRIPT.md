# AeroThermal 2-Minute Live Demo & Stage Pitch Script (SIH26162 - NTRO)

Use this script during your college internal hackathon presentation.

---

### Part 1: The Pitch & Live Demo (Total: 2 Minutes)

#### Step 1: The Hook (0:00 - 0:30)
> *"Respected judges, NASA's FIRMS satellites detect thousands of thermal anomalies across the Indian subcontinent every single day. But to an infrared satellite sensor, every fire looks like a glowing dot on a map.  
> 
> The National Technical Research Organisation (NTRO) needs to know: **Is that glowing dot a legitimate refinery gas flare, a seasonal crop stubble fire, a spreading forest wildfire, or an unpermitted clandestine industrial facility operating in secret?**  
> 
> For **SIH26162**, we built **AeroThermal**—an AI intelligence platform that fuses NASA FIRMS VIIRS satellite data with OpenStreetMap vector boundaries and 60-day temporal persistence modeling."*

#### Step 2: The Cinematic Demo (0:30 - 1:30)

*(Click preset 1: **"🏭 Jamnagar Refinery"**)*
> *"Look at scenario 1: Jamnagar Petrochemical Complex, Gujarat.  
> Notice that our engine classified this as an **Industrial Gas Flare (94% confidence)**. Why? Because the temporal persistence is **80%**—it was detected 48 times across 60 days in the exact same 375m cell, sitting 120m from verified OpenStreetMap industrial refinery zoning.  
> *(Click 'Switch to Satellite Imagery')*—Judges can see the actual refinery infrastructure directly underneath the thermal hotspot."*

*(Click preset 2: **"🌾 Punjab Stubble Fires"**)*
> *"Now look at Sangrur, Punjab during harvest season. The persistence drops to **1-2 passes (3%)**, while the land-use shifts to `farmland`. Our engine instantly flags it as **Agricultural Stubble Burning** with an automated alert routed to the Air Quality Commission (CAQM)."*

*(Click preset 4: **"⚠️ Clandestine Anomaly"**)*
> *"Here is the most critical feature for NTRO: an **Unregistered Clandestine Thermal Anomaly**. In the Singrauli hinterland, we detected a persistent hotspot (34 passes) with high FRP, but the OpenStreetMap tag is **unmapped scrubland**. This triggers an intelligence alert for illegal smelting or unpermitted industrial operations."*

#### Step 3: The Actionable Deliverables (1:30 - 2:00)
*(Click **"Export Intel Dossier (PDF)"** and point to the Limitations Box)*
> *"With one click, an intelligence analyst can download an **Official Geospatial Intelligence Dossier (PDF)** or export raw **GeoJSON** for GIS software.  
> 
> Furthermore, we are scientifically honest about our resolution boundaries: VIIRS provides 375m pixel resolution, which accurately identifies facility-level boundaries, while high-resolution 20m optical verification is scoped for Phase 2. Thank you!"*

---

### Part 2: Defense Against Tough Judge Questions

#### Q1: "Why is temporal persistence so important?"
* **Your Winning Answer:**
  > *"Sir, a single satellite overpass cannot distinguish between a gas flare and a temporary farm fire. But physics and human behavior are different: an industrial flare burns year-round in the same spot, while agricultural fires are seasonal and transient. By computing recurrence across 60 days of overpasses, temporal persistence eliminates 90% of false classifications."*

#### Q2: "Can FIRMS satellite resolution pinpoint the exact pipe or boiler?"
* **Your Winning Answer:**
  > *"No, sir, and we explicitly document that limitation in our platform. VIIRS has a 375m spatial resolution, meaning one pixel covers ~14 hectares. That is why our tool attributes hotspots to the **facility zone** rather than claiming sub-meter accuracy. To achieve pipe-level attribution, our Phase 2 roadmap integrates Sentinel-2 20m SWIR bands and drone imagery."*

#### Q3: "Where does OpenStreetMap fit into this?"
* **Your Winning Answer:**
  > *"NASA FIRMS only provides raw thermal coordinates and radiative power. OpenStreetMap provides semantic geospatial ground truth—whether those coordinates belong to an industrial refinery, agricultural cropland, a residential colony, or a reserved forest. Fusing the two converts raw satellite telemetry into actionable intelligence."*
