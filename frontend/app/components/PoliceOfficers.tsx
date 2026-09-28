const officers = [
  {
    id: 1,
    name: "Officer James",
    status: "Available",
  },
  {
    id: 2,
    name: "Officer Sophia",
    status: "Responding",
  },
  {
    id: 3,
    name: "Officer Daniel",
    status: "Patrolling",
  },
];

export default function PoliceOfficers() {
  return (
    <div className="rounded-2xl bg-slate-900 p-6">

      <h2 className="text-xl font-bold text-blue-400 mb-4">
        Active Officers
      </h2>

      {officers.map((officer) => (
        <div
          key={officer.id}
          className="flex justify-between py-3 border-b border-slate-800"
        >
          <span>{officer.name}</span>

          <span
            className={
              officer.status === "Available"
                ? "text-green-400"
                : officer.status === "Responding"
                ? "text-red-400"
                : "text-yellow-400"
            }
          >
            {officer.status}
          </span>
        </div>
      ))}
    </div>
  );
}