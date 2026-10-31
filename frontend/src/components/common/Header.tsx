import React from "react";
import { Sparkles, Layers, Images, Info } from "lucide-react";
import { HealthResponse } from "../../types/api";

interface HeaderProps {
  activeTab: "single" | "batch";
  onTabChange: (tab: "single" | "batch") => void;
  onOpenAbout: () => void;
  health: HealthResponse | null;
  isHealthLoading: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  onOpenAbout,
  health,
  isHealthLoading,
}) => {
  const isOnline = health?.status === "healthy";

  return (
    <header className="header" role="banner">
      <div className="header-content">
        <div className="logo-area">
          <div className="logo-badge" aria-hidden="true">
            <Sparkles size={16} />
          </div>
          <div>
            <div className="logo-title">PixelRevive</div>
            <div className="logo-subtitle">AI-Powered Image Restoration</div>
          </div>
        </div>

        <nav className="nav-tabs" aria-label="Main Navigation">
          <button
            type="button"
            className={`nav-tab ${activeTab === "single" ? "active" : ""}`}
            onClick={() => onTabChange("single")}
            aria-selected={activeTab === "single"}
            role="tab"
          >
            <Layers size={15} />
            <span>Restoration</span>
          </button>
          <button
            type="button"
            className={`nav-tab ${activeTab === "batch" ? "active" : ""}`}
            onClick={() => onTabChange("batch")}
            aria-selected={activeTab === "batch"}
            role="tab"
          >
            <Images size={15} />
            <span>Batch Queue</span>
          </button>
          <button
            type="button"
            className="nav-tab"
            onClick={onOpenAbout}
            title="About PixelRevive"
          >
            <Info size={15} />
            <span>About</span>
          </button>
        </nav>

        <div className="header-status">
          {isHealthLoading ? (
            <div className="status-pill" title="Checking backend health...">
              <span className="status-dot spinner" style={{ border: "1px solid var(--text-secondary)", borderTopColor: "transparent" }} />
              <span>Connecting...</span>
            </div>
          ) : isOnline ? (
            <div className="status-pill status-online" title={`FastAPI v${health.version} active on ${health.device}`}>
              <span className="status-dot" />
              <span>Online ({health.device})</span>
            </div>
          ) : (
            <div
              className="status-pill status-offline"
              title="FastAPI backend is offline on http://127.0.0.1:8000"
            >
              <span className="status-dot" />
              <span>Backend Offline</span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
