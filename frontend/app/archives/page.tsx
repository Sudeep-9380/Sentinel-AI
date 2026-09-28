"use client";

import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE!;

export default function ArchivesPage() {
  const [incidents, setIncidents] = useState<any[]>([]);

  useEffect(() => {
    const fetchArchiveData = async () => {
      try {
        const res = await fetch(`${API_BASE}/incidents`);
        if (!res.ok) throw new Error("Backend connection failed");
        const data = await res.json();
        
        // Sort: Newest detected first
        data.sort((a: any, b: any) => new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime());
        
        setIncidents(data);
      } catch (err) {
        console.warn("Archives: Failed to fetch incidents:", err);
        setIncidents([]); // fallback
      }
    };
    fetchArchiveData();
  }, []);
  return (
    <div className="flex h-screen w-full bg-background overflow-hidden font-sans">
      {/* Background Grid Pattern */}
      <div className="absolute inset-0 grid-bg opacity-30 pointer-events-none"></div>

      {/* Left Column: Sidebar */}
      <Sidebar />

      {/* Center Content */}
      <main className="flex-1 flex flex-col relative px-8 py-8 z-10 overflow-y-auto">
        <header className="flex items-center justify-between mb-8 bg-zinc-900/40 backdrop-blur-xl border border-zinc-800 rounded-2xl p-4 shadow-lg">
          <div>
            <h1 className="text-xl font-bold tracking-widest text-text-primary font-mono uppercase">
              Incident Archives
            </h1>
            <p className="text-xs text-text-dim font-mono tracking-wider mt-1">
              History of Incidents
            </p>
          </div>
        </header>

        <div className="bg-surface-elevated rounded-2xl border border-border p-6 shadow-xl">
          <table className="w-full text-left font-mono text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-text-dim">
                <th className="pb-3 px-4">INCIDENT ID</th>
                <th className="pb-3 px-4">TYPE</th>
                <th className="pb-3 px-4">TIMESTAMP</th>
                <th className="pb-3 px-4">STATUS</th>
              </tr>
            </thead>
            <tbody>
              {incidents.length > 0 ? incidents.map((incident) => (
                <tr key={incident.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/20 transition-colors">
                  <td className="py-4 px-4 text-accent">{incident.incident_number}</td>
                  <td className="py-4 px-4 text-text-primary">{incident.threat_type?.name || incident.summary || "UNKNOWN"}</td>
                  <td className="py-4 px-4 text-text-dim">{new Date(incident.detected_at).toLocaleString()}</td>
                  <td className="py-4 px-4 text-success">{incident.status || "DETECTED"}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-text-dim font-mono text-sm tracking-widest border-b border-zinc-800/50 flex items-center justify-center gap-3">
                    <span className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin"></span>
                    Retrieving Ballari Incident Logs...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
