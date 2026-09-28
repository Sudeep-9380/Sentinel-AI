"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  FaHome,
  FaUserShield,
  FaHospital,
  FaFire,
  FaVideo,
  FaChartBar,
  FaCog,
  FaRobot,
  FaDatabase,
  FaCamera,
  FaUserCircle,
} from "react-icons/fa";

const menu = [
  { name: "Dashboard", href: "/", icon: FaHome },
  { name: "Police", href: "/police", icon: FaUserShield },
  { name: "Hospital", href: "/hospital", icon: FaHospital },
  { name: "Fire", href: "/fire", icon: FaFire },
  { name: "Cameras", href: "/cameras", icon: FaVideo },
  { name: "Analytics", href: "/analytics", icon: FaChartBar },
  { name: "Settings", href: "/settings", icon: FaCog },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-72 bg-slate-950 border-r border-slate-800 flex flex-col justify-between">

      {/* Logo */}
      <div>
        <div className="p-6 border-b border-slate-800">
          <h1 className="text-3xl font-bold text-cyan-400">
            Sentinel AI
          </h1>

          <p className="text-xs text-slate-400 mt-2 tracking-widest uppercase">
            Security Command Center
          </p>
        </div>

        {/* Navigation */}
        <nav className="mt-4 px-3">
          {menu.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;

            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-4 rounded-xl px-4 py-3 mb-2 transition-all duration-200
                  ${
                    active
                      ? "bg-cyan-500 text-black font-semibold shadow-lg shadow-cyan-500/30"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
              >
                <Icon size={18} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* System Status */}
        <div className="mx-4 mt-6 rounded-xl bg-slate-900 border border-slate-800 p-4">
          <h2 className="text-sm font-semibold text-cyan-400 mb-4">
            System Status
          </h2>

          <Status icon={<FaRobot />} label="AI Engine" value="Online" />

          <Status icon={<FaDatabase />} label="Database" value="Connected" />

          <Status icon={<FaCamera />} label="Cameras" value="12 Active" />
        </div>
      </div>

      {/* User */}
      <div className="border-t border-slate-800 p-5 flex items-center gap-3">
        <FaUserCircle size={42} className="text-cyan-400" />

        <div>
          <p className="font-semibold">Administrator</p>

          <p className="text-xs text-slate-400">
            Smart City Control
          </p>
        </div>
      </div>
    </aside>
  );
}

function Status({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2 text-slate-300">
        {icon}
        <span className="text-sm">{label}</span>
      </div>

      <span className="text-green-400 text-xs font-semibold">
        {value}
      </span>
    </div>
  );
}