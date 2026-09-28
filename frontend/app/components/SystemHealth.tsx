import { Shield, Database, Activity, Cpu } from "lucide-react";

export function SystemHealth({ activeNodes = 1 }: { activeNodes?: number }) {
  return (
    <div className="flex items-center justify-center gap-4 py-4 w-full z-20">
      <div className="flex items-center gap-6 bg-surface/80 backdrop-blur-md border border-border px-8 py-3 rounded-full shadow-lg">
        
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-accent" />
          <span className="text-xs font-mono tracking-widest text-text-primary">SENTINEL</span>
        </div>

        <div className="w-px h-4 bg-border"></div>

        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-success" />
          <span className="text-xs font-mono text-text-secondary">
            AI Engine: <strong className="text-success">Online</strong>
          </span>
        </div>

        <div className="w-px h-4 bg-border"></div>

        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-success" />
          <span className="text-xs font-mono text-text-secondary">
            DB: <strong className="text-success">Connected</strong>
          </span>
        </div>

        <div className="w-px h-4 bg-border"></div>

        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-accent" />
          <span className="text-xs font-mono text-text-secondary">
            Active Nodes: <strong className="text-text-primary">{activeNodes}</strong>
          </span>
        </div>

      </div>
    </div>
  );
}
