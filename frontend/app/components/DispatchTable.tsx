"use client";

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  Phone,
  MapPin,
  Shield,
  Trash2,
  RefreshCw,
} from "lucide-react";

const API =
  "http://127.0.0.1:8000/api/v1";

type Department =
  | "POLICE"
  | "FIRE"
  | "MEDICAL";

interface DispatchItem {
  incidentId: string;
  incident: string;
  severity: string;
  agency: string;
  office: any;
}

interface DispatchTableProps {
  department?: Department;

  onDispatchRemoved?: (
    incidentId: string
  ) => void;
}

export default function DispatchTable({
  department = "POLICE",
  onDispatchRemoved,
}: DispatchTableProps) {

  const [dispatches, setDispatches] =
    useState<DispatchItem[]>([]);

  const [deletingId, setDeletingId] =
    useState<string | null>(null);


  // ============================================================
  // DEPARTMENT SETTINGS
  // ============================================================

  const departmentKey =
    department === "POLICE"
      ? "POLICE"
      : department === "FIRE"
        ? "FIRE TEAM"
        : "MEDICAL TEAM";


  const departmentLabel =
    department === "POLICE"
      ? "Police"
      : department === "FIRE"
        ? "Fire"
        : "Medical";


  // ============================================================
  // LOAD DISPATCHES
  // ============================================================

  const loadDispatches = useCallback(
    async () => {

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

        const data =
          await res.json();

        const rows: DispatchItem[] = [];


        data.forEach(
          (incident: any) => {

            if (
              !incident.dispatched_offices
            ) {
              return;
            }


            const offices =
              incident.dispatched_offices[
              departmentKey
              ];


            if (
              !Array.isArray(offices)
            ) {
              return;
            }


            offices.forEach(
              (office: any) => {

                rows.push({
                  incidentId:
                    incident.id,

                  incident:
                    incident
                      .threat_type
                      ?.name ||
                    "Incident",

                  severity:
                    incident.severity ||
                    "UNKNOWN",

                  agency:
                    departmentKey,

                  office,
                });

              }
            );

          }
        );


        setDispatches(rows);

      } catch (error) {

        console.error(
          `${departmentLabel} dispatch loading error:`,
          error
        );

      }

    },
    [
      departmentKey,
      departmentLabel,
    ]
  );


  // ============================================================
  // AUTO REFRESH
  // ============================================================

  useEffect(() => {

    loadDispatches();

    const timer =
      setInterval(
        loadDispatches,
        3000
      );

    return () =>
      clearInterval(timer);

  }, [loadDispatches]);


  // ============================================================
  // REMOVE DISPATCH
  // ============================================================

  const deleteDispatch = async (
    incidentId: string
  ) => {

    const confirmed =
      window.confirm(
        `Remove this ${departmentLabel} dispatch?`
      );

    if (!confirmed) {
      return;
    }


    try {

      setDeletingId(
        incidentId
      );


      console.log(
        `Removing ${departmentKey} dispatch for incident:`,
        incidentId
      );


      const res =
        await fetch(
          `${API}/incidents/${incidentId}/dispatch/${department}`,
          {
            method: "DELETE",
            headers: {
              "Content-Type":
                "application/json",
            },
          }
        );


      const responseText =
        await res.text();


      console.log(
        "DELETE response:",
        res.status,
        responseText
      );


      if (!res.ok) {

        throw new Error(
          responseText ||
          `HTTP ${res.status}`
        );

      }


      // --------------------------------------------------------
      // Remove dispatch immediately
      // --------------------------------------------------------

      setDispatches(
        (current) =>
          current.filter(
            (item) =>
              item.incidentId !==
              incidentId
          )
      );


      // --------------------------------------------------------
      // Remove incident from parent dashboard
      // --------------------------------------------------------

      if (onDispatchRemoved) {

        onDispatchRemoved(
          incidentId
        );

      }


      // --------------------------------------------------------
      // Verify backend state
      // --------------------------------------------------------

      await loadDispatches();


    } catch (error) {

      console.error(
        `${departmentLabel} dispatch delete error:`,
        error
      );

      alert(
        `Failed to remove ${departmentLabel} dispatch.\n\nCheck the browser console.`
      );

    } finally {

      setDeletingId(null);

    }

  };


  // ============================================================
  // UI
  // ============================================================

  return (

    <div
      className="
        rounded-2xl
        bg-slate-900
        border
        border-slate-800
        p-6
        h-full
        overflow-y-auto
      "
    >

      {/* HEADER */}

      <div
        className="
          flex
          items-center
          justify-between
          mb-6
        "
      >

        <h2
          className="
            text-2xl
            font-bold
            text-cyan-400
          "
        >
          {department === "POLICE"
            ? "🚓 Live Police Dispatch Queue"
            : department === "FIRE"
              ? "🚒 Live Fire Dispatch Queue"
              : "🏥 Live Medical Dispatch Queue"}
        </h2>


        <button
          onClick={loadDispatches}
          className="
            rounded-lg
            bg-slate-800
            p-2
            text-cyan-400
            hover:bg-slate-700
          "
          title="Refresh"
        >
          <RefreshCw size={18} />
        </button>

      </div>


      {/* EMPTY */}

      {dispatches.length === 0 ? (

        <div
          className="
            text-center
            text-slate-400
            py-10
          "
        >
          No Active{" "}
          {departmentLabel} Dispatches
        </div>

      ) : (

        <div className="space-y-4">

          {dispatches.map(
            (item, index) => (

              <div
                key={`${item.incidentId}-${index}`}
                className="
                  rounded-xl
                  border
                  border-slate-700
                  bg-slate-800
                  p-5
                  hover:border-cyan-500
                  transition
                "
              >

                {/* HEADER */}

                <div
                  className="
                    flex
                    justify-between
                    items-start
                    gap-4
                  "
                >

                  <div>

                    <h3
                      className="
                        text-lg
                        font-bold
                        text-white
                      "
                    >
                      {item.office?.name ||
                        `Unknown ${departmentLabel} Office`}
                    </h3>


                    <p
                      className="
                        text-sm
                        text-slate-400
                        mt-1
                      "
                    >
                      {item.incident}
                    </p>

                  </div>


                  <span
                    className="
                      rounded-full
                      bg-green-600
                      px-3
                      py-1
                      text-xs
                      font-bold
                    "
                  >
                    DISPATCHED
                  </span>

                </div>


                {/* DETAILS */}

                <div
                  className="
                    mt-5
                    space-y-3
                    text-sm
                    text-slate-300
                  "
                >

                  <div
                    className="
                      flex
                      items-center
                      gap-2
                    "
                  >

                    <Shield
                      size={16}
                      className="text-cyan-400"
                    />

                    {departmentKey}

                  </div>


                  <div
                    className="
                      flex
                      items-center
                      gap-2
                    "
                  >

                    <MapPin
                      size={16}
                      className="text-red-400"
                    />

                    {item.office
                      ?.distance_km ??
                      "--"}{" "}
                    km

                  </div>


                  <div
                    className="
                      flex
                      items-center
                      gap-2
                    "
                  >

                    <Phone
                      size={16}
                      className="text-green-400"
                    />

                    {item.office
                      ?.contact_number ||
                      "--"}

                  </div>

                </div>


                {/* REMOVE */}

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
                  className="
                    mt-5
                    w-full
                    flex
                    items-center
                    justify-center
                    gap-2
                    rounded-lg
                    bg-red-700
                    px-4
                    py-3
                    font-semibold
                    text-white
                    transition
                    hover:bg-red-600
                    disabled:opacity-50
                    disabled:cursor-not-allowed
                  "
                >

                  <Trash2 size={18} />

                  {deletingId ===
                    item.incidentId
                    ? "Removing..."
                    : `Remove ${departmentLabel} Dispatch`}

                </button>

              </div>

            )
          )}

        </div>

      )}

    </div>

  );
}