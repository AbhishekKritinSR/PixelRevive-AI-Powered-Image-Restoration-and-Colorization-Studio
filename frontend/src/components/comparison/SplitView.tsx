import React from "react";

interface SplitViewProps {
  originalUrl: string;
  processedUrl: string;
}

export const SplitView: React.FC<SplitViewProps> = ({ originalUrl, processedUrl }) => {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
      <div className="card" style={{ padding: "0.75rem" }}>
        <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "0.5rem" }}>
          Original Input
        </div>
        <div style={{ background: "#000", borderRadius: "var(--radius-md)", overflow: "hidden" }}>
          <img
            src={originalUrl}
            alt="Original"
            style={{ width: "100%", maxHeight: "450px", objectFit: "contain", display: "block" }}
          />
        </div>
      </div>

      <div className="card" style={{ padding: "0.75rem" }}>
        <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--accent-primary)", textTransform: "uppercase", marginBottom: "0.5rem" }}>
          Restored Output
        </div>
        <div style={{ background: "#000", borderRadius: "var(--radius-md)", overflow: "hidden" }}>
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

