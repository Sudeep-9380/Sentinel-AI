"use client";

import { useEffect, useMemo, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE!;

export default function AnalyticsPage() {
    const [incidents, setIncidents] = useState<any[]>([]);

    async function loadIncidents() {
        try {
            const res = await fetch(`${API}/incidents`);

            if (!res.ok) return;

            const data = await res.json();

            setIncidents(data);
        } catch (err) {
            console.error(err);
        }
    }

    useEffect(() => {
        loadIncidents();

        const timer = setInterval(loadIncidents, 1000);

        return () => clearInterval(timer);
    }, []);

    const analytics = useMemo(() => {
        const totalIncidents = incidents.length;

        const todayAlerts = incidents.filter((incident) => {
            return (
                new Date(incident.detected_at).toDateString() ===
                new Date().toDateString()
            );
        }).length;

        const avgAccuracy =
            incidents.length > 0
                ? Math.round(
                    (incidents.reduce(
                        (sum, incident) => sum + (incident.ai_confidence || 0),
                        0
                    ) /
                        incidents.length) *
                    100
                )
                : 0;

        const videosProcessed = new Set(
            incidents.map((i) => i.evidence_path || i.video_path || i.id)
        ).size;

        return {
            totalIncidents,
            todayAlerts,
            avgAccuracy,
            videosProcessed,
        };
    }, [incidents]);

    return (
        <div className="min-h-screen bg-slate-950 text-white p-8">

            <div className="flex justify-between items-center">

                <div>

                    <h1 className="text-4xl font-bold text-cyan-400">
                        📊 Analytics Dashboard
                    </h1>

                    <p className="text-slate-400 mt-2">
                        Real-Time AI Surveillance Analytics
                    </p>

                </div>

                <div className="flex items-center gap-2 text-green-400 font-semibold">

                    <span className="h-3 w-3 rounded-full bg-green-500 animate-pulse"></span>

                    LIVE

                </div>

            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mt-10">

                <Card
                    title="🚨 Total Incidents"
                    value={analytics.totalIncidents}
                    color="text-red-500"
                />

                <Card
                    title="⚡ Today's Alerts"
                    value={analytics.todayAlerts}
                    color="text-yellow-400"
                />

                <Card
                    title="🤖 Avg AI Confidence"
                    value={`${analytics.avgAccuracy}%`}
                    color="text-cyan-400"
                />

                <Card
                    title="🎥 Videos Processed"
                    value={analytics.videosProcessed}
                    color="text-purple-400"
                />

            </div>
        </div>
    );
}

function Card({
    title,
    value,
    color,
}: {
    title: string;
    value: string | number;
    color: string;
}) {
    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 transition hover:scale-[1.02] hover:border-cyan-500">

            <h2 className="text-lg font-semibold text-slate-300">
                {title}
            </h2>

            <p className={`text-5xl mt-5 font-bold ${color}`}>
                {value}
            </p>

        </div>
    );
}