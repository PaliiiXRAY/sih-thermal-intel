/**
 * pages/Responder.jsx — Responder Operations Page
 * Owner: Adil
 *
 * Field terminal for first responders:
 * - Incident selection and tactical details
 * - State machine with validated transitions
 * - Ground verification notes
 *
 * This is the top-level page component that wraps ResponderOperations.
 * Import and render inside the portal routing system.
 */
import React from "react";
import ResponderOperations from "../components/responder/ResponderOperations";

/**
 * Responder Page
 * Renders the Responder Operations portal.
 *
 * Usage in portal routing:
 *   {portal === "responder" && <ResponderPage />}
 */
export default function ResponderPage() {
  return (
    <div className="space-y-6">
      <ResponderOperations />
    </div>
  );
}
