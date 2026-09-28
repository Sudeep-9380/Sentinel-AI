const resources = [
  { name: "Emergency Beds", available: 48 },
  { name: "ICU Beds", available: 10 },
  { name: "Ventilators", available: 8 },
  { name: "Blood Units", available: 120 },
];

export default function HospitalResources() {
  return (
    <div className="rounded-2xl bg-slate-900 p-6">
      <h2 className="text-xl font-bold text-green-400 mb-4">
        Hospital Resources
      </h2>

      {resources.map((r) => (
        <div
          key={r.name}
          className="flex justify-between py-3 border-b border-slate-800"
        >
          <span>{r.name}</span>
          <span className="text-green-400">{r.available}</span>
        </div>
      ))}
    </div>
  );
}