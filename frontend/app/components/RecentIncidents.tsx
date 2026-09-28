interface Props {
  incidents: any[];
  onSelectIncident?: (incident: any) => void;
}

export default function RecentIncidents({
  incidents,
  onSelectIncident,
}: Props) {
  return (
    <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <h2 className="text-xl font-bold text-cyan-400 mb-4">
        🚨 Recent Incidents
      </h2>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-slate-400">
              <th className="text-left py-2">Type</th>
              <th className="text-left py-2">Severity</th>
              <th className="text-left py-2">Location</th>
              <th className="text-left py-2">Time</th>
            </tr>
          </thead>

          <tbody>
            {incidents.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-6 text-center text-slate-500">
                  No incidents detected
                </td>
              </tr>
            ) : (
              incidents.map((incident) => (
                <tr
                  key={incident.id}
                  onClick={() => onSelectIncident?.(incident)}
                  className="cursor-pointer border-b border-slate-800 hover:bg-slate-800 transition"
                >
                  <td className="py-3">
                    {incident.incident_type || incident.type}
                  </td>

                  <td
                    className={`py-3 font-semibold ${
                      incident.severity === "High"
                        ? "text-red-400"
                        : incident.severity === "Medium"
                        ? "text-yellow-400"
                        : "text-green-400"
                    }`}
                  >
                    {incident.severity}
                  </td>

                  <td className="py-3">
                    {incident.location || "Unknown"}
                  </td>

                  <td className="py-3">
                    {incident.detected_at
                      ? new Date(incident.detected_at).toLocaleTimeString()
                      : "-"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}