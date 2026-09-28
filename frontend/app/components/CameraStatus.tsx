"use client";

import { useRouter } from "next/navigation";
import { Video, ExternalLink } from "lucide-react";

interface CameraStatusProps {
  cameras: any[];
}

export default function CameraStatus({
  cameras,
}: CameraStatusProps) {
  const router = useRouter();

  return (
    <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <h2 className="mb-4 text-xl font-bold text-cyan-400">
        📹 Camera Status
      </h2>

      {cameras.length === 0 ? (
        <div className="text-slate-400">
          No cameras available
        </div>
      ) : (
        <div className="space-y-3">
          {cameras.map((camera) => {
            const isOnline =
              String(camera.status || "")
                .toUpperCase() === "ONLINE";

            const isCamera1 =
              String(camera.name || "")
                .toLowerCase() === "camera 1";

            return (
              <div
                key={camera.id}
                className="rounded-lg bg-slate-800 p-3"
              >
                {/* Camera name + status */}
                <div className="flex items-center justify-between">
                  <span className="text-lg">
                    {camera.name}
                  </span>

                  <span
                    className={`font-semibold ${isOnline
                        ? "text-green-400"
                        : "text-red-400"
                      }`}
                  >
                    {camera.status}
                  </span>
                </div>

                {/* Open Camera 1 button */}
                {isCamera1 && isOnline && (
                  <button
                    onClick={() =>
                      router.push("/cameras?camera=1")
                    }
                    className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-600 px-4 py-2.5 font-semibold text-white transition hover:bg-cyan-500"
                  >
                    <Video size={18} />
                    Open Camera 1
                    <ExternalLink size={16} />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}