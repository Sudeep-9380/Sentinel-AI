"use client";

import { useRouter } from "next/navigation";
import {
  FaUserShield,
  FaHospital,
  FaFire,
  FaVideo,
} from "react-icons/fa";

export default function QuickActions() {
  const router = useRouter();

  const actions = [
    {
      title: "Police",
      icon: <FaUserShield size={26} />,
      color: "bg-blue-600 hover:bg-blue-700",
      path: "/police",
    },
    {
      title: "Hospital",
      icon: <FaHospital size={26} />,
      color: "bg-green-600 hover:bg-green-700",
      path: "/hospital",
    },
    {
      title: "Fire",
      icon: <FaFire size={26} />,
      color: "bg-red-600 hover:bg-red-700",
      path: "/fire",
    },
    {
      title: "Cameras",
      icon: <FaVideo size={26} />,
      color: "bg-cyan-600 hover:bg-cyan-700",
      path: "/cameras",
    },
  ];

  return (
    <div className="grid grid-cols-4 gap-4 mt-4">
      {actions.map((action) => (
        <button
          key={action.title}
          onClick={() => router.push(action.path)}
          className={`${action.color} rounded-xl p-5 transition-all duration-300 shadow-lg hover:scale-105`}
        >
          <div className="flex flex-col items-center gap-3 text-white">
            {action.icon}
            <span className="font-semibold">{action.title}</span>
          </div>
        </button>
      ))}
    </div>
  );
}