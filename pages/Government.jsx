/**
 * pages/Government.jsx — Government Command Center Page
 * Owner: Adil
 *
 * Master-detail layout for government officials:
 * - Left: Active incidents list (master)
 * - Right: Selected incident dossier with actions
 *
 * This is the top-level page component that wraps GovernmentCommand.
 * Import and render inside the portal routing system.
 */
import React from "react";
import GovernmentCommand from "../components/government/GovernmentCommand";

/**
 * Government Page
 * Renders the Government Command Center portal.
 *
 * Usage in portal routing:
 *   {portal === "command" && <GovernmentPage />}
 */
export default function GovernmentPage() {
  return (
    <div className="space-y-6">
      <GovernmentCommand />
    </div>
  );
}
