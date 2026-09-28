"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE!;

interface SituationMapProps {
  incidents?: any[];
  activeIncident?: any;
  selectedLocation: [number, number] | null;
}

const DEFAULT_CENTER: [number, number] = [15.1394, 76.9242];

/* =========================================================
   INCIDENT CONFIG
========================================================= */

const INCIDENT_CONFIG: Record<
  string,
  {
    color: string;
    glow: string;
    emoji: string;
  }
> = {
  FIRE: {
    color: "#ef4444",
    glow: "#ef4444",
    emoji: "🔥",
  },

  ACCIDENT: {
    color: "#f97316",
    glow: "#f97316",
    emoji: "🚑",
  },

  FIGHT: {
    color: "#a855f7",
    glow: "#a855f7",
    emoji: "⚠️",
  },

  THEFT: {
    color: "#eab308",
    glow: "#eab308",
    emoji: "🚨",
  },
};

/* =========================================================
   INCIDENT TYPE
========================================================= */

function getIncidentType(incident: any): string {
  return String(
    incident?.threat_type?.code ??
    incident?.threat_type?.name ??
    incident?.incident_type ??
    incident?.type ??
    "UNKNOWN"
  )
    .toUpperCase()
    .trim();
}

/* =========================================================
   INCIDENT MARKER
========================================================= */

