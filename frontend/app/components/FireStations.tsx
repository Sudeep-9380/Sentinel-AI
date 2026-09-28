const stations = [
  { id: 1, name: "Central Station", trucks: 6 },
  { id: 2, name: "North Station", trucks: 5 },
  { id: 3, name: "South Station", trucks: 4 },
  { id: 4, name: "East Station", trucks: 9 },
];

export default function FireStations() {
  return (
    <div className="rounded-2xl bg-slate-900 p-6">

      <h2 className="text-xl font-bold text-red-400 mb-4">
        Fire Stations
      </h2>

      {stations.map((station) => (
        <div
          key={station.id}
          className="flex justify-between py-3 border-b border-slate-800"
        >
          <span>{station.name}</span>

          <span className="text-orange-400">
            🚒 {station.trucks}
          </span>
        </div>
      ))}

    </div>
  );
}