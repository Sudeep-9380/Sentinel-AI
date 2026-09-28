interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
}

export default function StatCard({
  title,
  value,
  subtitle,
  color = "text-cyan-400",
}: StatCardProps) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-lg hover:border-cyan-500 transition">
      <h3 className="text-sm text-slate-400 uppercase tracking-wider">
        {title}
      </h3>

      <div className={`mt-3 text-4xl font-bold ${color}`}>
        {value}
      </div>

      {subtitle && (
        <p className="mt-2 text-xs text-slate-500">
          {subtitle}
        </p>
      )}
    </div>
  );
}