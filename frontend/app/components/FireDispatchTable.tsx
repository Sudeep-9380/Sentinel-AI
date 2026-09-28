"use client";

import { useCallback, useEffect, useState } from "react";

import {
  Phone,
  MapPin,
  Flame,
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

export default function FireDispatchTable() {
  const [dispatches, setDispatches] = useState<DispatchItem[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // ============================================================
  // LOAD FIRE DISPATCHES ONLY
  // ============================================================

  const loadDispatches = useCallback(async () => {
    try {
      const res = await fetch(
        `${API}/incidents`,
        {
          cache: "no-store",
        }
      );

      if (!res.ok) {
        throw new Error("Failed to fetch incidents");
      }

      const data = await res.json();

      const rows: DispatchItem[] = [];

      data.forEach((incident: any) => {
        if (!incident.dispatched_offices) {
          return;
        }

        // ONLY FIRE
        const fireOffices =
          incident.dispatched_offices["FIRE"];

        if (!Array.isArray(fireOffices)) {
          return;
        }

        fireOffices.forEach((office: any) => {
          rows.push({
            incidentId: incident.id,
            incident:
              incident.threat_type?.name ||
              "Incident",
            severity:
              incident.severity ||
              "UNKNOWN",
            agency: "FIRE",
            office,
          });
        });
      });

      setDispatches(rows);
    } catch (error) {
      console.error(
        "Fire dispatch loading error:",
        error
      );
    }
  }, []);

  // ============================================================
  // AUTO REFRESH
  // ============================================================

  useEffect(() => {
    loadDispatches();

    const timer = setInterval(() => {
      loadDispatches();
    }, 3000);

    return () => clearInterval(timer);
  }, [loadDispatches]);

  // ============================================================
  // DELETE FIRE DISPATCH
  // ============================================================

  const deleteDispatch = async (
    incidentId: string
  ) => {
    const confirmed = window.confirm(
      "Remove this FIRE dispatch?"
    );

    if (!confirmed) {
      return;
    }

    try {
      setDeletingId(incidentId);

      const res = await fetch(
        `${API}/incidents/${incidentId}/dispatch/FIRE`,
        {
          method: "DELETE",
        }
      );

      if (!res.ok) {
        const text = await res.text();

        throw new Error(
          text || "Failed to remove fire dispatch"
        );
      }

      setDispatches((current) =>
        current.filter(
          (item) =>
            item.incidentId !== incidentId
        )
      );
    } catch (error) {
      console.error(
        "Fire dispatch delete error:",
        error
      );

      alert(
        "Failed to remove fire dispatch."
      );
    } finally {
      setDeletingId(null);
    }
  };

  // ============================================================
  // UI
  // ============================================================

  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 h-full overflow-y-auto">

      <h2 className="text-2xl font-bold text-orange-400 mb-6">
        🔥 Live Fire Dispatch Queue
      </h2>

      {dispatches.length === 0 ? (
        <div className="text-center text-slate-400 py-10">
          No Active Fire Dispatches
        </div>
      ) : (
        <div className="space-y-4">

          {dispatches.map((item, index) => (
            <div
              key={`${item.incidentId}-${index}`}
              className="rounded-xl border border-slate-700 bg-slate-800 p-5 hover:border-orange-500 transition"
            >

              {/* HEADER */}

              <div className="flex justify-between items-start gap-4">

                <div>
                  <h3 className="text-lg font-bold text-white">
                    {item.office?.name ||
                      "Unknown Fire Station"}
                  </h3>

                  <p className="text-sm text-slate-400 mt-1">
                    {item.incident}
                  </p>

                  <p className="text-xs text-slate-500 mt-1">
                    Severity:{" "}
                    {item.severity}
                  </p>
                </div>

                <span className="rounded-full bg-green-600 px-3 py-1 text-xs font-bold">
                  DISPATCHED
                </span>

              </div>

              {/* DETAILS */}

              <div className="mt-5 space-y-3 text-sm text-slate-300">

                <div className="flex items-center gap-2">
                  <Flame
                    size={16}
                    className="text-orange-400"
                  />
                  FIRE
                </div>

                <div className="flex items-center gap-2">
                  <MapPin
                    size={16}
                    className="text-red-400"
                  />
                  {item.office?.distance_km ??
                    "--"}{" "}
                  km
                </div>

                <div className="flex items-center gap-2">
                  <Phone
                    size={16}
                    className="text-green-400"
                  />
                  {item.office?.contact_number ||
                    "--"}
                </div>

              </div>

              {/* DELETE */}

              <button
                onClick={() =>
                  deleteDispatch(
                    item.incidentId
                  )
                }
                disabled={
                  deletingId ===
                  item.incidentId
                }
                className="mt-5 w-full flex items-center justify-center gap-2 rounded-lg bg-red-700 px-4 py-3 font-semibold text-white transition hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Trash2 size={18} />

                {deletingId ===
                  item.incidentId
                  ? "Removing..."
                  : "Remove Fire Dispatch"}
              </button>

            </div>
          ))}

        </div>
      )}
    </div>
  );
}