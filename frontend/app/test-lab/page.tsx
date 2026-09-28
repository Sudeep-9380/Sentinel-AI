"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { Sidebar } from "../components/Sidebar";
import { UploadCloud, Video, ChevronLeft, PlayCircle, Settings2 } from "lucide-react";

export default function TestLab() {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [hasDetected, setHasDetected] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [testMeta, setTestMeta] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const API_BASE = "http://127.0.0.1:8000/api/v1";

    fetch(`${API_BASE}/incidents/meta/test-lab`)
      .then((r) => {
        if (!r.ok) {
          throw new Error("API not reachable");
        }
        return r.json();
      })
      .then((data) => setTestMeta(data))
      .catch((e) => console.error("Failed to load test meta:", e));

  }, []);

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden font-sans">
      {/* Background Grid Pattern */}
      <div className="absolute inset-0 grid-bg opacity-30 pointer-events-none"></div>

      {/* Left Column: Sidebar */}
      <Sidebar />

      {/* Center Content */}
      <main className="flex-1 flex flex-col relative px-8 py-8 z-10 overflow-y-auto">
        {/* Header */}
        <header className="flex items-center justify-between mb-8 bg-zinc-900/40 backdrop-blur-xl border border-zinc-800 rounded-2xl p-4 shadow-lg">
          <div className="flex items-center gap-4">
            <Link href="/">
              <button className="p-2 bg-surface-elevated hover:bg-accent/20 hover:text-accent rounded-xl text-text-secondary transition-all border border-border hover:border-accent/30">
                <ChevronLeft className="w-5 h-5" />
              </button>
            </Link>
            <div>
              <h1 className="text-xl font-bold tracking-widest text-text-primary font-mono uppercase flex items-center gap-2">
                <Video className="w-5 h-5 text-accent" /> Test Lab
              </h1>
              <p className="text-xs text-text-dim font-mono tracking-wider mt-1">
                Video Ingestion & AI Model Playground
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button className="p-2 bg-surface-elevated text-text-secondary rounded-xl hover:text-text-primary transition-colors border border-border">
              <Settings2 className="w-5 h-5" />
            </button>
            <button
              disabled={!selectedFile}
              onClick={async () => {
                if (!selectedFile) return;
                setIsScanning(true);
                setHasDetected(false);
                try {
                  // Simulate 2 seconds of scanning
                  setTimeout(async () => {
                    setIsScanning(false);
                    setHasDetected(true);

                    if (testMeta) {
                      const payload = {
                        incident_number: `INC-TEST-${Math.floor(Math.random() * 10000)}`,
                        camera_id: testMeta.camera_id,
                        zone_id: testMeta.zone_id,
                        threat_type_id: testMeta.threat_type_id,
                        severity: "HIGH",
                        ai_confidence: 0.98,
                        ai_model_version: "sentinel-cv-v1",
                        detected_at: new Date().toISOString(),
                        gps_latitude: 15.1394,
                        gps_longitude: 76.9242,
                        summary: "AI Detected Incident in Ballari"
                      };

                      try {
                        const API_BASE = "http://127.0.0.1:8000/api/v1";
                        const response = await fetch(`${API_BASE}/incidents`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify(payload)
                        });

                        if (response.ok) {
                          console.log("Pushed incident to global feed.");
                          setShowToast(true);
                          setTimeout(() => setShowToast(false), 5000); // Hide toast after 5s
                        } else {
                          const errorData = await response.json();
                          console.error("Backend rejected incident payload:", errorData);
                        }
                      } catch (e: any) {
                        console.error("Failed to push incident", e);
                      }
                    }
                  }, 2000);
                } catch (err) {
                  console.error("Inference error:", err);
                  setIsScanning(false);
                  alert("Error triggering inference.");
                }
              }}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl font-bold font-mono text-sm transition-colors ${selectedFile
                  ? "bg-accent text-background hover:bg-accent-muted shadow-[0_0_15px_rgba(6,182,212,0.3)]"
                  : "bg-surface-elevated text-text-dim cursor-not-allowed border border-border"
                }`}
            >
              <PlayCircle className="w-4 h-4" /> RUN INFERENCE
            </button>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-full min-h-0">

          {/* Left Column: Video Upload */}
          <section className="flex flex-col gap-4">
            <h2 className="text-sm font-bold font-mono tracking-widest text-text-secondary uppercase">
              Data Source
            </h2>
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                  const file = e.dataTransfer.files[0];
                  setSelectedFile(file);
                  setVideoUrl(URL.createObjectURL(file));
                  setHasDetected(false);
                }
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`flex-1 flex flex-col items-center justify-center border-2 border-dashed rounded-3xl transition-all cursor-pointer ${isDragging
                  ? "border-accent bg-accent/5"
                  : selectedFile
                    ? "border-success/50 bg-success/5 hover:bg-success/10"
                    : "border-zinc-800 bg-zinc-900/40 backdrop-blur-xl hover:border-accent/30 hover:bg-zinc-900/60"
                }`}
            >
              <input
                type="file"
                id="video-upload"
                ref={fileInputRef}
                hidden
                accept="video/*"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    const file = e.target.files[0];
                    setSelectedFile(file);
                    setVideoUrl(URL.createObjectURL(file));
                    setHasDetected(false);
                  }
                }}
              />

              {selectedFile ? (
                <>
                  <div className="p-6 bg-success/20 rounded-full border border-success/30 shadow-[0_0_20px_rgba(16,185,129,0.3)] mb-6">
                    <Video className="w-10 h-10 text-success" />
                  </div>
                  <h3 className="text-lg font-bold text-success mb-2">Ready for Inference</h3>
                  <p className="text-sm text-text-primary font-mono text-center max-w-xs mb-6 truncate px-4">
                    {selectedFile.name}
                  </p>
                  <button className="px-6 py-2.5 bg-surface-elevated border border-border text-text-primary font-mono text-xs font-bold rounded-xl hover:bg-zinc-800 transition-all">
                    CHANGE FILE
                  </button>
                </>
              ) : (
                <>
                  <div className="p-6 bg-surface-elevated rounded-full border border-border shadow-xl mb-6 group-hover:scale-105 transition-transform">
                    <UploadCloud className="w-10 h-10 text-accent" />
                  </div>
                  <h3 className="text-lg font-bold text-text-primary mb-2">Drag & Drop Media</h3>
                  <p className="text-sm text-text-dim font-mono text-center max-w-xs mb-6">
                    Upload CCTV footage or sample video clips (.mp4, .avi) for AI threat detection processing.
                  </p>
                  <button className="px-6 py-2.5 bg-surface-elevated border border-border text-text-primary font-mono text-xs font-bold rounded-xl hover:bg-accent hover:border-accent hover:text-background transition-all">
                    BROWSE FILES
                  </button>
                </>
              )}
            </div>
          </section>

          {/* Right Column: Live Detection Canvas Placeholder */}
          <section className="flex flex-col gap-4">
            <h2 className="text-sm font-bold font-mono tracking-widest text-text-secondary uppercase flex justify-between items-center">
              <span>Detection Canvas</span>
              <span className="flex items-center gap-1.5 text-[10px] text-text-dim">
                <span className="relative flex h-2 w-2">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isScanning ? 'bg-danger' : 'bg-warning'}`}></span>
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${isScanning ? 'bg-danger' : 'bg-warning'}`}></span>
                </span>
                {isScanning ? 'SCANNING' : 'STANDBY'}
              </span>
            </h2>

            <div className="flex-1 bg-[#0a0a0a] rounded-3xl border border-zinc-800 shadow-[inset_0_0_50px_rgba(0,0,0,0.8)] relative overflow-hidden flex flex-col items-center justify-center">
              {/* Scanline Effect */}
              <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:100%_4px] pointer-events-none z-10 opacity-20"></div>
              {isScanning && <div className="absolute top-0 left-0 right-0 h-1 bg-accent/30 blur-sm animate-[scanline_3s_linear_infinite] z-20"></div>}

              {videoUrl ? (
                <video src={videoUrl} controls autoPlay loop className="absolute inset-0 w-full h-full object-cover z-0" />
              ) : (
                <>
                  <Video className="w-16 h-16 text-white/5 mb-4" />
                  <p className="text-text-dim font-mono text-xs tracking-[0.2em] uppercase">
                    Awaiting Video Input
                  </p>
                </>
              )}

              {isScanning && (
                <div className="absolute top-[20%] left-[20%] w-[60%] h-[60%] border-2 border-warning rounded-md z-20 shadow-[0_0_15px_rgba(234,179,8,0.5)] flex items-start justify-start pointer-events-none">
                  <div className="bg-warning text-black text-[10px] font-mono px-1 m-1">SCANNING...</div>
                </div>
              )}

              {hasDetected && !isScanning && (
                <div className="absolute top-[20%] left-[25%] w-[45%] h-[40%] border-2 border-danger rounded-md z-20 shadow-[0_0_15px_rgba(239,68,68,0.5)] flex items-start justify-start pointer-events-none">
                  <div className="bg-danger text-white text-[10px] font-mono px-1 m-1">ACCIDENT DETECTED</div>
                </div>
              )}

              {hasDetected && !isScanning && (
                <div className="absolute bottom-16 right-6 w-64 bg-zinc-900/90 backdrop-blur-xl border border-zinc-800 rounded-xl p-3 z-30 shadow-2xl">
                  <p className="text-[10px] uppercase tracking-wider text-text-dim font-bold mb-2">Top 3 Nearest Responders</p>
                  <div className="flex flex-col gap-1.5">
                    <div className="flex justify-between items-center bg-zinc-800/50 rounded-md px-2 py-1.5">
                      <span className="text-xs text-text-primary">City Hospital</span>
                      <span className="text-[10px] font-mono text-accent bg-accent/10 px-1.5 py-0.5 rounded-full">1.2 km</span>
                    </div>
                    <div className="flex justify-between items-center bg-zinc-800/50 rounded-md px-2 py-1.5">
                      <span className="text-xs text-text-primary">Metro Police Dept</span>
                      <span className="text-[10px] font-mono text-accent bg-accent/10 px-1.5 py-0.5 rounded-full">2.4 km</span>
                    </div>
                    <div className="flex justify-between items-center bg-zinc-800/50 rounded-md px-2 py-1.5">
                      <span className="text-xs text-text-primary">Fire Station #4</span>
                      <span className="text-[10px] font-mono text-accent bg-accent/10 px-1.5 py-0.5 rounded-full">3.1 km</span>
                    </div>
                  </div>
                </div>
              )}

              <div className="absolute bottom-6 left-6 right-6 flex justify-between items-end z-30 pointer-events-none">
                <div className="bg-zinc-900/80 backdrop-blur-md px-3 py-1.5 rounded-lg border border-zinc-800">
                  <p className="text-[10px] font-mono text-accent tracking-widest">FPS: {videoUrl ? '30' : '--'}</p>
                  <p className="text-[10px] font-mono text-text-dim tracking-widest">RES: {videoUrl ? '1080P' : '--'}</p>
                </div>
                <div className="bg-zinc-900/80 backdrop-blur-md px-3 py-1.5 rounded-lg border border-zinc-800 text-right">
                  <p className="text-[10px] font-mono text-text-secondary tracking-widest">SENTINEL-CV-V1</p>
                  <p className={`text-[10px] font-mono tracking-widest ${isScanning ? 'text-warning animate-pulse' : hasDetected ? 'text-danger' : 'text-success'}`}>
                    {isScanning ? 'SCANNING' : hasDetected ? 'DETECTED' : 'IDLE'}
                  </p>
                </div>
              </div>
            </div>
          </section>

        </div>
      </main>

      {/* Success Toast */}
      {showToast && (
        <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-success/20 backdrop-blur-xl border border-success/50 text-success px-6 py-3 rounded-2xl shadow-[0_0_20px_rgba(16,185,129,0.2)] flex items-center gap-3 z-50 animate-in slide-in-from-bottom-5">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
          <span className="font-mono text-sm font-bold tracking-widest">INCIDENT SYNCHRONIZED TO GLOBAL FEED</span>
        </div>
      )}
    </div>
  );
}
