"use client";

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import { useRouter } from "next/navigation";

import {
  AlertFeed,
  incidentBelongsToDepartment,
} from "../components/AlertFeed";

import DispatchTable from "../components/DispatchTable";

import IncidentStats from "../components/IncidentStats";

const API = process.env.NEXT_PUBLIC_API_BASE!;

export default function PolicePage() {
  const router = useRouter();

  const [incidents, setIncidents] =
    useState<any[]>([]);

  const [activeIncident, setActiveIncident] =
    useState<any>(null);

  const loadIncidents = useCallback(async () => {
    try {
      const res = await fetch(
        `${API}/incidents`,
        {
          cache: "no-store",
        }
      );

      if (!res.ok) {
        throw new Error(
          "Failed to fetch incidents"
        );
      }

      const data = await res.json();

      data.sort(
        (a: any, b: any) =>
          new Date(
            b.detected_at || 0
          ).getTime() -
          new Date(
            a.detected_at || 0
          ).getTime()
      );

      setIncidents(data);
    } catch (error) {
      console.error(
        "Police incident loading error:",
        error
      );
    }
  }, []);

  useEffect(() => {
    loadIncidents();

    const timer = setInterval(() => {
      loadIncidents();
    }, 3000);

    return () => clearInterval(timer);
  }, [loadIncidents]);

  const policeIncidents =
    incidents.filter((incident) =>
      incidentBelongsToDepartment(
        incident,
        "POLICE"
      )
    );

  useEffect(() => {
    if (policeIncidents.length === 0) {
      setActiveIncident(null);
      return;
    }

    setActiveIncident((current: any) => {
      if (!current) {
        return policeIncidents[0];
      }

      const updated =
        policeIncidents.find(
          (incident: any) =>
            incident.id === current.id
        );

      return (
        updated ||
        policeIncidents[0]
      );
    });
  }, [policeIncidents]);

  return (
    <div className="min-h-screen bg-slate-950 text-white">

      {/* HEADER */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur">
        <div className="flex items-center justify-between px-8 py-5">

          <div className="flex items-center gap-6">

            <button
              onClick={() => router.push("/")}
              className="rounded-xl border border-slate-700 bg-slate-800 px-5 py-3 text-white transition hover:bg-slate-700"
            >
              ← Main Dashboard
            </button>

            <div>
              <h1 className="text-4xl font-bold text-cyan-400">
                🚓 Police Command Center
              </h1>

              <p className="mt-2 text-slate-400">
                Live AI Surveillance & Emergency Dispatch
              </p>
            </div>

          </div>

          <div className="flex items-center gap-3">
            <span className="h-3 w-3 animate-pulse rounded-full bg-green-500" />

            <span className="font-bold text-green-400">
              LIVE
            </span>
          </div>

        </div>
      </header>

      {/* MAIN */}
      <main className="space-y-6 p-6">

        <IncidentStats
          incidents={policeIncidents}
        />

        <div className="grid grid-cols-12 gap-6">

          {/* POLICE INCIDENT FEED */}
          <div className="col-span-8 h-[720px]">

            <AlertFeed
              incidents={policeIncidents}
              activeIncidentId={
                activeIncident?.id || null
              }
              onSelectIncident={(incident) => {
                setActiveIncident(incident);
              }}
              onRefresh={loadIncidents}
              department="POLICE"
            />

          </div>

          {/* POLICE DISPATCH */}
          <div className="col-span-4 h-[720px]">

            <DispatchTable
              department="POLICE"
              onDispatchRemoved={(incidentId) => {

                console.log(
                  "Police dispatch removed:",
                  incidentId
                );

                setIncidents((current: any[]) =>
                  current.filter(
                    (incident: any) =>
                      incident.id !== incidentId
                  )
                );

                setActiveIncident((current: any) =>
                  current?.id === incidentId
                    ? null
                    : current
                );

              }}
            />


          </div>

        </div>

        {/* QUICK ACTIONS */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">

          <h2 className="mb-5 text-xl font-bold text-cyan-400">
            ⚡ Police Quick Actions
          </h2>

          <div className="grid grid-cols-4 gap-4">

            <button className="rounded-xl bg-slate-800 py-4 transition hover:bg-slate-700">
              🚓 Dispatch Police Team
            </button>

            <button className="rounded-xl bg-slate-800 py-4 transition hover:bg-slate-700">
              👮 Officers On Duty
            </button>

            <button className="rounded-xl bg-slate-800 py-4 transition hover:bg-slate-700">
              📄 Police Reports
            </button>

            <button className="rounded-xl bg-red-700 py-4 transition hover:bg-red-600">
              🚨 Police Emergency
            </button>

          </div>
        </div>

      </main>
    </div>
  );
}