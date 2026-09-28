"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

interface Props {
  incidents: any[];
}

export default function AnalyticsCharts({ incidents }: Props) {
  // -------------------------
  // Incident Type Chart
  // -------------------------

  const typeMap: Record<string, number> = {};

  incidents.forEach((incident) => {
    const type =
      incident.threat_type?.name ||
      incident.threat_type?.code ||
      "Unknown";

    typeMap[type] = (typeMap[type] || 0) + 1;
  });

  const incidentTypeData = Object.entries(typeMap).map(
    ([name, value]) => ({
      name,
      value,
    })
  );

  // -------------------------
  // Severity Chart
  // -------------------------

  const severityLevels = [
    "CRITICAL",
    "HIGH",
    "MEDIUM",
    "LOW",
  ];

  const severityData = severityLevels.map((level) => ({
    name: level,
    value: incidents.filter(
      (i) =>
        (i.severity || "").toUpperCase() === level
    ).length,
  }));

  const COLORS = [
    "#ef4444",
    "#f97316",
    "#facc15",
    "#22c55e",
  ];

  return (
    <div className="mt-6 grid grid-cols-1 xl:grid-cols-2 gap-6">

      {/* Incident Types */}

      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">

        <h2 className="mb-5 text-xl font-bold text-cyan-400">
          🚨 Incident Distribution
        </h2>

        <ResponsiveContainer width="100%" height={320}>

          <BarChart data={incidentTypeData}>

            <XAxis dataKey="name" stroke="#94a3b8" />

            <YAxis stroke="#94a3b8" />

            <Tooltip />

            <Bar
              dataKey="value"
              fill="#06b6d4"
              radius={[8, 8, 0, 0]}
            />

          </BarChart>

        </ResponsiveContainer>

      </div>

      {/* Severity */}

      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">

        <h2 className="mb-5 text-xl font-bold text-cyan-400">
          🔥 Severity Distribution
        </h2>

        <ResponsiveContainer width="100%" height={320}>

          <PieChart>

            <Pie
              data={severityData}
              dataKey="value"
              outerRadius={110}
              innerRadius={50}
              label
            >

              {severityData.map((_, index) => (

                <Cell
                  key={index}
                  fill={COLORS[index]}
                />

              ))}

            </Pie>

            <Legend />

            <Tooltip />

          </PieChart>

        </ResponsiveContainer>

      </div>

    </div>
  );
}