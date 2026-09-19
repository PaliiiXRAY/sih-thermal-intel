# FireSense design system

## Product character

FireSense is disaster-response intelligence software. It should feel precise,
calm, operational, premium, and information-dense without being cluttered.

It must not feel cyberpunk, a generic AI dashboard, crypto, gaming UI, neon
sci-fi, or glassmorphism-heavy.

## Shared visual rules

Every screen has one primary decision, supporting context, and quiet secondary
metadata. Never make every metric equally prominent.

- Use large type only for a page title, incident severity, or the primary
  decision.
- Prefer restrained surfaces, strong spacing, thin borders, and clear section
  hierarchy.
- Avoid excessive shadows, rounded containers, gradients, glowing borders,
  decorative icons, and equal-weight metric-card grids.
- Use status colour sparingly and never as the sole means of communicating a
  state.
- Preserve existing API contracts, incident IDs, lifecycle states, and Leaflet
  maps when implementing a portal.

## Foundations

### Colour

Light theme:

- Background: `#F7F7F5`
- Surface: `#FFFFFF`
- Primary text: `#111111`
- Secondary text: `#34383D`
- Muted text: `#555B61`
- Border: `#D5D7DA`
- Accent/action: `#F4511E`

Dark theme uses near-black surfaces, off-white primary text, muted secondary
text, and thermal orange for actions. Severity colours are semantic: critical
red, high amber/orange, moderate neutral amber, resolved green.

### Type and spacing

Use a compact operational sans-serif UI with tabular figures for IDs, times,
coordinates, scores, and telemetry. Keep metadata smaller and quieter than
decisions. Use a deliberate 4/8px spacing rhythm; favour 16–24px internal
spacing and 24–32px between major regions.

## Portal intent

### NTRO Intelligence

Question: “What thermal signals merit analyst attention, and why?”

The flagship screen prioritises active signals and a map, followed by a short
incident list. Selecting an incident opens a focused evidence dossier rather
than another card grid. The dossier may include satellite fields, classification
and confidence, persistence, geospatial context, risk, and analyst
verification. Evidence should be grouped by claim, not presented as raw metric
tiles.

Primary flow: signal queue → select incident → evidence dossier → analyst
verify or flag.

### Government Command

Question: “Which incidents require command attention and what is their
operational state?”

Use an active-incident queue leading to a command dossier. Surface the
lifecycle and operational actions: alert, acknowledge, assign, dispatch, and
status. Do not duplicate NTRO ML evidence; retain only context needed to make
a command decision.

Primary flow: active incidents → select incident → command dossier → action →
lifecycle.

### Responder Operations

Question: “I am in the field; what do I need to do next?”

This is a field terminal, not an analytics dashboard. Present the mission,
location, hazard and route context, then one unambiguous next action. Do not
show model score, confidence, FRP, persistence, or ML evidence.

### Citizen Services

Question: “How do I stay safe right now?”

Show only an active alert, immediate guidance, nearest shelter, safe route,
and SOS. Keep language clear, calm, localised, and accessible. Never expose
model scores, confidence, FRP, persistence, or other ML evidence.

## Implementation guardrails

- Work one portal at a time, beginning with NTRO Intelligence.
- Treat an approved Figma frame as the visual source of truth for layout,
  spacing, type, hierarchy, colour, and component composition.
- Do not rebuild the frontend, introduce a second portal implementation,
  migrate frameworks, replace Leaflet, or invent data.
- Before editing a portal, inspect its production entrypoint and rendered
  components. After editing, run tests, inspect the rendered responsive UI,
  then correct hierarchy, spacing, and typography issues.
