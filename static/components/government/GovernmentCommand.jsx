/**
 * GovernmentCommand.jsx — Government Command Center
 * Master-detail layout: active incidents (left) | selected incident dossier (right).
 *
 * Actions: Generate Alert, Acknowledge, Track Status, Export PDF.
 * Reuses dossier blocks shared with NTRO (props contract with Pallabi).
 *
 * API Contract (Frozen — Aditya owns):
 *   GET  /api/incidents                     → { incidents: Incident[] }
 *   GET  /api/incidents/:id                 → Incident
 *   POST /api/incidents/:id/alert           → AlertResponse
 *   GET  /api/incidents/:id/responders      → { responders: Responder[] }
 *   GET  /api/export/:id/pdf                → { pdf_url, filename }
 *   GET  /api/incidents/:id/status-log      → { log: StatusLogEntry[] }
 *
 * CONSTRAINT: UI must NEVER imply autonomous AI dispatch or that a
 * simulated alert reached a real government system.
 */
import React, { useState, useEffect, useCallback, useRef } from "react";

/* ─── Canonical Status Colors (shared with NTRO / Responder) ─── */
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

const SEVERITY_COLORS = {
  CRITICAL: "bg-red-100 text-red-700 border-red-200",
  HIGH: "bg-amber-100 text-amber-700 border-amber-200",
  ALERT: "bg-orange-100 text-orange-700 border-orange-200",
  MODERATE: "bg-blue-100 text-blue-700 border-blue-200",
  ROUTINE: "bg-emerald-100 text-emerald-700 border-emerald-200",
};

/* ─── Shared Dossier Block: Confidence Breakdown ───
 * Props contract with Pallabi's NTRO dossier:
 *   confidence: number, breakdown: { score, rating, sensor_signal, cross_satellite, ... }
 */
function DossierConfidence({ confidence, breakdown }) {
  if (!breakdown) return null;
  return (
    <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 text-xs space-y-1.5">
      <span className="text-[10px] text-slate-400 uppercase font-mono font-bold block">
        AI Confidence Breakdown
      </span>
      <div className="flex items-center justify-between">
        <span className="font-mono text-lg font-black text-emerald-600">
          {confidence}%
        </span>
        <span className="px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 font-bold font-mono text-[10px]">
          {breakdown.rating}
        </span>
      </div>
      {breakdown.sensor_signal && (
        <div className="text-slate-600 dark:text-slate-300 font-mono text-[11px]">
          {breakdown.sensor_signal}
        </div>
      )}
      {breakdown.cross_satellite && (
        <div className="text-slate-500 dark:text-slate-400 text-[11px]">
          {breakdown.cross_satellite}
        </div>
      )}
    </div>
  );
}

