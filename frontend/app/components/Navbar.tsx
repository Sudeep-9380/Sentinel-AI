"use client";

export default function Navbar() {
  return (
    <header className="h-16 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-8">

      <div>

        <h1 className="text-2xl font-bold">

          Smart Emergency Response System

        </h1>

      </div>

      <div className="flex items-center gap-4">

        <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>

        <span>System Online</span>

        <div className="bg-cyan-500 rounded-full w-10 h-10 flex items-center justify-center">

          A

        </div>

      </div>

    </header>
  );
}