function createIncidentIcon(
  incident: any,
  active = false
): L.DivIcon {
  const type = getIncidentType(incident);

  const config =
    INCIDENT_CONFIG[type] ?? {
      color: "#06b6d4",
      glow: "#06b6d4",
      emoji: "!",
    };

  const size = active ? 68 : 54;
  const innerSize = active ? 42 : 34;

  return L.divIcon({
    className: "sentinel-incident-marker",

    html: `
      <div style="
        position:relative;
        width:${size}px;
        height:${size}px;
        display:flex;
        align-items:center;
        justify-content:center;
      ">

        <div style="
          position:absolute;
          width:${size}px;
          height:${size}px;
          border-radius:50%;
          background:${config.color}30;
          border:2px solid ${config.color}55;
          animation:sentinelPulse 1.5s infinite;
        "></div>

        <div style="
          position:absolute;
          width:${size + 20}px;
          height:${size + 20}px;
          border-radius:50%;
          border:2px solid ${config.color}45;
          animation:sentinelPulse 2s infinite;
        "></div>

        <div style="
          position:relative;
          width:${innerSize}px;
          height:${innerSize}px;
          border-radius:50%;
          background:${config.color};
          border:3px solid white;
          box-shadow:
            0 0 15px ${config.glow},
            0 0 35px ${config.glow},
            0 0 60px ${config.glow}88;
          display:flex;
          align-items:center;
          justify-content:center;
          color:white;
          font-size:${active ? 23 : 18}px;
          z-index:5;
        ">
          ${config.emoji}
        </div>

      </div>

      <style>
        @keyframes sentinelPulse {
          0% {
            transform:scale(0.7);
            opacity:0.8;
          }

          70% {
            transform:scale(1.45);
            opacity:0;
          }

          100% {
            transform:scale(1.45);
            opacity:0;
          }
        }
      </style>
    `,

    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

/* =========================================================
   STATION ICON
========================================================= */

function createStationIcon(type: string): L.DivIcon {
  const normalized =
    String(type || "").toUpperCase();

  let color = "#06b6d4";
  let emoji = "🏢";

  if (normalized === "FIRE") {
    color = "#ef4444";
    emoji = "🔥";
  }

  if (normalized === "POLICE") {
    color = "#2563eb";
    emoji = "👮";
  }

  if (normalized === "HOSPITAL") {
    color = "#22c55e";
    emoji = "🏥";
  }

  return L.divIcon({
    className: "sentinel-station-marker",

    html: `
      <div style="
        width:36px;
        height:36px;
        border-radius:50%;
        background:${color};
        border:3px solid white;
        box-shadow:
          0 0 12px ${color},
          0 0 25px ${color}99;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:17px;
      ">
        ${emoji}
      </div>
    `,

    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
}

/* =========================================================
   CAMERA ICON
========================================================= */

function createCameraIcon(
  status: string
): L.DivIcon {
  const online =
    String(status || "").toUpperCase() ===
    "ONLINE";

  const color = online
    ? "#22c55e"
    : "#64748b";

  return L.divIcon({
    className: "sentinel-camera-marker",

    html: `
      <div style="
        position:relative;
        width:34px;
        height:34px;
        border-radius:50%;
        background:#0f172a;
        border:2px solid ${color};
        box-shadow:
          0 0 12px ${color},
          0 0 20px ${color}88;
        display:flex;
        align-items:center;
        justify-content:center;
        color:white;
        font-size:15px;
      ">

        📹

        <span style="
          position:absolute;
          right:-2px;
          bottom:-2px;
          width:10px;
          height:10px;
          border-radius:50%;
          background:${color};
          border:2px solid #0f172a;
        "></span>

      </div>
    `,

    iconSize: [34, 34],
    iconAnchor: [17, 17],
  });
}

/* =========================================================
   MAIN COMPONENT
========================================================= */

export default function SituationMap({
  incidents = [],
  activeIncident,
  selectedLocation,
}: SituationMapProps) {
  const mapContainerRef =
    useRef<HTMLDivElement | null>(null);

  const mapRef =
    useRef<L.Map | null>(null);

  const incidentLayerRef =
    useRef<L.LayerGroup | null>(null);

  const stationLayerRef =
    useRef<L.LayerGroup | null>(null);

  const cameraLayerRef =
    useRef<L.LayerGroup | null>(null);

  const routeLayerRef =
    useRef<L.LayerGroup | null>(null);

  const radiusLayerRef =
    useRef<L.LayerGroup | null>(null);

  const [stations, setStations] =
    useState<any[]>([]);

  const [cameras, setCameras] =
    useState<any[]>([]);

  const [showCameras, setShowCameras] =
    useState(true);

  const [showStations, setShowStations] =
    useState(true);

  const [showRoutes, setShowRoutes] =
    useState(true);

  /* =======================================================
     VALID INCIDENTS
  ======================================================= */

  const validIncidents = useMemo(() => {
    return incidents.filter(
      (incident: any) => {
        const lat = Number(
          incident?.gps_latitude
        );

        const lng = Number(
          incident?.gps_longitude
        );

        return (
          Number.isFinite(lat) &&
          Number.isFinite(lng)
        );
      }
    );
  }, [incidents]);

  const activeIncidentId =
    activeIncident?.id ??
    activeIncident?.incident_number;

  /* =======================================================
     LOAD STATIONS
  ======================================================= */

  useEffect(() => {
    let cancelled = false;

    async function loadStations() {
      try {
        const response = await fetch(
          `${API_BASE}/stations`,
          {
            cache: "no-store",
          }
        );

        if (!response.ok) {
          throw new Error(
            `Stations API returned ${response.status}`
          );
        }

        const data =
          await response.json();

        if (!cancelled) {
          setStations(
            Array.isArray(data)
              ? data
              : []
          );
        }
      } catch (error) {
        console.error(
          "Station API error:",
          error
        );
      }
    }

    loadStations();

    return () => {
      cancelled = true;
    };
  }, []);

  /* =======================================================
     LOAD CAMERAS
  ======================================================= */

  useEffect(() => {
    let cancelled = false;

    async function loadCameras() {
      try {
        const response = await fetch(
          `${API_BASE}/cameras`,
          {
            cache: "no-store",
          }
        );

        if (!response.ok) {
          throw new Error(
            `Cameras API returned ${response.status}`
          );
        }

        const data =
          await response.json();

        if (!cancelled) {
          setCameras(
            Array.isArray(data)
              ? data
              : []
          );
        }
      } catch (error) {
        console.error(
          "Camera API error:",
          error
        );
      }
    }

    loadCameras();

    return () => {
      cancelled = true;
    };
  }, []);

  /* =======================================================
     CREATE LEAFLET MAP
  ======================================================= */

  useEffect(() => {
    const container =
      mapContainerRef.current;

    if (!container) {
      return;
    }

    if (mapRef.current) {
      return;
    }

    const existingLeafletId =
      (container as any)._leaflet_id;

    if (existingLeafletId) {
      delete (container as any)._leaflet_id;
      container.innerHTML = "";
    }

    const map = L.map(container, {
      center: DEFAULT_CENTER,
      zoom: 13,
      zoomControl: false,
      scrollWheelZoom: true,
      preferCanvas: true,
    });

    mapRef.current = map;

    /* =====================================================
       OPEN STREET MAP
    ===================================================== */

    L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        attribution:
          "&copy; OpenStreetMap contributors",
        maxZoom: 19,
      }
    ).addTo(map);

    /* =====================================================
       LAYERS
    ===================================================== */

    incidentLayerRef.current =
      L.layerGroup().addTo(map);

    stationLayerRef.current =
      L.layerGroup().addTo(map);

    cameraLayerRef.current =
      L.layerGroup().addTo(map);

    routeLayerRef.current =
      L.layerGroup().addTo(map);

    radiusLayerRef.current =
      L.layerGroup().addTo(map);

    /* =====================================================
       ZOOM
    ===================================================== */

    L.control
      .zoom({
        position: "bottomright",
      })
      .addTo(map);

    const resizeTimer =
      window.setTimeout(() => {
        if (
          mapRef.current === map &&
          mapContainerRef.current &&
          mapContainerRef.current.isConnected
        ) {
          try {
            map.invalidateSize();
          } catch {
            console.warn(
              "Leaflet resize skipped"
            );
          }
        }
      }, 300);

    return () => {
      window.clearTimeout(
        resizeTimer
      );

      if (mapRef.current === map) {
        try {
          map.remove();
        } catch {
          console.warn(
            "Leaflet cleanup skipped"
          );
        }

        mapRef.current = null;
      }

      incidentLayerRef.current = null;
      stationLayerRef.current = null;
      cameraLayerRef.current = null;
      routeLayerRef.current = null;
      radiusLayerRef.current = null;

      if (
        container &&
        (container as any)._leaflet_id
      ) {
        delete (
          container as any
        )._leaflet_id;
      }
    };
  }, []);

  /* =======================================================
     SELECTED LOCATION
  ======================================================= */

  useEffect(() => {
    const map =
      mapRef.current;

    if (!map) {
      return;
    }

    if (
      selectedLocation &&
      Number.isFinite(
        selectedLocation[0]
      ) &&
      Number.isFinite(
        selectedLocation[1]
      )
    ) {
      try {
        map.flyTo(
          selectedLocation,
          16,
          {
            animate: true,
            duration: 1,
          }
        );
      } catch {
        console.warn(
          "Location focus skipped"
        );
      }

      return;
    }

    if (activeIncident) {
      const lat = Number(
        activeIncident?.gps_latitude
      );

      const lng = Number(
        activeIncident?.gps_longitude
      );

      if (
        Number.isFinite(lat) &&
        Number.isFinite(lng)
      ) {
        try {
          map.flyTo(
            [lat, lng],
            15,
            {
              animate: true,
              duration: 1,
            }
          );
        } catch {
          console.warn(
            "Incident focus skipped"
          );
        }
      }
    }
  }, [
    selectedLocation,
    activeIncident,
  ]);

  /* =======================================================
     INCIDENT MARKERS
  ======================================================= */

  useEffect(() => {
    const layer =
      incidentLayerRef.current;

    if (!layer) {
      return;
    }

    layer.clearLayers();

    validIncidents.forEach(
      (incident: any) => {
        const lat = Number(
          incident?.gps_latitude
        );

        const lng = Number(
          incident?.gps_longitude
        );

        if (
          !Number.isFinite(lat) ||
          !Number.isFinite(lng)
        ) {
          return;
        }

        const isActive =
          activeIncidentId != null &&
          (
            incident?.id ===
            activeIncidentId ||
            incident?.incident_number ===
            activeIncidentId
          );

        const type =
          getIncidentType(
            incident
          );

        const config =
          INCIDENT_CONFIG[type] ?? {
            color: "#06b6d4",
            glow: "#06b6d4",
            emoji: "!",
          };

        const confidence =
          Number(
            incident?.ai_confidence ??
            incident?.confidence ??
            0
          );

        const confidencePercent =
          confidence <= 1
            ? confidence * 100
            : confidence;

        const marker =
          L.marker(
            [lat, lng],
            {
              icon:
                createIncidentIcon(
                  incident,
                  isActive
                ),

              zIndexOffset:
                isActive
                  ? 1000
                  : 100,
            }
          );

        marker.bindPopup(`
          <div style="
            width:280px;
            font-family:Arial,sans-serif;
            color:#0f172a;
          ">

            <div style="
              background:${config.color};
              color:white;
              padding:10px;
              border-radius:8px;
              margin-bottom:12px;
              font-weight:800;
              font-size:17px;
            ">
              ${config.emoji}
              ${type}
            </div>

            <div style="
              display:grid;
              gap:8px;
              font-size:13px;
            ">

              <div>
                <strong>Incident:</strong>
                ${incident?.incident_number ??
          "N/A"
          }
              </div>

              <div>
                <strong>Confidence:</strong>
                ${confidencePercent.toFixed(1)}%
              </div>

              <div>
                <strong>Severity:</strong>
                ${incident?.severity ??
          "N/A"
          }
              </div>

              <div>
                <strong>Status:</strong>
                ${incident?.status ??
          "Detected"
          }
              </div>

              <div>
                <strong>GPS:</strong>
                ${lat.toFixed(6)},
                ${lng.toFixed(6)}
              </div>

            </div>

          </div>
        `);

        marker.addTo(layer);
      }
    );
  }, [
    validIncidents,
    activeIncidentId,
  ]);

  /* =======================================================
     ACTIVE INCIDENT RADIUS
  ======================================================= */

  useEffect(() => {
    const layer =
      radiusLayerRef.current;

    if (!layer) {
      return;
    }

    layer.clearLayers();

    if (!activeIncident) {
      return;
    }

    const lat = Number(
      activeIncident?.gps_latitude
    );

    const lng = Number(
      activeIncident?.gps_longitude
    );

    if (
      !Number.isFinite(lat) ||
      !Number.isFinite(lng)
    ) {
      return;
    }

    const type =
      getIncidentType(
        activeIncident
      );

    const config =
      INCIDENT_CONFIG[type] ?? {
        color: "#06b6d4",
      };

    L.circle(
      [lat, lng],
      {
        radius: 1000,
        color: config.color,
        weight: 2,
        opacity: 0.6,
        fillColor: config.color,
        fillOpacity: 0.08,
        dashArray: "8 8",
      }
    ).addTo(layer);

    L.circleMarker(
      [lat, lng],
      {
        radius: 7,
        color: "#ffffff",
        weight: 3,
        fillColor: config.color,
        fillOpacity: 1,
      }
    ).addTo(layer);
  }, [activeIncident]);

  /* =======================================================
     STATION MARKERS
  ======================================================= */

  useEffect(() => {
    const layer =
      stationLayerRef.current;

    if (!layer) {
      return;
    }

    layer.clearLayers();

    if (!showStations) {
      return;
    }

    stations.forEach(
      (station: any) => {
        const lat = Number(
          station?.latitude
        );

        const lng = Number(
          station?.longitude
        );

        if (
          !Number.isFinite(lat) ||
          !Number.isFinite(lng)
        ) {
          return;
        }

        const type =
          String(
            station?.office_type ?? ""
          ).toUpperCase();

        const marker =
          L.marker(
            [lat, lng],
            {
              icon:
                createStationIcon(
                  type
                ),
              zIndexOffset: 200,
            }
          );

        marker.bindPopup(`
          <div style="
            width:230px;
            font-family:Arial,sans-serif;
            color:#0f172a;
          ">

            <div style="
              font-size:17px;
              font-weight:800;
              margin-bottom:10px;
            ">
              ${station?.name ??
          "Emergency Office"
          }
            </div>

            <div style="
              margin-bottom:8px;
            ">
              <strong>Department:</strong>
              ${station?.office_type ??
          "N/A"
          }
            </div>

            ${station?.contact_number
            ? `
              <div style="
                margin-bottom:8px;
              ">
                <strong>Contact:</strong>
                ${station.contact_number}
              </div>
            `
            : ""
          }

            <div style="
              font-size:11px;
              color:#64748b;
            ">
              GPS:
              ${lat.toFixed(6)},
              ${lng.toFixed(6)}
            </div>

          </div>
        `);

        marker.addTo(layer);
      }
    );
  }, [
    stations,
    showStations,
  ]);

  /* =======================================================
     CAMERA MARKERS
  ======================================================= */

  useEffect(() => {
    const layer =
      cameraLayerRef.current;

    if (!layer) {
      return;
    }

    layer.clearLayers();

    if (!showCameras) {
      return;
    }

    cameras.forEach(
      (camera: any) => {
        const lat = Number(
          camera?.latitude
        );

        const lng = Number(
          camera?.longitude
        );

        if (
          !Number.isFinite(lat) ||
          !Number.isFinite(lng)
        ) {
          return;
        }

        const marker =
          L.marker(
            [lat, lng],
            {
              icon:
                createCameraIcon(
                  camera?.status
                ),
              zIndexOffset: 150,
            }
          );

        const status =
          String(
            camera?.status ??
            "UNKNOWN"
          ).toUpperCase();

        const statusColor =
          status === "ONLINE"
            ? "#16a34a"
            : "#64748b";

        marker.bindPopup(`
          <div style="
            width:240px;
            font-family:Arial,sans-serif;
            color:#0f172a;
          ">

            <div style="
              font-size:17px;
              font-weight:800;
              margin-bottom:10px;
            ">
              📹
              ${camera?.name ??
          "CCTV Camera"
          }
            </div>

            <div style="
              display:grid;
              gap:7px;
              font-size:13px;
            ">

              <div>
                <strong>Status:</strong>

                <span style="
                  color:${statusColor};
                  font-weight:800;
                ">
                  ${status}
                </span>
              </div>

              <div>
                <strong>Type:</strong>
                ${camera?.camera_type ??
          "CCTV"
          }
              </div>

              <div>
                <strong>FPS:</strong>
                ${camera?.fps ??
          "N/A"
          }
              </div>

              <div>
                <strong>GPS:</strong>
                ${lat.toFixed(6)},
                ${lng.toFixed(6)}
              </div>

            </div>

          </div>
        `);

        marker.addTo(layer);
      }
    );
  }, [
    cameras,
    showCameras,
  ]);

  /* =======================================================
     DISPATCH ROUTES
  ======================================================= */

  useEffect(() => {
    const layer =
      routeLayerRef.current;

    if (!layer) {
      return;
    }

    layer.clearLayers();

    if (
      !showRoutes ||
      !activeIncident ||
      !activeIncident?.dispatched_offices
    ) {
      return;
    }

    const incidentLat =
      Number(
        activeIncident?.gps_latitude
      );

    const incidentLng =
      Number(
        activeIncident?.gps_longitude
      );

    if (
      !Number.isFinite(
        incidentLat
      ) ||
      !Number.isFinite(
        incidentLng
      )
    ) {
      return;
    }

    Object.entries(
      activeIncident.dispatched_offices
    ).forEach(
      ([teamName, offices]) => {
        if (!Array.isArray(offices)) {
          return;
        }

        offices.forEach(
          (
            office: any,
            index: number
          ) => {
            const officeLat =
              Number(
                office?.latitude
              );

            const officeLng =
              Number(
                office?.longitude
              );

            if (
              !Number.isFinite(
                officeLat
              ) ||
              !Number.isFinite(
                officeLng
              )
            ) {
              return;
            }

            const team =
              String(
                teamName
              ).toUpperCase();

            let color =
              "#06b6d4";

            if (
              team.includes("FIRE")
            ) {
              color = "#ef4444";
            } else if (
              team.includes("POLICE")
            ) {
              color = "#2563eb";
            } else if (
              team.includes("MEDICAL")
            ) {
              color = "#22c55e";
            }

            const route =
              L.polyline(
                [
                  [
                    incidentLat,
                    incidentLng,
                  ],
                  [
                    officeLat,
                    officeLng,
                  ],
                ],
                {
                  color,
                  weight: 4,
                  dashArray: "10 8",
                  opacity: 0.9,
                }
              );

            route.bindTooltip(
              `${teamName} • ${office?.name ??
              `Responder ${index + 1}`
              }`,
              {
                sticky: true,
              }
            );

            route.addTo(layer);
          }
        );
      }
    );
  }, [
    activeIncident,
    showRoutes,
  ]);

  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <div className="relative h-[500px] w-full overflow-hidden rounded-2xl border border-slate-700 bg-slate-950 shadow-2xl">

      {/* MAP */}

      <div
        ref={mapContainerRef}
        className="h-full w-full"
      />

      {/* =================================================
          CAMERAS / STATIONS / DISPATCH
          KEEP THESE
      ================================================= */}

      <div className="absolute bottom-5 left-5 z-[1000] flex flex-col gap-2">

        {/* CAMERAS */}

        <button
          onClick={() =>
            setShowCameras(
              (value) => !value
            )
          }
          className={`flex items-center justify-between gap-5 rounded-lg border px-4 py-2.5 text-xs font-bold shadow-xl backdrop-blur-md transition ${showCameras
              ? "border-green-400/40 bg-slate-950/95 text-white hover:bg-green-500/20"
              : "border-slate-600 bg-slate-950/95 text-slate-500"
            }`}
        >
          <span>📹 Cameras</span>

          <span
            className={`h-3 w-3 rounded-full ${showCameras
                ? "bg-green-400 shadow-[0_0_10px_#22c55e]"
                : "bg-slate-600"
              }`}
          />
        </button>

        {/* STATIONS */}

        <button
          onClick={() =>
            setShowStations(
              (value) => !value
            )
          }
          className={`flex items-center justify-between gap-5 rounded-lg border px-4 py-2.5 text-xs font-bold shadow-xl backdrop-blur-md transition ${showStations
              ? "border-blue-400/40 bg-slate-950/95 text-white hover:bg-blue-500/20"
              : "border-slate-600 bg-slate-950/95 text-slate-500"
            }`}
        >
          <span>🚨 Stations</span>

          <span
            className={`h-3 w-3 rounded-full ${showStations
                ? "bg-green-400 shadow-[0_0_10px_#22c55e]"
                : "bg-slate-600"
              }`}
          />
        </button>

        {/* DISPATCH */}

        <button
          onClick={() =>
            setShowRoutes(
              (value) => !value
            )
          }
          className={`flex items-center justify-between gap-5 rounded-lg border px-4 py-2.5 text-xs font-bold shadow-xl backdrop-blur-md transition ${showRoutes
              ? "border-cyan-400/40 bg-slate-950/95 text-white hover:bg-cyan-500/20"
              : "border-slate-600 bg-slate-950/95 text-slate-500"
            }`}
        >
          <span>🛣️ Dispatch</span>

          <span
            className={`h-3 w-3 rounded-full ${showRoutes
                ? "bg-green-400 shadow-[0_0_10px_#22c55e]"
                : "bg-slate-600"
              }`}
          />
        </button>

      </div>

    </div>
  );
}