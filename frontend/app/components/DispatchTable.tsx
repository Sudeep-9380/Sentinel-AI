"use client";

import { useCallback, useEffect, useState } from "react";

import {
  Phone,
  MapPin,
  Shield,
  Trash2,
} from "lucide-react";

const API = "http://127.0.0.1:8000/api/v1";

interface DispatchItem {
  incidentId: string;
  incident: string;
  severity: string;
  agency: string;
  office: any;
}

interface DispatchTableProps {
  department: "POLICE" | "FIRE" | "MEDICAL";
}

export default function DispatchTable({
  department,
}: DispatchTableProps) {
  const [dispatches, setDispatches] = useState<DispatchItem[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadDispatches = useCallback(async () => {
    try {
      const res = await fetch(`${API}/incidents`, {
        cache: "no-store",
      });

      if (!res.ok) {
        throw new Error("Failed to fetch incidents");
      }

      const payload = await res.json();

      // Backend returns:
      // { value: [...], Count: 11 }
      const incidents = Array.isArray(payload)
        ? payload
        : Array.isArray(payload.value)
          ? payload.value
          : [];

      const rows: DispatchItem[] = [];

      // Backend dispatch keys
      const teamKey =
        department === "POLICE"
          ? "POLICE TEAM"
          : department === "FIRE"
            ? "FIRE TEAM"
            : "MEDICAL TEAM";

      incidents.forEach((incident: any) => {
        if (!incident?.dispatched_offices) {
          return;
        }

        const offices =
          incident.dispatched_offices[teamKey];

        if (!Array.isArray(offices)) {
          return;
        }

        offices.forEach((office: any) => {
          rows.push({
            incidentId: incident.id,
            incident:
              incident.threat_type?.name ||
              incident.summary ||
              "Incident",
            severity:
              incident.severity ||
              "UNKNOWN",
            agency: teamKey,
            office,
          });
        });
      });

      setDispatches(rows);
    } catch (error) {
      console.error(
        `${department} dispatch loading error:`,
        error
      );

      setDispatches([]);
    }
  }, [department]);

  useEffect(() => {
    loadDispatches();

    const timer = setInterval(() => {
      loadDispatches();
    }, 3000);

    return () => clearInterval(timer);
  }, [loadDispatches]);

  const deleteDispatch = async (
    incidentId: string
  ) => {
    const confirmed = window.confirm(
      `Remove this ${department} dispatch?`
    );

    if (!confirmed) {
      return;
    }

    try {
      setDeletingId(incidentId);

      const res = await fetch(
        `${API}/incidents/${incidentId}/dispatch/${department}`,
        {
          method: "DELETE",
        }
      );

      if (!res.ok) {
        const text = await res.text();

        throw new Error(
          text || "Failed to remove dispatch"
        );
      }

      setDispatches((current) =>
        current.filter(
          (item) => item.incidentId !== incidentId
        )
      );
    } catch (error) {
      console.error(
        `${department} dispatch delete error:`,
        error
      );

      alert(
        `Failed to remove ${department.toLowerCase()} dispatch.`
      );
    } finally {
      setDeletingId(null);
    }
  };

  const departmentName =
    department === "POLICE"
      ? "Police"
      : department === "FIRE"
        ? "Fire"
        : "Medical";

  const departmentIcon =
    department === "POLICE"
      ? "🚓"
      : department === "FIRE"
        ? "🚒"
        : "🏥";

  return (
    <div className="h-full overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <h2 className="mb-6 text-2xl font-bold text-cyan-400">
        {departmentIcon} Live {departmentName} Dispatch Queue
      </h2>

      {dispatches.length === 0 ? (
        <div className="py-10 text-center text-slate-400">
          No Active {departmentName} Dispatches
        </div>
      ) : (
        <div className="space-y-4">
          {dispatches.map((item, index) => (
            <div
              key={`${item.incidentId}-${index}`}
              className="rounded-xl border border-slate-700 bg-slate-800 p-5 transition hover:border-cyan-500"
            >
              {/* HEADER */}
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-lg font-bold text-white">
                    {item.office?.name ||
                      `Unknown ${departmentName} Office`}
                  </h3>

                  <p className="mt-1 text-sm text-slate-400">
                    {item.incident}
                  </p>

                  <p className="mt-1 text-xs text-slate-500">
                    Severity: {item.severity}
                  </p>
                </div>

                <span className="rounded-full bg-green-600 px-3 py-1 text-xs font-bold text-white">
                  DISPATCHED
                </span>
              </div>

              {/* DETAILS */}
              <div className="mt-5 space-y-3 text-sm text-slate-300">
                <div className="flex items-center gap-2">
                  <Shield
                    size={16}
                    className="text-cyan-400"
                  />
                  {item.agency}
                </div>

                <div className="flex items-center gap-2">
                  <MapPin
                    size={16}
                    className="text-red-400"
                  />
                  {item.office?.distance_km ?? "--"} km
                </div>

                <div className="flex items-center gap-2">
                  <Phone
                    size={16}
                    className="text-green-400"
                  />
                  {item.office?.contact_number || "--"}
                </div>
              </div>

              {/* DELETE BUTTON */}
              <button
                onClick={() =>
                  deleteDispatch(item.incidentId)
                }
                disabled={
                  deletingId === item.incidentId
                }
                className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-red-700 px-4 py-3 font-semibold text-white transition hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Trash2 size={18} />

                {deletingId === item.incidentId
                  ? "Removing..."
                  : `Remove ${departmentName} Dispatch`}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}