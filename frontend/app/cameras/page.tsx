"use client";

import {
    useCallback,
    useEffect,
    useRef,
    useState,
} from "react";

import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE!;

interface LiveDetection {
    detected: boolean;
    detections: any[];
    threat?: any;
    incident_created?: boolean;
    incident?: any;
    cooldown?: boolean;
    cooldown_remaining?: number;
    incident_error?: string;
}

export default function CamerasPage() {
    const router = useRouter();

    // =====================================================
    // UPLOAD VIDEO
    // =====================================================

    const [video, setVideo] = useState<File | null>(null);
    const [preview, setPreview] = useState("");
    const [processing, setProcessing] = useState(false);
    const [result, setResult] = useState<any>(null);

    // =====================================================
    // CAMERA
    // =====================================================

    const webcamRef = useRef<HTMLVideoElement | null>(null);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const streamRef = useRef<MediaStream | null>(null);

    const [cameraOpen, setCameraOpen] = useState(false);
    const [cameraError, setCameraError] = useState("");

    // =====================================================
    // LIVE DETECTION
    // =====================================================

    const [liveDetection, setLiveDetection] =
        useState<LiveDetection | null>(null);

    const [liveProcessing, setLiveProcessing] =
        useState(false);

    const liveLoopRef = useRef(false);

    // =====================================================
    // START CAMERA
    // =====================================================

    const startCamera = async () => {
        try {
            setCameraError("");
            setLiveDetection(null);

            if (
                !navigator.mediaDevices ||
                !navigator.mediaDevices.getUserMedia
            ) {
                setCameraError(
                    "Camera access is not supported by this browser."
                );
                return;
            }

            // Stop old stream if one exists
            if (streamRef.current) {
                streamRef.current
                    .getTracks()
                    .forEach((track) => track.stop());

                streamRef.current = null;
            }

            // Request laptop webcam
            const stream =
                await navigator.mediaDevices.getUserMedia({
                    video: {
                        width: {
                            ideal: 1280,
                        },
                        height: {
                            ideal: 720,
                        },
                        facingMode: "user",
                    },
                    audio: false,
                });

            streamRef.current = stream;

            /*
             * IMPORTANT:
             * Do NOT attach stream here.
             *
             * setCameraOpen() renders the <video> element first.
             * Another useEffect below attaches the stream after rendering.
             */
            setCameraOpen(true);

        } catch (error) {
            console.error(
                "Camera access error:",
                error
            );

            setCameraOpen(false);

            if (error instanceof DOMException) {
                if (error.name === "NotAllowedError") {
                    setCameraError(
                        "Camera permission was denied. Allow camera access in the browser and try again."
                    );
                } else if (error.name === "NotFoundError") {
                    setCameraError(
                        "No laptop camera was found."
                    );
                } else if (error.name === "NotReadableError") {
                    setCameraError(
                        "The camera is already being used by another application."
                    );
                } else if (error.name === "AbortError") {
                    setCameraError(
                        "Camera startup was interrupted. Please try again."
                    );
                } else {
                    setCameraError(
                        `Camera error: ${error.message}`
                    );
                }
            } else {
                setCameraError(
                    "Unable to access the laptop camera."
                );
            }
        }
    };

    // =====================================================
    // ATTACH CAMERA STREAM AFTER VIDEO ELEMENT EXISTS
    // =====================================================

    useEffect(() => {
        if (!cameraOpen) {
            return;
        }

        const videoElement = webcamRef.current;
        const stream = streamRef.current;

        if (!videoElement || !stream) {
            console.error(
                "Video element or camera stream is missing."
            );
            return;
        }

        videoElement.srcObject = stream;

        const playVideo = async () => {
            try {
                await videoElement.play();
                console.log(
                    "Camera 1 started successfully."
                );
            } catch (error) {
                console.error(
                    "Video play error:",
                    error
                );

                setCameraError(
                    "Camera opened but video could not start. Please check browser permissions."
                );
            }
        };

        if (videoElement.readyState >= 2) {
            playVideo();
        } else {
            videoElement.onloadedmetadata = () => {
                playVideo();
            };
        }

        return () => {
            videoElement.onloadedmetadata = null;
        };
    }, [cameraOpen]);

    // =====================================================
    // STOP CAMERA
    // =====================================================

    const stopCamera = useCallback(() => {
        liveLoopRef.current = false;

        if (streamRef.current) {
            streamRef.current
                .getTracks()
                .forEach((track) => {
                    track.stop();
                });

            streamRef.current = null;
        }

        if (webcamRef.current) {
            webcamRef.current.pause();
            webcamRef.current.srcObject = null;
        }

        setCameraOpen(false);
        setLiveProcessing(false);
        setLiveDetection(null);
    }, []);

    // =====================================================
    // CLEANUP WHEN PAGE CLOSES
    // =====================================================

    useEffect(() => {
        return () => {
            liveLoopRef.current = false;

            if (streamRef.current) {
                streamRef.current
                    .getTracks()
                    .forEach((track) => {
                        track.stop();
                    });

                streamRef.current = null;
            }

            if (webcamRef.current) {
                webcamRef.current.pause();
                webcamRef.current.srcObject = null;
            }
        };
    }, []);

    // =====================================================
    // CAPTURE CAMERA FRAME
    // =====================================================

    const captureCameraFrame =
        async (): Promise<Blob | null> => {
            const videoElement =
                webcamRef.current;

            const canvas =
                canvasRef.current;

            if (
                !videoElement ||
                !canvas
            ) {
                return null;
            }

            if (
                videoElement.videoWidth === 0 ||
                videoElement.videoHeight === 0
            ) {
                return null;
            }

            // Smaller image = faster detection
            const width = 640;

            const height = Math.round(
                videoElement.videoHeight *
                (width /
                    videoElement.videoWidth)
            );

            canvas.width = width;
            canvas.height = height;

            const context =
                canvas.getContext("2d");

            if (!context) {
                return null;
            }

            context.drawImage(
                videoElement,
                0,
                0,
                width,
                height
            );

            return new Promise(
                (resolve) => {
                    canvas.toBlob(
                        (blob) => {
                            resolve(blob);
                        },
                        "image/jpeg",
                        0.75
                    );
                }
            );
        };

    // =====================================================
    // SEND CAMERA FRAME TO YOLO
    // =====================================================

    const detectCameraFrame =
        useCallback(async () => {
            if (!cameraOpen) {
                return;
            }

            if (liveProcessing) {
                return;
            }

            try {
                setLiveProcessing(true);

                const blob =
                    await captureCameraFrame();

                if (!blob) {
                    return;
                }

                const formData =
                    new FormData();

                formData.append(
                    "file",
                    blob,
                    "camera1.jpg"
                );

                const response =
                    await fetch(
                        `${API_BASE}/detect/frame`,
                        {
                            method: "POST",
                            body: formData,
                        }
                    );

                if (!response.ok) {
                    const text =
                        await response.text();

                    throw new Error(
                        text ||
                        "Live detection failed"
                    );
                }

                const data =
                    await response.json();

                console.log(
                    "Live detection:",
                    data
                );

                setLiveDetection(data);

            } catch (error) {
                console.error(
                    "Live detection error:",
                    error
                );
            } finally {
                setLiveProcessing(false);
            }
        }, [
            cameraOpen,
            liveProcessing,
        ]);

    // =====================================================
    // CONTINUOUS YOLO DETECTION
    // =====================================================

    useEffect(() => {
        if (!cameraOpen) {
            liveLoopRef.current = false;
            return;
        }

        liveLoopRef.current = true;

        let timeoutId:
            ReturnType<
                typeof setTimeout
            > | null = null;

        const loop = async () => {
            if (!liveLoopRef.current) {
                return;
            }

            await detectCameraFrame();

            if (!liveLoopRef.current) {
                return;
            }

            // Detect approximately once per second
            timeoutId = setTimeout(
                loop,
                1000
            );
        };

        loop();

        return () => {
            liveLoopRef.current = false;

            if (timeoutId) {
                clearTimeout(timeoutId);
            }
        };
    }, [
        cameraOpen,
        detectCameraFrame,
    ]);

    // =====================================================
    // SELECT CCTV VIDEO
    // =====================================================

    const handleFileChange = (
        e: React.ChangeEvent<HTMLInputElement>
    ) => {
        const file =
            e.target.files?.[0];

        if (!file) {
            return;
        }

        setVideo(file);

        if (preview) {
            URL.revokeObjectURL(preview);
        }

        const videoUrl =
            URL.createObjectURL(file);

        setPreview(videoUrl);
        setResult(null);
    };

    // =====================================================
    // UPLOAD CCTV VIDEO
    // =====================================================

    const uploadVideo = async () => {
        if (!video) {
            alert(
                "Please choose a video first."
            );
            return;
        }

        try {
            setProcessing(true);
            setResult(null);

            const formData =
                new FormData();

            formData.append(
                "file",
                video
            );

            const response =
                await fetch(
                    `${API_BASE}/detect/video`,
                    {
                        method: "POST",
                        body: formData,
                    }
                );

            const data =
                await response.json();

            if (!response.ok) {
                alert(
                    JSON.stringify(data)
                );
                return;
            }

            setResult(data);

        } catch (error) {
            console.error(
                "Upload Error:",
                error
            );

            if (
                error instanceof Error
            ) {
                alert(
                    error.message
                );
            } else {
                alert(
                    String(error)
                );
            }
        } finally {
            setProcessing(false);
        }
    };

    // =====================================================
    // RENDER
    // =====================================================

    return (
        <div className="min-h-screen bg-slate-950 p-6 text-white">

            {/* HEADER */}

            <div className="mb-5 flex items-center justify-between">

                <div>
                    <h1 className="text-3xl font-bold text-cyan-400">
                        📹 Camera Monitoring
                    </h1>

                    <p className="mt-1 text-sm text-slate-400">
                        Live Camera 1 detection and CCTV video analysis
                    </p>
                </div>

                <button
                    onClick={() =>
                        router.push("/")
                    }
                    className="rounded-xl border border-slate-700 bg-slate-800 px-5 py-3 font-semibold transition hover:bg-slate-700"
                >
                    ← Main Dashboard
                </button>

            </div>

            {/* =================================================
                UPLOAD CCTV VIDEO
            ================================================= */}

            <div className="mb-5 rounded-2xl border border-slate-700 bg-slate-900 p-5">

                <h2 className="mb-4 text-xl font-bold">
                    📁 Upload CCTV Video
                </h2>

                <div className="flex flex-wrap items-center gap-4">

                    <label
                        htmlFor="video-upload"
                        className="cursor-pointer rounded-xl border-2 border-cyan-400 bg-cyan-500/10 px-5 py-3 font-semibold text-cyan-300 transition hover:bg-cyan-500/20"
                    >
                        📁 Choose CCTV Video
                    </label>

                    <input
                        id="video-upload"
                        type="file"
                        accept="video/*"
                        onChange={
                            handleFileChange
                        }
                        className="hidden"
                    />

                    <button
                        onClick={
                            uploadVideo
                        }
                        disabled={
                            processing ||
                            !video
                        }
                        className="rounded-xl bg-cyan-600 px-5 py-3 font-semibold transition hover:bg-cyan-500 disabled:cursor-not-allowed disabled:bg-slate-700"
                    >
                        {processing
                            ? "🔄 Detecting..."
                            : "🚨 Upload & Detect"}
                    </button>

                </div>

                {video && (
                    <div className="mt-3 text-sm text-green-400">
                        ✅ Selected:{" "}
                        {video.name}
                    </div>
                )}

                {preview && (
                    <video
                        src={preview}
                        controls
                        className="mt-4 max-h-[300px] w-full rounded-xl border border-slate-700 bg-black object-contain"
                    />
                )}

            </div>

            {/* =================================================
                CAMERA 1
            ================================================= */}

            <div className="mb-5 rounded-2xl border border-cyan-800 bg-slate-900 p-5">

                {/* CAMERA HEADER */}

                <div className="mb-4 flex items-center justify-between">

                    <div>
                        <h2 className="text-xl font-bold text-cyan-400">
                            📹 Camera 1
                        </h2>

                        <p className="mt-1 text-sm text-slate-400">
                            Laptop Camera + Real-Time YOLO Detection
                        </p>
                    </div>

                    <div className="flex items-center gap-2">

                        <span
                            className={`h-3 w-3 rounded-full ${cameraOpen
                                ? "bg-green-400"
                                : "bg-red-400"
                                }`}
                        />

                        <span
                            className={
                                cameraOpen
                                    ? "font-bold text-green-400"
                                    : "font-bold text-red-400"
                            }
                        >
                            {cameraOpen
                                ? "ONLINE"
                                : "OFFLINE"}
                        </span>

                    </div>

                </div>

                {/* CAMERA VIEW */}

                {cameraOpen ? (

                    <div className="relative overflow-hidden rounded-xl border border-slate-700 bg-black">

                        <video
                            ref={webcamRef}
                            autoPlay
                            playsInline
                            muted
                            className="block h-auto max-h-[450px] min-h-[300px] w-full bg-black object-contain"
                        />

                        {/* LIVE BADGE */}

                        <div className="absolute left-3 top-3 flex items-center gap-2 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-bold">

                            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-white" />

                            LIVE

                        </div>

                        {/* AI SCANNING */}

                        {liveProcessing && (
                            <div className="absolute right-3 top-3 rounded-lg bg-black/70 px-3 py-1.5 text-xs text-cyan-300">
                                🔄 AI SCANNING
                            </div>
                        )}

                    </div>

                ) : (

                    <div className="flex h-[180px] items-center justify-center rounded-xl border border-slate-700 bg-slate-950">

                        <div className="text-center">

                            <div className="mb-2 text-4xl">
                                📹
                            </div>

                            <p className="font-semibold text-slate-300">
                                Camera 1 is OFFLINE
                            </p>

                            <p className="mt-1 text-xs text-slate-500">
                                Click Open Camera 1 to start your laptop webcam.
                            </p>

                        </div>

                    </div>

                )}

                {/* CAMERA ERROR */}

                {cameraError && (
                    <div className="mt-3 rounded-lg border border-red-700 bg-red-950/40 p-3 text-sm text-red-300">
                        ⚠️ {cameraError}
                    </div>
                )}

                {/* CAMERA BUTTON */}

                <div className="mt-4">

                    {!cameraOpen ? (

                        <button
                            onClick={
                                startCamera
                            }
                            className="rounded-xl bg-green-600 px-6 py-3 font-bold transition hover:bg-green-500"
                        >
                            📹 Open Camera 1
                        </button>

                    ) : (

                        <button
                            onClick={
                                stopCamera
                            }
                            className="rounded-xl bg-red-600 px-6 py-3 font-bold transition hover:bg-red-500"
                        >
                            ⏹ Stop Camera 1
                        </button>

                    )}

                </div>

                {/* =================================================
                    LIVE DETECTION RESULT
                ================================================= */}

                {liveDetection && (

                    <div className="mt-5 rounded-xl border border-slate-700 bg-slate-950 p-4">

                        {!liveDetection.detected ? (

                            <div className="text-center">

                                <p className="font-semibold text-green-400">
                                    ✅ No Emergency Detected
                                </p>

                                <p className="mt-1 text-xs text-slate-500">
                                    Camera 1 is being monitored by YOLO
                                </p>

                            </div>

                        ) : (

                            <div>

                                <div className="flex items-center justify-between">

                                    <h3 className="text-xl font-bold text-red-400">

                                        🚨{" "}

                                        {liveDetection.threat?.summary ||
                                            "Emergency Detected"}

                                    </h3>

                                    <span className="rounded-full bg-red-600 px-3 py-1 text-xs font-bold">

                                        {liveDetection.threat?.code ||
                                            "UNKNOWN"}

                                    </span>

                                </div>

                                <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-3">

                                    {/* CONFIDENCE */}

                                    <div className="rounded-lg bg-slate-800 p-3">

                                        <p className="text-xs text-slate-400">
                                            Confidence
                                        </p>

                                        <p className="font-bold text-cyan-400">

                                            {(
                                                (liveDetection.threat?.confidence ||
                                                    0) *
                                                100
                                            ).toFixed(1)}

                                            %

                                        </p>

                                    </div>

                                    {/* SEVERITY */}

                                    <div className="rounded-lg bg-slate-800 p-3">

                                        <p className="text-xs text-slate-400">
                                            Severity
                                        </p>

                                        <p className="font-bold text-red-400">
                                            {liveDetection.threat?.severity ||
                                                "N/A"}
                                        </p>

                                    </div>

                                    {/* STATUS */}

                                    <div className="rounded-lg bg-slate-800 p-3">

                                        <p className="text-xs text-slate-400">
                                            Status
                                        </p>

                                        <p className="font-bold text-green-400">

                                            {liveDetection.incident_created
                                                ? "INCIDENT CREATED"
                                                : liveDetection.cooldown
                                                    ? "MONITORING"
                                                    : "DETECTED"}

                                        </p>

                                    </div>

                                </div>

                                {/* LOCATION */}

                                {liveDetection.incident && (

                                    <div className="mt-4 border-t border-slate-700 pt-4">

                                        <p className="font-bold text-cyan-400">
                                            📍 Incident Location
                                        </p>

                                        <p className="mt-2 text-sm text-slate-300">

                                            Latitude:{" "}

                                            {liveDetection.incident.latitude ??
                                                liveDetection.incident.gps_latitude ??
                                                "N/A"}

                                            <br />

                                            Longitude:{" "}

                                            {liveDetection.incident.longitude ??
                                                liveDetection.incident.gps_longitude ??
                                                "N/A"}

                                        </p>

                                        {liveDetection.incident_created && (
                                            <p className="mt-2 font-semibold text-green-400">
                                                🚨 Incident saved and responders dispatched
                                            </p>
                                        )}

                                    </div>

                                )}

                                {/* COOLDOWN */}

                                {liveDetection.cooldown && (

                                    <p className="mt-3 text-xs text-yellow-400">

                                        Same threat detected. New incident creation paused for{" "}
                                        {liveDetection.cooldown_remaining ??
                                            0}{" "}
                                        seconds.

                                    </p>

                                )}

                                {/* INCIDENT ERROR */}

                                {liveDetection.incident_error && (

                                    <p className="mt-3 rounded-lg bg-red-950 p-3 text-xs text-red-300">

                                        ⚠️{" "}
                                        {liveDetection.incident_error}

                                    </p>

                                )}

                            </div>

                        )}

                    </div>

                )}

            </div>

            {/* HIDDEN CANVAS */}

            <canvas
                ref={canvasRef}
                className="hidden"
            />

            {/* =================================================
                UPLOADED VIDEO RESULT
            ================================================= */}

            {result && (

                <div className="rounded-2xl border border-green-600 bg-slate-900 p-5">

                    <h2 className="mb-5 text-xl font-bold text-green-400">
                        🚨 Detection Result
                    </h2>

                    {result.results &&
                        result.results.length > 0 ? (

                        <div className="text-center">

                            <h3 className="text-3xl font-bold text-red-500">

                                🚨{" "}

                                {
                                    result.results[0]
                                        .incident
                                        ?.summary ||
                                    "Emergency Detected"
                                }

                            </h3>

                            <p className="mt-3 text-lg">

                                <strong>
                                    Type:
                                </strong>{" "}

                                {
                                    result.results[0]
                                        .incident
                                        ?.code ||
                                    "N/A"
                                }

                            </p>

                            <p className="text-lg">

                                <strong>
                                    Severity:
                                </strong>{" "}

                                {
                                    result.results[0]
                                        .incident
                                        ?.severity ||
                                    "N/A"
                                }

                            </p>

                            <p className="text-lg">

                                <strong>
                                    Confidence:
                                </strong>{" "}

                                {(
                                    (result.results[0]
                                        .incident
                                        ?.confidence ||
                                        0) *
                                    100
                                ).toFixed(1)}
                                %

                            </p>

                            {/* LOCATION */}

                            <div className="mt-5 border-t border-slate-700 pt-4">

                                <p className="text-lg font-bold text-cyan-400">
                                    📍 Location
                                </p>

                                <p className="mt-2 text-slate-300">

                                    <strong>
                                        Latitude:
                                    </strong>{" "}

                                    {
                                        result.results[0]
                                            .incident
                                            ?.gps_latitude ??
                                        result.results[0]
                                            .incident
                                            ?.latitude ??
                                        "N/A"
                                    }

                                </p>

                                <p className="text-slate-300">

                                    <strong>
                                        Longitude:
                                    </strong>{" "}

                                    {
                                        result.results[0]
                                            .incident
                                            ?.gps_longitude ??
                                        result.results[0]
                                            .incident
                                            ?.longitude ??
                                        "N/A"
                                    }

                                </p>

                            </div>

                        </div>

                    ) : (

                        <h3 className="text-2xl font-bold text-green-500">
                            ✅ No Incident Detected
                        </h3>

                    )}

                </div>

            )}

        </div>
    );
}