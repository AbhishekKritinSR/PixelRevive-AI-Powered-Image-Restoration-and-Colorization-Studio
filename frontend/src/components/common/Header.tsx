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
    <header className="header">
      <div className="header-content">
        <div className="logo-area">
          <div className="logo-badge">
            <Sparkles size={20} />
          </div>
          <div>
            <div className="logo-title">PixelRevive</div>
            <div className="logo-subtitle">AI-Powered Image Restoration</div>
          </div>
        </div>

        <nav className="nav-tabs">
          <button
            className={`nav-tab ${activeTab === "single" ? "active" : ""}`}
            onClick={() => onTabChange("single")}
          >
            <Layers size={16} />
            <span>Restoration</span>
          </button>
          <button
            className={`nav-tab ${activeTab === "batch" ? "active" : ""}`}
            onClick={() => onTabChange("batch")}
          >
            <Images size={16} />
            <span>Batch Queue</span>
          </button>
          <button className="nav-tab" onClick={onOpenAbout}>
            <Info size={16} />
            <span>About</span>
          </button>
        </nav>

        <div className="header-status">
          {isHealthLoading ? (
            <div className="status-pill">
              <span className="status-dot spinner" />
              <span>Connecting...</span>
            </div>
          ) : isOnline ? (
            <div className="status-pill status-online" title={`Backend v${health.version}`}>
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
