"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  function login(e: React.FormEvent) {
    e.preventDefault();

    if (username === "admin" && password === "admin123") {
      localStorage.setItem("token", "sentinel-token");
      router.push("/");
    } else {
      alert("Invalid credentials");
    }
  }

  return (
    <div className="flex h-screen items-center justify-center bg-slate-950">

      <form
        onSubmit={login}
        className="w-[400px] rounded-2xl bg-slate-900 p-8"
      >

        <h1 className="mb-8 text-center text-3xl font-bold text-cyan-400">
          Sentinel AI Login
        </h1>

        <input
          placeholder="Username"
          className="mb-4 w-full rounded bg-slate-800 p-3"
          value={username}
          onChange={(e)=>setUsername(e.target.value)}
        />

        <input
          type="password"
          placeholder="Password"
          className="mb-6 w-full rounded bg-slate-800 p-3"
          value={password}
          onChange={(e)=>setPassword(e.target.value)}
        />

        <button
          className="w-full rounded bg-cyan-500 p-3 font-bold"
        >
          Login
        </button>

      </form>

    </div>
  );
}