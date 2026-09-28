"use client";


import { useMemo } from "react";
import {
  AlertTriangle,
  Clock,
  Flame,
  MapPin,
  RefreshCw,
  Shield,
  Stethoscope,
} from "lucide-react";

export type Department = "ALL" | "POLICE" | "FIRE" | "MEDICAL";

interface AlertFeedProps {
  incidents: any[];
  activeIncidentId?: string | number | null;
  onSelectIncident?: (incident: any) => void;
  onRefresh?: () => void;
  department: Department;
}

/* =========================================================
   DEPARTMENT HELPERS
========================================================= */

export function agencyMatchesDepartment(
  agency: string,
  department: Department
) {
  const value = String(agency || "").toUpperCase();

  if (department === "ALL") {
    return true;
  }

  if (department === "POLICE") {
    return value === "POLICE TEAM";
  }

  if (department === "FIRE") {
    return value === "FIRE TEAM";
  }

  if (department === "MEDICAL") {
    return value === "MEDICAL TEAM";
  }

  return false;
}

export function getDepartmentUnits(
  incident: any,
  department: Department
) {
  if (!incident?.dispatched_offices) {
    return [];
  }

  return Object.entries(
    incident.dispatched_offices
  ).filter(([agency]) =>
    agencyMatchesDepartment(agency, department)
  );
}

export function incidentBelongsToDepartment(
  incident: any,
  department: Department
) {
  return getDepartmentUnits(incident, department).length > 0;
}

/* =========================================================
   ICON
========================================================= */

function getIncidentIcon(incident: any) {
  const type = String(
    incident?.threat_type?.name ||
    incident?.threat_type ||
    ""
  ).toLowerCase();

  if (
    type.includes("fire") ||
    type.includes("smoke")
  ) {
    return (
      <Flame
        size={28}
        className="text-red-400"
      />
    );
  }

  if (
    type.includes("medical") ||
    type.includes("accident") ||
    type.includes("injury")
  ) {
    return (
      <Stethoscope
        size={28}
        className="text-green-400"
      />
    );
  }

  if (
    type.includes("crime") ||
    type.includes("fight") ||
    type.includes("violence") ||
    type.includes("police")
  ) {
    return (
      <Shield
        size={28}
        className="text-blue-400"
      />
    );
  }

  return (
    <AlertTriangle
      size={28}
      className="text-yellow-400"
    />
  );
}

/* =========================================================
   DEPARTMENT LABEL
========================================================= */

function departmentLabel(
  department: Department
) {
  if (department === "ALL") {
    return "ALL TEAMS";
  }

  if (department === "POLICE") {
    return "POLICE TEAM";
  }

  if (department === "FIRE") {
    return "FIRE TEAM";
  }

  return "MEDICAL TEAM";
}

/* =========================================================
   MAIN COMPONENT
========================================================= */

