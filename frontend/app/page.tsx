"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import dynamic from "next/dynamic";

import Sidebar from "./components/Sidebar";
import { SystemHealth } from "./components/SystemHealth";
import { AlertFeed } from "./components/AlertFeed";
import StatCard from "./components/StatCard";
import QuickActions from "./components/QuickActions";
import CameraStatus from "./components/CameraStatus";
import IncidentStats from "./components/IncidentStats";
import RecentIncidents from "./components/RecentIncidents";
import AnalyticsCharts from "./components/AnalyticsCharts";

// Dynamic import for Leaflet map to prevent SSR issues
const SituationMap = dynamic(
  () => import("./components/SituationMap"),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full w-full items-center justify-center rounded-2xl border border-border bg-surface-elevated/50">
        <span className="font-mono text-sm tracking-widest text-text-dim">
          INITIALIZING GIS MODULE...
        </span>
      </div>
    ),
  }
);

const API_BASE = "http://127.0.0.1:8000/api/v1";

const POLL_INTERVAL_MS = 1000;

export default function CommandCenter() {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [cameras, setCameras] = useState<any[]>([]);

  const [activeIncidentId, setActiveIncidentId] =
    useState<string | null>(null);

  const [selectedLocation, setSelectedLocation] =
    useState<[number, number] | null>(null);

  const pollRef =
    useRef<ReturnType<typeof setInterval> | null>(null);

  // ============================================================
  // FETCH INCIDENTS
  // ============================================================

  const fetchIncidents = useCallback(async () => {
    try {
      const res = await fetch(
        `${API_BASE}/incidents`,
        {
          mode: "cors",
          credentials: "omit",
          cache: "no-store",
        }
      );

      if (!res.ok) {
        throw new Error(
          `Incident API failed: ${res.status}`
        );
      }

      const payload = await res.json();

      // Backend can return either:
      // [...]
      //
      // OR:
      // {
      //   value: [...],
      //   Count: ...
      // }
      const data = Array.isArray(payload)
        ? payload
        : Array.isArray(payload?.value)
          ? payload.value
          : [];

      // Newest incidents first
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
    } catch (err) {
      console.error(
        "Incident API error:",
        err
      );

      setIncidents([]);
    }
  }, []);

  // ============================================================
  // FETCH CAMERAS
  // ============================================================

  const fetchCameras = useCallback(async () => {
    try {
      const res = await fetch(
        `${API_BASE}/cameras`,
        {
          cache: "no-store",
        }
      );

      if (!res.ok) {
        throw new Error(
          `Camera API failed: ${res.status}`
        );
      }

      const data = await res.json();

      // Camera API should return an array
      setCameras(
        Array.isArray(data)
          ? data
          : []
      );
    } catch (err) {
      console.error(
        "Camera API error:",
        err
      );

      setCameras([]);
    }
  }, []);

  // ============================================================
  // POLLING
  // ============================================================

  useEffect(() => {
    // Initial load
    fetchIncidents();
    fetchCameras();

    // Refresh every second
    pollRef.current = setInterval(() => {
      fetchIncidents();
      fetchCameras();
    }, POLL_INTERVAL_MS);

    // Cleanup
    return () => {
      if (pollRef.current) {
        clearInterval(
          pollRef.current
        );

        pollRef.current = null;
      }
    };
  }, [
    fetchIncidents,
    fetchCameras,
  ]);

  // ============================================================
  // ACTIVE INCIDENTS
  // ============================================================
  //
  // Only RESOLVED and CLOSED incidents are excluded.
  //
  // DETECTED
  // DISPATCHED
  // IN_PROGRESS
  // ESCALATED
  // etc.
  //
  // will still be considered active.
  // ============================================================

  const activeIncidents = incidents.filter(
    (incident) => {
      const status = String(
        incident?.status || ""
      )
        .trim()
        .toUpperCase();

      return (
        status !== "RESOLVED" &&
        status !== "CLOSED"
      );
    }
  );

  // ============================================================
  // ONLINE CAMERAS
  // ============================================================

  const onlineCameras = cameras.filter(
    (camera) =>
      String(
        camera?.status || ""
      )
        .trim()
        .toUpperCase() === "ONLINE"
  );

  // ============================================================
  // SELECTED / ACTIVE INCIDENT
  // ============================================================

  const activeIncident =
    incidents.find(
      (incident) =>
        incident.id ===
        activeIncidentId
    ) ||
    incidents[0] ||
    null;

  // ============================================================
  // SELECT INCIDENT LOCATION
  // ============================================================

  const selectIncident = (
    incident: any
  ) => {
    setActiveIncidentId(
      incident.id
    );

    const latitude = Number(
      incident?.gps_latitude
    );

    const longitude = Number(
      incident?.gps_longitude
    );

    if (
      Number.isFinite(latitude) &&
      Number.isFinite(longitude)
    ) {
      setSelectedLocation([
        latitude,
        longitude,
      ]);
    } else {
      setSelectedLocation(null);
    }
  };

  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background font-sans">

      {/* ======================================================
          BACKGROUND
      ====================================================== */}

      <div className="pointer-events-none absolute inset-0 grid-bg opacity-30" />

      {/* ======================================================
          SIDEBAR
      ====================================================== */}

      <Sidebar />

      {/* ======================================================
          MAIN CONTENT
      ====================================================== */}

      <main className="flex-1 overflow-y-auto px-4 pb-4">

        {/* ====================================================
            SYSTEM HEALTH
        ==================================================== */}

        <SystemHealth
          activeNodes={
            activeIncidents.length
          }
        />

        {/* ====================================================
            KPI CARDS
        ==================================================== */}

        <div className="my-4 grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">

          {/* ACTIVE INCIDENTS */}

          <StatCard
            title="Active Incidents"
            value={
              activeIncidents.length
            }
            subtitle="Live Incidents"
            color="text-red-400"
          />

          {/* CAMERAS ONLINE */}

          <StatCard
            title="Cameras Online"
            value={
              onlineCameras.length
            }
            subtitle={`${cameras.length} Total Cameras`}
            color="text-green-400"
          />

          {/* AI ACCURACY */}

          <StatCard
            title="AI Accuracy"
            value="98.6%"
            subtitle="YOLO Model"
            color="text-cyan-400"
          />

          {/* RESPONSE TIME */}

          <StatCard
            title="Avg Response"
            value="3.4 min"
            subtitle="Dispatch Time"
            color="text-yellow-400"
          />
        </div>

        {/* ====================================================
            QUICK ACTIONS
        ==================================================== */}

        <QuickActions />

        {/* ====================================================
            MAP + CAMERA STATUS
        ==================================================== */}

        <div className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-3">

          {/* MAP */}

          <div className="xl:col-span-2">

            <SituationMap
              incidents={incidents}
              activeIncident={
                activeIncident
              }
              selectedLocation={
                selectedLocation
              }
            />

          </div>

          {/* CAMERA STATUS */}

          <CameraStatus
            cameras={cameras}
          />

        </div>

        {/* ====================================================
            INCIDENT ANALYTICS
        ==================================================== */}

        <IncidentStats
          incidents={incidents}
        />

        {/* ====================================================
            RECENT INCIDENTS
        ==================================================== */}

        <RecentIncidents
          incidents={incidents}
          onSelectIncident={
            selectIncident
          }
        />

        {/* ====================================================
            ANALYTICS CHARTS
        ==================================================== */}

        <AnalyticsCharts
          incidents={incidents}
        />

      </main>

      {/* ======================================================
          LIVE INCIDENT FEED
      ====================================================== */}

      <div className="flex h-full py-4 pr-4">

        <AlertFeed
          incidents={incidents}

          activeIncidentId={
            activeIncident?.id || null
          }

          onSelectIncident={
            selectIncident
          }

          onRefresh={
            fetchIncidents
          }

          department="ALL"
        />

      </div>

    </div>
  );
}