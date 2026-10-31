import React, { useState, useEffect } from "react";
import { Header } from "./components/common/Header";
import { SingleRestorationView } from "./pages/SingleRestorationView";
import { BatchRestorationView } from "./pages/BatchRestorationView";
import { AboutModal } from "./pages/AboutModal";
import { HealthResponse, ModelStatusResponse } from "./types/api";
import { fetchHealth, fetchModelStatus } from "./services/api";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"single" | "batch">("single");
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [modelStatus, setModelStatus] = useState<ModelStatusResponse | null>(null);
  const [isHealthLoading, setIsHealthLoading] = useState(true);

  const checkBackendHealth = async () => {
    try {
      const h = await fetchHealth();
      setHealth(h);
      const m = await fetchModelStatus();
      setModelStatus(m);
    } catch {
      setHealth(null);
      setModelStatus(null);
    } finally {
      setIsHealthLoading(false);
    }
  };

  useEffect(() => {
    checkBackendHealth();
    // Poll backend health every 15 seconds
    const interval = setInterval(checkBackendHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-container">
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onOpenAbout={() => setIsAboutOpen(true)}
        health={health}
        isHealthLoading={isHealthLoading}
      />

      <main className="main-content">
        {activeTab === "single" ? (
          <SingleRestorationView isModelReady={modelStatus?.ready_for_inference ?? true} />
        ) : (
          <BatchRestorationView isModelReady={modelStatus?.ready_for_inference ?? true} />
        )}
      </main>

      <footer
        style={{
          borderTop: "1px solid var(--border-primary)",
          background: "var(--bg-surface)",
          padding: "1rem 1.5rem",
          textAlign: "center",
          fontSize: "0.75rem",
          color: "var(--text-secondary)",
          marginTop: "auto",
        }}
      >
        PixelRevive – AI-Powered Image Restoration • OpenCV & Deep Learning • FastAPI & React
      </footer>

      <AboutModal
        isOpen={isAboutOpen}
        onClose={() => setIsAboutOpen(false)}
        version={health?.version}
        device={health?.device}
      />
    </div>
  );
};

export default App;