export function AlertFeed({
  incidents,
  activeIncidentId,
  onSelectIncident,
  onRefresh,
  department,
}: AlertFeedProps) {
  const filteredIncidents = useMemo(() => {
    return incidents
      .filter((incident) =>
        incidentBelongsToDepartment(
          incident,
          department
        )
      )
      .sort(
        (a, b) =>
          new Date(
            b.detected_at || 0
          ).getTime() -
          new Date(
            a.detected_at || 0
          ).getTime()
      );
  }, [incidents, department]);

  return (
    <div className="h-full overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
      {/* HEADER */}
      <div className="border-b border-red-900/40 bg-gradient-to-r from-red-950/50 to-slate-950 p-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <span className="h-4 w-4 animate-pulse rounded-full bg-red-500" />

              <h2 className="text-xl font-bold text-white">
                LIVE INCIDENT FEED
              </h2>
            </div>

            <p className="mt-2 text-sm text-slate-400">
              Sentinel AI Emergency Monitoring
            </p>
          </div>

          <button
            onClick={onRefresh}
            className="rounded-lg border border-slate-700 bg-slate-800 p-3 transition hover:bg-slate-700"
            title="Refresh"
          >
            <RefreshCw
              size={18}
              className="text-cyan-400"
            />
          </button>
        </div>
      </div>

      {/* INCIDENT LIST */}
      <div className="h-[calc(100%-110px)] overflow-y-auto p-4">
        {filteredIncidents.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <AlertTriangle
                size={42}
                className="mx-auto mb-4 text-slate-600"
              />

              <p className="text-lg font-semibold text-slate-400">
                No {department.toLowerCase()} incidents
              </p>

              <p className="mt-2 text-sm text-slate-500">
                Waiting for new emergency events...
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredIncidents.map(
              (incident: any) => {
                const isActive =
                  incident.id ===
                  activeIncidentId;

                const units =
                  getDepartmentUnits(
                    incident,
                    department
                  );

                const incidentName =
                  incident?.threat_type?.name ||
                  incident?.threat_type ||
                  "Unknown Incident";

                const severity =
                  String(
                    incident?.severity ||
                    "UNKNOWN"
                  ).toUpperCase();

                return (
                  <div
                    key={incident.id}
                    onClick={() =>
                      onSelectIncident?.(
                        incident
                      )
                    }
                    className={`cursor-pointer rounded-2xl border p-5 transition ${isActive
                      ? "border-cyan-500 bg-slate-900"
                      : "border-slate-800 bg-slate-900/70 hover:border-slate-600"
                      }`}
                  >
                    {/* TOP */}
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-center gap-4">
                        <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-slate-800">
                          {getIncidentIcon(
                            incident
                          )}
                        </div>

                        <div>
                          <h3 className="text-lg font-bold text-white">
                            {incidentName}
                          </h3>

                          <div className="mt-2 flex items-center gap-2 text-sm text-slate-400">
                            <MapPin
                              size={15}
                              className="text-cyan-400"
                            />

                            {incident.gps_latitude ??
                              incident.latitude ??
                              incident.lat ??
                              "—"}
                            ,{" "}
                            {incident.gps_longitude ??
                              incident.longitude ??
                              incident.lng ??
                              "—"}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 text-sm text-slate-400">
                        <Clock size={15} />

                        {incident.detected_at
                          ? new Date(
                            incident.detected_at
                          ).toLocaleTimeString(
                            [],
                            {
                              hour: "2-digit",
                              minute:
                                "2-digit",
                            }
                          )
                          : "--:--"}
                      </div>
                    </div>

                    {/* DESCRIPTION */}
                    <div className="mt-4 text-sm text-slate-300">
                      {incident.description ||
                        incident.message ||
                        `${incidentName} detected automatically`}
                    </div>

                    {/* TAGS */}
                    <div className="mt-4 flex flex-wrap gap-2">
                      <span className="rounded-full bg-cyan-900/70 px-3 py-1 text-xs font-bold text-cyan-300">
                        {departmentLabel(
                          department
                        )}
                      </span>

                      <span
                        className={`rounded-full px-3 py-1 text-xs font-bold ${severity === "CRITICAL"
                          ? "bg-red-900 text-red-300"
                          : severity ===
                            "HIGH"
                            ? "bg-orange-900 text-orange-300"
                            : "bg-yellow-900 text-yellow-300"
                          }`}
                      >
                        {severity}
                      </span>

                      {incident.ai_confidence !=
                        null && (
                          <span className="rounded-full bg-slate-700 px-3 py-1 text-xs font-bold text-slate-200">
                            AI{" "}
                            {Math.round(
                              Number(
                                incident.ai_confidence
                              ) *
                              (Number(
                                incident.ai_confidence
                              ) <= 1
                                ? 100
                                : 1)
                            )}
                            %
                          </span>
                        )}
                    </div>

                    {/* ONLY THIS DEPARTMENT'S UNITS */}
                    {units.length > 0 && (
                      <div className="mt-5 border-t border-slate-800 pt-4">
                        <p className="mb-3 text-xs font-bold uppercase tracking-wider text-cyan-400">
                          Assigned{" "}
                          {departmentLabel(
                            department
                          )}
                        </p>

                        <div className="space-y-2">
                          {units.map(
                            ([agency, offices]: [
                              string,
                              any
                            ]) => (
                              <div
                                key={agency}
                                className="rounded-lg bg-slate-800 p-3"
                              >
                                <div className="mb-2 font-semibold text-white">
                                  {agency}
                                </div>

                                <div className="space-y-1">
                                  {Array.isArray(
                                    offices
                                  ) &&
                                    offices.map(
                                      (
                                        office: any,
                                        index: number
                                      ) => (
                                        <div
                                          key={
                                            index
                                          }
                                          className="flex items-center justify-between text-sm"
                                        >
                                          <span className="text-slate-300">
                                            {
                                              office.name
                                            }
                                          </span>

                                          <span className="text-cyan-400">
                                            {office.distance_km ??
                                              "—"}{" "}
                                            km
                                          </span>
                                        </div>
                                      )
                                    )}
                                </div>
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              }
            )}
          </div>
        )}
      </div>
    </div>
  );
}