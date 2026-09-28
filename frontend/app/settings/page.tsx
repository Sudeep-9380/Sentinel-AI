export default function SettingsPage() {
    return (
        <div className="min-h-screen bg-slate-950 text-white p-8">
            <h1 className="text-4xl font-bold text-cyan-400">
                Settings
            </h1>

            <p className="text-slate-400 mt-2">
                Sentinel AI configuration.
            </p>

            <div className="bg-slate-900 rounded-xl p-8 mt-10">
                <p>⚙️ AI Detection Settings</p>
                <p className="mt-4">⚙️ Camera Configuration</p>
                <p className="mt-4">⚙️ Notification Settings</p>
                <p className="mt-4">⚙️ User Management</p>
            </div>
        </div>
    );
}