/* ─── Shared Dossier Block: Assets at Risk ─── */
function DossierAssets({ assets }) {
  if (!assets || !assets.length) return null;
  return (
    <div className="space-y-1.5">
      <span className="text-[10px] text-slate-400 uppercase font-mono font-bold block">
        Assets at Risk
      </span>
      {assets.map((a, i) => (
        <div
          key={i}
          className="flex items-center justify-between py-1.5 border-b border-slate-100 dark:border-slate-800 last:border-0 text-xs"
        >
          <div>
            <span className="text-slate-800 dark:text-slate-200 font-medium">
              {a.asset}
            </span>
            <span className="text-slate-400 ml-1 text-[10px]">
              {a.distance_km} km
            </span>
          </div>
          <span
            className={`px-1.5 py-0.5 rounded text-[10px] font-bold font-mono ${
              a.risk_tier.includes("CRITICAL")
                ? "bg-red-100 text-red-700"
                : a.risk_tier.includes("HIGH")
                ? "bg-amber-100 text-amber-700"
                : "bg-slate-100 text-slate-600"
            }`}
          >
            {a.risk_tier}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ─── Shared Dossier Block: Wind Corridor ─── */
function DossierWindCorridor({ wind }) {
  if (!wind) return null;
  return (
    <div className="p-2.5 rounded-lg bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900/60 text-[11px] font-mono text-blue-900 dark:text-blue-300">
      <span className="font-bold">Surface Wind:</span> {wind.direction} at{" "}
      {wind.speed_kmh} km/h
      <br />
      <span className="text-blue-700 dark:text-blue-400">
        Downwind Threat: ~{wind.potential_corridor_km} km
      </span>
    </div>
  );
}

/* ─── Shared Dossier Block: Explanation Evidence ─── */
function DossierExplanation({ explanation }) {
  if (!explanation) return null;
  return (
    <div className="space-y-1 text-xs">
      <span className="text-[10px] text-slate-400 uppercase font-mono font-bold block">
        Classification Rationale
      </span>
      {(explanation.evidence || []).map((e, i) => (
        <div key={i} className="flex items-start gap-1.5 text-slate-600 dark:text-slate-300">
          <span className="text-emerald-500 mt-0.5">✔</span>
          <span>{e}</span>
        </div>
      ))}
      {(explanation.counter_evidence || []).map((e, i) => (
        <div key={i} className="flex items-start gap-1.5 text-amber-600 dark:text-amber-400">
          <span className="mt-0.5">⚠</span>
          <span>{e}</span>
        </div>
      ))}
    </div>
  );
}

/* ─── Alert Preview Card ("SIMULATED DISPATCH") ─── */
function AlertPreview({ incident, responders, onConfirm, onCancel, sending }) {
  if (!incident) return null;
  const auth = incident.assigned_authority || {};
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl border-2 border-amber-400 max-w-lg w-full p-6 space-y-4 shadow-2xl">
        {/* SIMULATED DISPATCH banner */}
        <div className="flex items-center gap-3 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-700">
          <span className="text-2xl">⚠️</span>
          <div>
            <div className="font-black text-amber-800 dark:text-amber-200 uppercase tracking-wider text-sm">
              SIMULATED DISPATCH
            </div>
            <div className="text-[11px] text-amber-600 dark:text-amber-400">
              This is a training/simulation alert. It will NOT reach any real government system.
            </div>
          </div>
        </div>

        {/* Alert preview */}
        <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 text-xs space-y-2">
          <div className="flex items-center justify-between font-bold text-slate-900 dark:text-white">
            <span className="font-mono">{incident.id}</span>
            <span className="font-mono text-[10px] uppercase">
              {incident.status || "NEW"}
            </span>
          </div>
          <div className="text-sm font-bold">{incident.title}</div>
          <div className="text-slate-500">{incident.location_name}</div>
          <div className="grid grid-cols-2 gap-2 mt-2 font-mono">
            <div>
              <span className="text-[10px] text-slate-400">Authority</span>
              <div className="font-bold">{auth.name || "Unassigned"}</div>
            </div>
            <div>
              <span className="text-[10px] text-slate-400">ETA</span>
              <div className="font-bold">{auth.eta_mins || "—"} mins</div>
            </div>
          </div>
        </div>

        {/* Nearest Responders */}
        {responders && responders.length > 0 && (
          <div className="space-y-1.5">
            <span className="text-[10px] text-slate-400 uppercase font-mono font-bold">
              Nearest Responders
            </span>
            {responders.map((r, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs"
              >
                <div>
                  <span className="font-bold text-slate-800 dark:text-slate-200">
                    {r.name}
                  </span>
                  <span className="text-slate-400 ml-2">{r.unit}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-blue-600 dark:text-blue-400">
                    {r.distance_km} km
                  </span>
                  <span className="font-mono text-slate-400">ETA {r.eta_mins}m</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Confirm / Cancel */}
        <div className="flex gap-3 pt-2">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 font-bold text-xs hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={sending}
            className="flex-1 px-4 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white font-bold text-xs shadow-sm transition-all flex items-center justify-center gap-2"
          >
            {sending ? (
              <>
                <span className="animate-spin">⏳</span> Sending...
              </>
            ) : (
              <>
                🚨 Confirm Simulated Alert
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Status History Timeline ─── */
function StatusTimeline({ log }) {
  if (!log || !log.length) return null;
  return (
    <div className="space-y-1.5">
      <span className="text-[10px] text-slate-400 uppercase font-mono font-bold block">
        Status History
      </span>
      <div className="space-y-0">
        {log.map((entry, i) => (
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
                <div className="text-slate-500 dark:text-slate-400 text-[11px] mt-0.5">
                  {entry.note}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
 * MAIN COMPONENT
 * ════════════════════════════════════════════════════════════════════ */
export default function GovernmentCommand() {
  const [incidents, setIncidents] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedInc, setSelectedInc] = useState(null);
  const [responders, setResponders] = useState([]);
  const [statusLog, setStatusLog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Alert flow
  const [showAlertPreview, setShowAlertPreview] = useState(false);
  const [alertSending, setAlertSending] = useState(false);
  const [alertResult, setAlertResult] = useState(null);

  // Polling ref
  const pollRef = useRef(null);

  /* ─── Fetch all incidents ─── */
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

      // If selected incident, refresh its detail too
      if (selectedId) {
        const detail = await fetch(`/api/incident/${selectedId}`);
        if (detail.ok) {
          const inc = await detail.json();
          setSelectedInc(inc);
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  /* ─── Fetch single incident detail + responders + status log ─── */
  const fetchDetail = useCallback(async (id) => {
    try {
      const [incResp, respResp, logResp] = await Promise.all([
        fetch(`/api/incident/${id}`),
        fetch(`/api/incidents/${id}/responders`).catch(() => null),
        fetch(`/api/incidents/${id}/status-log`).catch(() => null),
      ]);

      if (incResp.ok) {
        const inc = await incResp.json();
        setSelectedInc(inc);
      }

      if (respResp && respResp.ok) {
        const rd = await respResp.json();
        setResponders(rd.responders || []);
      } else {
        setResponders([]);
      }

      if (logResp && logResp.ok) {
        const ld = await logResp.json();
        setStatusLog(ld.log || []);
      } else {
        setStatusLog([]);
      }
    } catch (err) {
      console.error("Failed to fetch incident detail:", err);
    }
  }, []);

  /* ─── Select incident ─── */
  const selectIncident = useCallback(
    (id) => {
      setSelectedId(id);
      setAlertResult(null);
      fetchDetail(id);
    },
    [fetchDetail]
  );

  /* ─── Poll every 5 seconds for cross-portal state sync ─── */
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

  /* ─── Generate Alert (POST /api/incidents/:id/alert) ─── */
  const handleAlertConfirm = async () => {
    if (!selectedId) return;
    setAlertSending(true);
    try {
      const resp = await fetch(`/api/incidents/${selectedId}/alert`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          incident_id: selectedId,
          alert_type: "SIMULATED_DISPATCH",
        }),
      });
      if (resp.status === 409) {
        const data = await resp.json();
        setAlertResult({ error: data.error || "Invalid transition" });
        return;
      }
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setAlertResult(data);
      setShowAlertPreview(false);
      // Refresh data
      fetchIncidents();
      if (selectedId) fetchDetail(selectedId);
    } catch (err) {
      setAlertResult({ error: `Network error: ${err.message}` });
    } finally {
      setAlertSending(false);
    }
  };

  /* ─── Acknowledge Incident (PATCH /api/incidents/:id/status) ─── */
  const handleAcknowledge = async () => {
    if (!selectedId) return;
    try {
      const resp = await fetch(`/api/incidents/${selectedId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "INVESTIGATING" }),
      });
      if (resp.status === 409) {
        const data = await resp.json();
        alert(`Invalid transition: ${data.error}`);
        return;
      }
      if (resp.status === 403) {
        alert("You do not have permission to perform this action.");
        return;
      }
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      fetchIncidents();
      if (selectedId) fetchDetail(selectedId);
    } catch (err) {
      alert(`Network error: ${err.message}`);
    }
  };

  /* ─── Export PDF (GET /api/export/:id/pdf) ─── */
  const handleExportPDF = async () => {
    if (!selectedId) return;
    try {
      const resp = await fetch(`/api/export/${selectedId}/pdf`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      if (data.pdf_url) {
        window.open(data.pdf_url, "_blank");
      } else {
        alert(`PDF Export: ${data.filename || "Export generated"}`);
      }
    } catch (err) {
      alert(`PDF export failed: ${err.message}`);
    }
  };

  /* ─── Render ─── */
  const selected = selectedInc;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Incident Command Center
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Real-time situational awareness &bull; Master-Detail View &bull; All
            jurisdictions
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-xs font-bold font-mono">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <span>{incidents.length} Active Incidents</span>
        </div>
      </div>

      {/* 4 Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm space-y-1">
          <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
            Active Incidents
          </span>
          <div className="text-3xl font-bold text-orange-600 dark:text-orange-400 font-mono">
            {incidents.length}
          </div>
          <span className="text-[11px] text-slate-500 font-medium">
            Across all jurisdictions
          </span>
        </div>
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm space-y-1">
          <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
            Critical
          </span>
          <div className="text-3xl font-bold text-red-600 dark:text-red-400 font-mono">
            {
              incidents.filter(
                (i) => i.risk_score >= 70 || i.risk_label?.includes("CRITICAL")
              ).length
            }
          </div>
          <span className="text-[11px] text-red-500 font-medium">
            Immediate attention
          </span>
        </div>
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm space-y-1">
          <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
            Dispatched
          </span>
          <div className="text-3xl font-bold text-blue-600 dark:text-blue-400 font-mono">
            {
              incidents.filter(
                (i) =>
                  i.status === "DISPATCHED" ||
                  i.status === "EN ROUTE" ||
                  i.status === "ARRIVED"
              ).length
            }
          </div>
          <span className="text-[11px] text-slate-500 font-medium">
            Teams in field
          </span>
        </div>
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm space-y-1">
          <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
            Resolved Today
          </span>
          <div className="text-3xl font-bold text-emerald-600 dark:text-emerald-400 font-mono">
            {
              incidents.filter(
                (i) => i.status === "RESOLVED" || i.status === "CONTAINED"
              ).length
            }
          </div>
          <span className="text-[11px] text-slate-500 font-medium">
            Contained or closed
          </span>
        </div>
      </div>

      {/* ─── Master-Detail Layout ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT: Active Incidents List (Master) */}
        <div className="lg:col-span-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2.5 text-xs font-bold">
            <span className="text-slate-800 dark:text-slate-200">
              Active Incidents
            </span>
            <span className="text-slate-400 font-mono">
              {incidents.length} events
            </span>
          </div>

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

          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
            {incidents.map((inc) => {
              const isSelected = inc.id === selectedId;
              const st = (inc.status || "NEW").toUpperCase();
              const riskColor =
                inc.risk_score >= 70
                  ? "text-red-600 dark:text-red-400"
                  : inc.risk_score >= 40
                  ? "text-amber-600 dark:text-amber-400"
                  : "text-emerald-600 dark:text-emerald-400";

              return (
                <div
                  key={inc.id}
                  onClick={() => selectIncident(inc.id)}
                  className={`p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                    isSelected
                      ? "border-blue-500 bg-blue-50/40 dark:bg-blue-950/20 ring-1 ring-blue-500/30"
                      : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                      {inc.id}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono text-white ${
                        STATUS_COLORS[st] || "bg-slate-500"
                      }`}
                    >
                      {st}
                    </span>
                  </div>
                  <div className="text-xs font-bold text-slate-900 dark:text-white mt-1">
                    {inc.title}
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 truncate">
                    {inc.location_name}
                  </div>
                  <div className="flex items-center justify-between mt-1.5">
                    <span
                      className={`text-[10px] font-mono font-bold ${riskColor}`}
                    >
                      Risk: {inc.risk_score}
                    </span>
                    <span className="text-slate-400 font-mono text-[10px]">
                      {inc.classification}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* RIGHT: Selected Incident Dossier (Detail) */}
        <div className="lg:col-span-7 space-y-4">
          {!selected ? (
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8 shadow-sm text-center">
              <div className="text-slate-400 dark:text-slate-500 text-sm font-medium">
                Select an incident from the list to view its dossier.
              </div>
            </div>
          ) : (
            <>
              {/* Dossier Header */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <span className="text-[10px] font-mono uppercase text-slate-400 block font-semibold">
                      Incident Dossier
                    </span>
                    <h3 className="text-xl font-bold text-slate-900 dark:text-white">
                      {selected.title}
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                      {selected.location_name}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono text-white ${
                          STATUS_COLORS[selected.status?.toUpperCase()] ||
                          "bg-slate-500"
                        }`}
                      >
                        {selected.status || "NEW"}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded border text-[10px] font-bold font-mono ${
                          SEVERITY_COLORS[
                            selected.risk_label?.split(" ")[0]
                          ] || "bg-slate-100 text-slate-600 border-slate-200"
                        }`}
                      >
                        {selected.risk_label || "UNKNOWN"}
                      </span>
                      <span className="text-slate-400 font-mono text-[10px]">
                        Risk Score: {selected.risk_score}
                      </span>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => setShowAlertPreview(true)}
                      className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-lg font-bold text-xs shadow-sm transition-all flex items-center gap-1.5"
                    >
                      🚨 Generate Alert
                    </button>
                    <button
                      onClick={handleAcknowledge}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold text-xs shadow-sm transition-all flex items-center gap-1.5"
                    >
                      ✓ Acknowledge
                    </button>
                    <button
                      onClick={handleExportPDF}
                      className="px-4 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg font-bold text-xs shadow-sm transition-all flex items-center gap-1.5 border border-slate-200 dark:border-slate-700"
                    >
                      📄 Export PDF
                    </button>
                  </div>
                </div>

                {/* Alert result */}
                {alertResult && (
                  <div
                    className={`p-3 rounded-lg text-xs font-mono ${
                      alertResult.error
                        ? "bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300"
                        : "bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300"
                    }`}
                  >
                    {alertResult.error ? (
                      <span>❌ {alertResult.error}</span>
                    ) : (
                      <span>
                        ✅ Alert sent. Ticket: {alertResult.alert_id || "N/A"}.
                        Dispatched to: {alertResult.dispatched_to || "N/A"}.
                      </span>
                    )}
                  </div>
                )}

                {/* Quick Telemetry */}
                <div className="grid grid-cols-3 gap-3 p-3 bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-200 dark:border-slate-800 text-xs font-mono">
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase block">
                      FRP
                    </span>
                    <span className="text-sm font-bold text-slate-900 dark:text-white">
                      {selected.frp_mw} MW
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase block">
                      Confidence
                    </span>
                    <span className="text-sm font-bold text-emerald-600">
                      {selected.confidence}%
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase block">
                      Classification
                    </span>
                    <span className="text-sm font-bold text-slate-900 dark:text-white">
                      {selected.classification}
                    </span>
                  </div>
                </div>

                {/* Coordinates */}
                {selected.coordinates && (
                  <div className="text-xs font-mono text-slate-500">
                    📍 {selected.coordinates.lat}°N,{" "}
                    {selected.coordinates.lon}°E
                  </div>
                )}
              </div>

              {/* Dossier Blocks */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
                <DossierConfidence
                  confidence={selected.confidence}
                  breakdown={selected.confidence_breakdown}
                />
                <DossierWindCorridor wind={selected.wind_corridor} />
                <DossierExplanation
                  explanation={selected.explain_classification}
                />
                <DossierAssets assets={selected.assets_at_risk} />
              </div>

              {/* Assigned Authority */}
              {selected.assigned_authority && (
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
                  <span className="text-[10px] text-slate-400 uppercase font-mono font-bold block">
                    Assigned Authority
                  </span>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <span className="text-slate-400 block">Name</span>
                      <span className="font-bold text-slate-800 dark:text-slate-200">
                        {selected.assigned_authority.name}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Jurisdiction</span>
                      <span className="font-bold text-slate-800 dark:text-slate-200">
                        {selected.assigned_authority.jurisdiction}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Distance</span>
                      <span className="font-bold font-mono text-blue-600">
                        {selected.assigned_authority.distance_km} km
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">ETA</span>
                      <span className="font-bold font-mono text-amber-600">
                        {selected.assigned_authority.eta_mins} mins
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Status Timeline */}
              {statusLog.length > 0 && (
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
                  <StatusTimeline log={statusLog} />
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Alert Preview Modal */}
      {showAlertPreview && (
        <AlertPreview
          incident={selected}
          responders={responders}
          onConfirm={handleAlertConfirm}
          onCancel={() => setShowAlertPreview(false)}
          sending={alertSending}
        />
      )}
    </div>
  );
}
