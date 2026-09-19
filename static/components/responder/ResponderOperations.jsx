/**
 * ResponderOperations.jsx — First Responder Field Terminal
 * Incident ID, location, severity, assignment, lifecycle state machine.
 *
 * Buttons: ACKNOWLEDGE → EN ROUTE → ARRIVED → CONTAINED → RESOLVED
 * Invalid transitions disabled via backend transition table (Faizaan's schema).
 * Ground-verification notes attached to each state change.
 *
 * API Contract (Frozen — Aditya owns):
 *   GET  /api/incidents                      → { incidents: Incident[] }
 *   GET  /api/incidents/:id                  → Incident
 *   PATCH /api/incidents/:id/status          → StatusResponse (validates transitions)
 *   POST /api/incidents/:id/alert            → AlertResponse
 *   GET  /api/incidents/:id/responders       → { responders: Responder[] }
 *   GET  /api/incidents/:id/status-log       → { log: StatusLogEntry[] }
 *
 * Error handling:
 *   403 — Forbidden (not assigned / no permission)
 *   409 — Invalid transition (backend rejects)
 *   Network failure — graceful fallback with retry
 *
 * CONSTRAINT: UI must NEVER imply autonomous AI dispatch or that a
 * simulated alert reached a real government system.
 */
import React, { useState, useEffect, useCallback, useRef } from "react";

/* ─── Canonical Status Colors (shared across portals) ─── */
const STATUS_COLORS = {
  NEW: "bg-slate-500",
  INVESTIGATING: "bg-blue-500",
  VERIFIED: "bg-indigo-500",
  DISPATCHED: "bg-amber-500",
  ACKNOWLEDGED: "bg-orange-500",
  "EN ROUTE": "bg-orange-600",
  ARRIVED: "bg-orange-700",
  CONTAINED: "bg-red-600",
  RESOLVED: "bg-emerald-600",
};

/* ─── Responder State Machine Flow (Faizaan's transition table) ─── */
const RESPONDER_FLOW = [
  {
    key: "DISPATCHED",
    label: "Dispatched",
    icon: "📤",
    next: "ACKNOWLEDGED",
    actionLabel: "🫡 ACKNOWLEDGE DISPATCH",
    actionClass: "bg-amber-500 hover:bg-amber-600",
    desc: "Receive and acknowledge the dispatch order",
  },
  {
    key: "ACKNOWLEDGED",
    label: "Acknowledged",
    icon: "✓",
    next: "EN ROUTE",
    actionLabel: "🚒 MARK EN ROUTE",
    actionClass: "bg-blue-600 hover:bg-blue-700",
    desc: "Unit is departing base / staging area",
  },
  {
    key: "EN ROUTE",
    label: "En Route",
    icon: "🚗",
    next: "ARRIVED",
    actionLabel: "📍 CONFIRM ARRIVED ON SCENE",
    actionClass: "bg-orange-600 hover:bg-orange-700",
    desc: "Unit is traveling to incident location",
  },
  {
    key: "ARRIVED",
    label: "Arrived",
    icon: "📍",
    next: "CONTAINED",
    actionLabel: "🧯 REPORT CONTAINED",
    actionClass: "bg-red-600 hover:bg-red-700",
    desc: "Unit has arrived on scene, commencing operations",
  },
  {
    key: "CONTAINED",
    label: "Contained",
    icon: "🛡️",
    next: "RESOLVED",
    actionLabel: "✅ MARK RESOLVED",
    actionClass: "bg-emerald-600 hover:bg-emerald-700",
    desc: "Incident is under control, perimeter secured",
  },
  {
    key: "RESOLVED",
    label: "Resolved",
    icon: "✅",
    next: null,
    actionLabel: "MISSION COMPLETE",
    actionClass: "bg-emerald-700",
    desc: "All operations concluded, site handed over",
  },
];

/* ─── Transition Map (which states can transition to which) ─── */
const VALID_TRANSITIONS = {
  NEW: ["INVESTIGATING"],
  INVESTIGATING: ["VERIFIED"],
  VERIFIED: ["DISPATCHED"],
  DISPATCHED: ["ACKNOWLEDGED", "INVESTIGATING"],
  ACKNOWLEDGED: ["EN ROUTE"],
  "EN ROUTE": ["ARRIVED"],
  ARRIVED: ["CONTAINED"],
  CONTAINED: ["RESOLVED"],
  RESOLVED: [],
};

/* ─── Determine if a transition is valid ─── */
function isValidTransition(from, to) {
  const allowed = VALID_TRANSITIONS[from?.toUpperCase()];
  if (!allowed) return false;
  return allowed.includes(to?.toUpperCase());
}

