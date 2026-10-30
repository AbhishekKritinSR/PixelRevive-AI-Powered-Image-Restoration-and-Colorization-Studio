import React from "react";
import { X, Sparkles, Layers } from "lucide-react";

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
  version?: string;
  device?: string;
}

export const AboutModal: React.FC<AboutModalProps> = ({
  isOpen,
  onClose,
  version = "1.0.0",
  device = "CPU",
}) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.25rem", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
            <div className="logo-badge" style={{ width: "32px", height: "32px" }}>
              <Sparkles size={18} />
            </div>
            <div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700 }}>About AI Photo Studio</div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Architecture & Pipeline Overview</div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-secondary)",
              cursor: "pointer",
              padding: "4px",
            }}
          >
            <X size={20} />
          </button>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "1rem", fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: "1.6" }}>
          <p>
            <strong style={{ color: "var(--text-primary)" }}>AI Photo Restoration & Colorization Studio</strong> is a modular,
            production-grade computer vision application designed to restore aged, degraded, noisy, and black-and-white
            photographs.
          </p>

          <div style={{ background: "var(--bg-surface-subtle)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
            <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Layers size={16} color="var(--accent-primary)" />
              <span>Processing Pipeline Sequence</span>
            </div>
            <ul style={{ paddingLeft: "1.25rem", display: "flex", flexDirection: "column", gap: "0.375rem" }}>
              <li>
                <strong style={{ color: "var(--text-primary)" }}>1. Denoising:</strong> OpenCV Non-Local Means (NLM) colored filter
                removes sensor noise while preserving sharp boundaries.
              </li>
              <li>
                <strong style={{ color: "var(--text-primary)" }}>2. Contrast Recovery:</strong> Contrast Limited Adaptive Histogram
                Equalization (CLAHE) on the CIELAB Lightness (L) channel restores faded dynamic range.
              </li>
              <li>
                <strong style={{ color: "var(--text-primary)" }}>3. Sharpening:</strong> Unity-gain Laplacian unsharp filter accents
                subtle details without altering local luminance.
              </li>
              <li>
                <strong style={{ color: "var(--text-primary)" }}>4. AI Colorization:</strong> Zhang, Isola, & Efros (ECCV 2016) deep
                convolutional neural network synthesizes realistic color distributions for monochrome photographs.
              </li>
            </ul>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
            <div style={{ background: "var(--bg-surface-subtle)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)", padding: "0.75rem" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>Backend Framework</div>
              <div style={{ fontSize: "0.9375rem", fontWeight: 600, color: "var(--text-primary)", marginTop: "2px" }}>FastAPI REST API v{version}</div>
            </div>
            <div style={{ background: "var(--bg-surface-subtle)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)", padding: "0.75rem" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>Execution Hardware</div>
              <div style={{ fontSize: "0.9375rem", fontWeight: 600, color: "var(--text-primary)", marginTop: "2px" }}>OpenCV ({device})</div>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "0.5rem" }}>
            <button className="btn btn-secondary" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
