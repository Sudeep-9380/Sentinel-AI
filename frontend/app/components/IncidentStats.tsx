"use client";

import {
  AlertTriangle,
  Shield,
  BrainCircuit,
  Users,
} from "lucide-react";

interface Props {
  incidents: any[];
}

export default function IncidentStats({ incidents }: Props) {
  const activeIncidents = incidents.filter(
    (i) => i.status !== "RESOLVED" && i.status !== "CLOSED"
  ).length;

  const criticalIncidents = incidents.filter(
    (i) =>
      (i.severity || "").toUpperCase() === "CRITICAL"
  ).length;

  const avgConfidence =
    incidents.length > 0
      ? Math.round(
        (incidents.reduce(
          (sum, i) => sum + (i.ai_confidence || 0),
          0
        ) /
          incidents.length) *
        100
      )
      : 0;

  let responders = 0;

  incidents.forEach((incident) => {
    if (!incident.dispatched_offices) return;

    Object.values(incident.dispatched_offices).forEach((units: any) => {
      responders += units.length;
    });
  });

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">

      <h2 className="mb-6 text-2xl font-bold text-cyan-400">
        📊 Live Incident Analytics
      </h2>

      <div className="grid grid-cols-4 gap-5">

        <StatCard
          icon={<AlertTriangle size={28} />}
          title="Active Incidents"
          value={activeIncidents}
          color="from-red-600 to-red-500"
        />

        <StatCard
          icon={<Shield size={28} />}
          title="Critical Alerts"
          value={criticalIncidents}
          color="from-orange-500 to-red-500"
        />

        <StatCard
          icon={<BrainCircuit size={28} />}
          title="Avg AI Confidence"
          value={`${avgConfidence}%`}
          color="from-cyan-600 to-blue-600"
        />

        <StatCard
          icon={<Users size={28} />}
          title="Responders"
          value={responders}
          color="from-green-600 to-emerald-500"
        />

      </div>
    </div>
  );
}

function StatCard({
  icon,
  title,
  value,
  color,
}: {
  icon: React.ReactNode;
  title: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-800 p-5 transition hover:scale-[1.02] hover:border-cyan-500">

      <div
        className={`mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br ${color}`}
      >
        {icon}
      </div>

      <p className="text-sm text-slate-400">
        {title}
      </p>

      <h3 className="mt-2 text-4xl font-bold text-white">
        {value}
      </h3>

    </div>
  );
}