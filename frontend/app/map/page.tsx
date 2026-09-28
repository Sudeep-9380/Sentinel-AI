"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Sidebar from "../components/Sidebar";

const SituationMap = dynamic(() => import("../components/SituationMap"), {
  ssr: false,
  loading: () => (
    <div className="flex-1 w-full h-full flex items-center justify-center bg-surface-elevated/50 rounded-2xl border border-border animate-pulse">
      <span className="font-mono text-sm text-text-dim tracking-widest">INITIALIZING GIS MODULE...</span>
    </div>
  ),
});

export default function MapPage() {
  const [incidents, setIncidents] = useState<any[]>([]);

  useEffect(() => {
    const fetchMapData = async () => {
      try {
        const API_BASE = process.env.NEXT_PUBLIC_API_BASE!;
        const res = await fetch(`${API_BASE}/incidents`);
        if (!res.ok) throw new Error("Backend connection failed");
        const data = await res.json();
        setIncidents(data);
      } catch (err) {
        console.warn("Map: Failed to fetch incidents:", err);
        setIncidents([]); // fallback
      }
    };
    fetchMapData();
  }, []);

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden font-sans">
      <div className="absolute inset-0 grid-bg opacity-30 pointer-events-none"></div>

      {/* Left Column: Sidebar */}
      <Sidebar />

      {/* Center Column: Fullscreen Map */}
      <main className="flex-1 flex flex-col relative px-4 py-4">
        <SituationMap incidents={incidents} activeIncident={null} selectedLocation={null} />
      </main>
    </div>
  );
}
