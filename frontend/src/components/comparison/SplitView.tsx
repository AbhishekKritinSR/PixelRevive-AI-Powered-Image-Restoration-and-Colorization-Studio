import React from "react";

interface SplitViewProps {
  originalUrl: string;
  processedUrl: string;
}

export const SplitView: React.FC<SplitViewProps> = ({ originalUrl, processedUrl }) => {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "0.875rem" }}>
      <div className="card" style={{ padding: "0.75rem" }}>
        <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", marginBottom: "0.5rem" }}>
          Original Input
        </div>
        <div style={{ background: "var(--bg-subtle)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)", overflow: "hidden" }}>
          <img
            src={originalUrl}
            alt="Original"
            style={{ width: "100%", maxHeight: "450px", objectFit: "contain", display: "block" }}
          />
        </div>
      </div>

      <div className="card" style={{ padding: "0.75rem" }}>
        <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--accent-primary)", textTransform: "uppercase", marginBottom: "0.5rem" }}>
          Restored Output
        </div>
        <div style={{ background: "var(--bg-subtle)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)", overflow: "hidden" }}>
          <img
            src={processedUrl}
            alt="Restored"
            style={{ width: "100%", maxHeight: "450px", objectFit: "contain", display: "block" }}
          />
        </div>
      </div>
    </div>
  );
};