/* ─── Get the next valid action for the current status ─── */
function getNextAction(currentStatus) {
  const normalized = (currentStatus || "DISPATCHED").toUpperCase();
  // Normalize pre-dispatch statuses for field view
  if (["NEW", "INVESTIGATING", "VERIFIED"].includes(normalized)) {
    return RESPONDER_FLOW[0]; // DISPATCHED
  }
  const idx = RESPONDER_FLOW.findIndex((s) => s.key === normalized);
  return idx >= 0 ? RESPONDER_FLOW[idx] : RESPONDER_FLOW[0];
}

/* ════════════════════════════════════════════════════════════════════
 * MAIN COMPONENT
 * ════════════════════════════════════════════════════════════════════ */
export default function ResponderOperations() {
  const [incidents, setIncidents] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedInc, setSelectedInc] = useState(null);
  const [statusLog, setStatusLog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // State machine
  const [currentStatus, setCurrentStatus] = useState("DISPATCHED");

  // Ground verification note
  const [groundNote, setGroundNote] = useState("");
  const [noteSubmitting, setNoteSubmitting] = useState(false);

  // Error handling
  const [transitionError, setTransitionError] = useState(null);

  // Polling ref
  const pollRef = useRef(null);

  /* ─── Fetch incidents ─── */
  const fetchIncidents = useCallback(async () => {
    try {
      const resp = await fetch("/api/incidents");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const list = Array.isArray(data.incidents)
        ? data.incidents
        : Object.values(data.incidents || {});
      setIncidents(list);
      setError(null);

      // Refresh selected incident
      if (selectedId) {
        const detail = await fetch(`/api/incidents/${selectedId}`);
        if (detail.ok) {
          const inc = await detail.json();
          setSelectedInc(inc);
          setCurrentStatus(inc.status || "DISPATCHED");
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  /* ─── Fetch status log ─── */
  const fetchStatusLog = useCallback(async (id) => {
    try {
      const resp = await fetch(`/api/incidents/${id}/status-log`);
      if (resp.ok) {
        const data = await resp.json();
        setStatusLog(data.log || []);
      }
    } catch {
      // Status log is optional, don't block on failure
    }
  }, []);

  /* ─── Select incident ─── */
  const selectIncident = useCallback(
    (id) => {
      setSelectedId(id);
      setTransitionError(null);
      // Fetch detail and update status
      fetch(`/api/incidents/${id}`)
        .then((r) => (r.ok ? r.json() : null))
        .then((inc) => {
          if (inc) {
            setSelectedInc(inc);
            setCurrentStatus(inc.status || "DISPATCHED");
          }
        })
        .catch(() => {});
      fetchStatusLog(id);
    },
    [fetchStatusLog]
  );

  /* ─── Poll for state sync ─── */
  useEffect(() => {
    fetchIncidents();
    pollRef.current = setInterval(fetchIncidents, 5000);
    return () => clearInterval(pollRef.current);
  }, [fetchIncidents]);

  /* ─── Auto-select first incident ─── */
  useEffect(() => {
    if (incidents.length > 0 && !selectedId) {
      selectIncident(incidents[0].id);
    }
  }, [incidents, selectedId, selectIncident]);

  /* ─── Advance Responder State ─── */
  const advanceState = async (targetStatus) => {
    if (!selectedId) return;

    // Client-side validation
    if (!isValidTransition(currentStatus, targetStatus)) {
      setTransitionError(
        `Invalid transition: ${currentStatus} → ${targetStatus}. ` +
          `Allowed: [${VALID_TRANSITIONS[currentStatus]?.join(", ") || "none"}]`
      );
      return;
    }

    setTransitionError(null);
    try {
      const resp = await fetch(`/api/incidents/${selectedId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: targetStatus,
          ground_note: groundNote || undefined,
          responder_id: "UNIT-001", // Canonical role
        }),
      });

      if (resp.status === 409) {
        const data = await resp.json();
        setTransitionError(
          data.error || "Invalid transition (server rejected)"
        );
        return;
      }
      if (resp.status === 403) {
        setTransitionError(
          "Forbidden: You are not assigned to this incident."
        );
        return;
      }
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.error || `HTTP ${resp.status}`);
      }

      // Success
      setCurrentStatus(targetStatus);
      setGroundNote("");
      fetchIncidents();
      fetchStatusLog(selectedId);
    } catch (err) {
      setTransitionError(`Network error: ${err.message}`);
    }
  };

  /* ─── Render state machine step indicators ─── */
  const renderStateMachine = () => {
    const normalized = currentStatus?.toUpperCase();
    const effectiveStatus =
      ["NEW", "INVESTIGATING", "VERIFIED"].includes(normalized)
        ? "DISPATCHED"
        : normalized;
    const curIdx = RESPONDER_FLOW.findIndex((s) => s.key === effectiveStatus);
    const safeIdx = curIdx >= 0 ? curIdx : 0;

    return (
      <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 text-center text-xs font-mono">
        {RESPONDER_FLOW.map((s, idx) => {
          const isPast = idx < safeIdx;
          const isCurrent = idx === safeIdx;
          let bg =
            "bg-slate-100 dark:bg-slate-800 text-slate-400 border border-slate-200 dark:border-slate-700";
          if (isPast)
            bg =
              "bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 font-bold";
          if (isCurrent)
            bg =
              "bg-orange-500 text-white font-black shadow-sm ring-2 ring-orange-500/30";

          return (
            <div
              key={s.key}
              className={`p-2 rounded-lg text-center ${bg} transition-all`}
            >
              <div className="text-[10px] uppercase font-bold tracking-wider">
                {isPast ? "✓ " : ""}
                {s.label}
              </div>
              <div className="text-[9px] mt-0.5 opacity-80">
                {isCurrent ? "ACTIVE NOW" : isPast ? "COMPLETED" : "PENDING"}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  /* ─── Get next valid action ─── */
  const nextAction = getNextAction(currentStatus);
  const canAdvance =
    nextAction &&
    nextAction.next &&
    isValidTransition(currentStatus, nextAction.next);

  /* ─── Render ─── */
  return (
    <div className="space-y-6">
      {/* Responder Header */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono font-bold tracking-wider text-orange-600 dark:text-orange-400 uppercase">
              <span className="animate-pulse">📡</span>
              <span>NDRF UNIT &bull; TACTICAL FIELD TERMINAL</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
              Responder Operations
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">
              Direct satellite telemetry, access corridors &amp; mission dispatch
              state.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <select
              value={selectedId || ""}
              onChange={(e) => selectIncident(e.target.value)}
              className="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white font-bold text-xs shadow-xs focus:ring-2 focus:ring-orange-500 outline-none"
            >
              <option value="">Select incident...</option>
              {incidents.map((inc) => (
                <option key={inc.id} value={inc.id}>
                  {inc.id} • {inc.location_name} ({inc.status || "NEW"})
                </option>
              ))}
            </select>
            <span className="px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs font-bold font-mono flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500" /> FIELD
              READY
            </span>
          </div>
        </div>
      </div>

      {/* Active Incident Tactical Card */}
      {selectedInc && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-3">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400 font-bold block">
                Assigned Mission
              </span>
              <h3 className="text-xl font-black text-slate-900 dark:text-white">
                {selectedInc.title || selectedInc.id}
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400">
                {selectedInc.location_name || ""}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 rounded-md bg-red-100 dark:bg-red-950/70 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-xs font-bold font-mono">
                {selectedInc.classification || "HAZARD"}
              </span>
              <span
                className={`px-2.5 py-1 rounded-md text-white text-xs font-black font-mono ${
                  (selectedInc.risk_score || 0) >= 70
                    ? "bg-red-600"
                    : (selectedInc.risk_score || 0) >= 40
                    ? "bg-amber-600"
                    : "bg-emerald-600"
                }`}
              >
                {selectedInc.risk_score >= 70
                  ? "CRITICAL"
                  : selectedInc.risk_score >= 40
                  ? "HIGH"
                  : "MODERATE"}
              </span>
            </div>
          </div>

          {/* Telemetry 4-Pack */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
              <span className="text-[10px] uppercase font-mono text-slate-500 dark:text-slate-400 font-bold block">
                Target GPS
              </span>
              <div className="text-sm font-black font-mono text-slate-900 dark:text-white mt-0.5">
                {selectedInc.coordinates?.lat || "—"}°N •{" "}
                {selectedInc.coordinates?.lon || "—"}°E
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
              <span className="text-[10px] uppercase font-mono text-slate-500 dark:text-slate-400 font-bold block">
                Thermal Power (FRP)
              </span>
              <div className="text-sm font-black font-mono text-orange-600 dark:text-orange-400 mt-0.5">
                {selectedInc.frp_mw || "0.0"} MW
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
              <span className="text-[10px] uppercase font-mono text-slate-500 dark:text-slate-400 font-bold block">
                Hazard Rating
              </span>
              <div className="text-sm font-black font-mono text-red-600 dark:text-red-400 mt-0.5">
                Risk {selectedInc.risk_score}/100
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
              <span className="text-[10px] uppercase font-mono text-slate-500 dark:text-slate-400 font-bold block">
                Surface Wind
              </span>
              <div className="text-sm font-black font-mono text-blue-600 dark:text-blue-400 mt-0.5">
                {selectedInc.wind_corridor?.direction || "NE"} at{" "}
                {selectedInc.wind_corridor?.speed_kmh || 20} km/h
              </div>
            </div>
          </div>

          {/* Assigned Authority */}
          {selectedInc.assigned_authority && (
            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">
                  Assigned:{" "}
                  <strong className="text-slate-800 dark:text-slate-200">
                    {selectedInc.assigned_authority.name}
                  </strong>
                </span>
                <span className="font-mono text-blue-600">
                  ETA {selectedInc.assigned_authority.eta_mins} min
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Operational State Machine Action Card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 text-xs">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-bold block">
              Lifecycle Control
            </span>
            <h4 className="text-sm font-bold text-slate-900 dark:text-white">
              Field Status Progression
            </h4>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-slate-500">
              Current state:
            </span>
            <span
              className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold text-white ${
                STATUS_COLORS[currentStatus?.toUpperCase()] || "bg-slate-500"
              }`}
            >
              {currentStatus?.toUpperCase() || "UNKNOWN"}
            </span>
          </div>
        </div>

        {/* State Machine Visual Pipeline */}
        {renderStateMachine()}

        {/* Transition Error */}
        {transitionError && (
          <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-xs text-red-700 dark:text-red-300 font-mono">
            ❌ {transitionError}
          </div>
        )}

        {/* Ground Verification Note */}
        <div className="space-y-2">
          <label className="text-[10px] text-slate-400 uppercase font-mono font-bold block">
            Ground Verification Note (optional)
          </label>
          <textarea
            rows={2}
            value={groundNote}
            onChange={(e) => setGroundNote(e.target.value)}
            placeholder="Enter field observation: fire perimeter status, wind conditions, evacuation status..."
            className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-xs placeholder:text-slate-400 focus:ring-2 focus:ring-orange-500 outline-none"
          />
        </div>

        {/* Primary Action Button */}
        {canAdvance ? (
          <button
            onClick={() => advanceState(nextAction.next)}
            className={`w-full py-4 px-6 rounded-xl ${nextAction.actionClass} text-white font-black text-sm tracking-wider uppercase shadow-lg transition-transform active:scale-[0.98] flex items-center justify-center gap-2`}
          >
            <span>{nextAction.actionLabel}</span>
            <span>→</span>
          </button>
        ) : (
          <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-center space-y-1">
            <div className="font-black text-sm uppercase tracking-wider flex items-center justify-center gap-1.5">
              ✅ Mission Complete
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              All fire perimeters sealed. Site handed over to state
              post-disaster authorities.
            </p>
          </div>
        )}

        {/* Disable info */}
        <div className="text-[10px] text-slate-400 font-mono text-center">
          Transitions validated against backend state machine. Invalid moves
          return HTTP 409.
        </div>
      </div>

      {/* Status History */}
      {statusLog.length > 0 && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm p-5 space-y-3">
          <span className="text-[10px] text-slate-400 uppercase font-mono font-bold block">
            Status History
          </span>
          <div className="space-y-0">
            {statusLog.map((entry, i) => (
              <div
                key={i}
                className="flex items-start gap-3 text-xs py-1.5 border-l-2 border-slate-200 dark:border-slate-700 pl-3 ml-1"
              >
                <div
                  className={`w-2 h-2 rounded-full mt-1 -ml-[17px] shrink-0 ${
                    STATUS_COLORS[entry.status] || "bg-slate-400"
                  }`}
                />
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold">{entry.status}</span>
                    <span className="text-[10px] text-slate-400 font-mono">
                      {entry.timestamp}
                    </span>
                  </div>
                  {entry.note && (
                    <div className="text-slate-500 dark:text-slate-400 text-[11px] mt-0.5 italic">
                      "{entry.note}"
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Loading / Error states */}
      {loading && (
        <div className="text-xs text-blue-500 font-mono py-6 text-center">
          Loading incidents...
        </div>
      )}
      {error && !loading && (
        <div className="text-xs text-red-500 font-mono py-6 text-center border border-red-200 dark:border-red-900 rounded-lg">
          Error: {error}
          <button
            onClick={fetchIncidents}
            className="underline ml-2 text-blue-500"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}
