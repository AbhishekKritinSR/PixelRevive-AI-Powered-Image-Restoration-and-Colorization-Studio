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
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "1.25rem",
            borderBottom: "1px solid var(--border-subtle)",
            paddingBottom: "1rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
            <div className="logo-badge" style={{ width: "32px", height: "32px" }}>
              <Sparkles size={18} />
            </div>
            <div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700 }}>About PixelRevive</div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                AI-Powered Image Restoration • Version {version}
              </div>
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

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "1rem",
            fontSize: "0.875rem",
            color: "var(--text-secondary)",
            lineHeight: "1.6",
          }}
        >
          <p>
            <strong style={{ color: "var(--text-primary)" }}>PixelRevive</strong> is a modular,
            production-grade computer vision application designed to analyze, restore, and colorize
            vintage, damaged, noisy, and monochrome photographs.
          </p>

          <div
            style={{
              background: "var(--bg-surface-subtle)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: "1rem",
            }}
          >
            <div
              style={{
                fontWeight: 600,
                color: "var(--text-primary)",
                marginBottom: "0.5rem",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <Layers size={16} color="var(--accent-primary)" />
              <span>Full Computer Vision Pipeline</span>
            </div>
            <ul
              style={{
                paddingLeft: "1.25rem",
                display: "flex",
                flexDirection: "column",
                gap: "0.375rem",
                fontSize: "0.8125rem",
              }}
            >
              <li>
                <strong style={{ color: "var(--text-primary)" }}>Image Analysis (Phase 5.1):</strong> Blind
                Laplacian noise estimation, edge sharpness analysis, contrast dynamics, and monochrome detection.
              </li>
              <li>
                <strong style={{ color: "var(--text-primary)" }}>Adaptive Denoising (Phase 5.2):</strong> Non-Local
                Means filtering with automatic noise-aware parameter scaling ($h \in [3, 15]$).
              </li>
              <li>
                <strong style={{ color: "var(--text-primary)" }}>Archival Scratch Repair (Phase 5.3):</strong> Morphological
                defect detection and inpainting to eliminate physical cracks, dust spots, and creases.
              </li>
              <li>
                <strong style={{ color: "var(--text-primary)" }}>Contrast & Sharpening:</strong> CLAHE on CIELAB L
                channel and Laplacian unsharp masking.
              </li>
              <li>
                <strong style={{ color: "var(--text-primary)" }}>AI Colorization & Model Registry (Phase 5.5):</strong> Deep
                learning colorization (Zhang et al. ECCV 2016) with extensible model registry and render factor tuning.
              </li>
              <li>
                <strong style={{ color: "var(--text-primary)" }}>AI Super-Resolution (Phase 5.4):</strong> FSRCNN
                neural network upscaling by 2× or 4×.
              </li>
              <li>
                <strong style={{ color: "var(--text-primary)" }}>Quality Assessment Dashboard (Phase 5.6):</strong> BRISQUE
                natural scene statistics distortion, SSIM structural fidelity, and Hasler–Süsstrunk Colorfulness.
              </li>
            </ul>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
            <div
              style={{
                background: "var(--bg-surface-subtle)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                padding: "0.75rem",
              }}
            >
              <div
                style={{
                  fontSize: "0.75rem",
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                  fontWeight: 700,
                }}
              >
                Backend Framework
              </div>
              <div
                style={{
                  fontSize: "0.9375rem",
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  marginTop: "2px",
                }}
              >
                FastAPI REST API v{version}
              </div>
            </div>
            <div
              style={{
                background: "var(--bg-surface-subtle)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                padding: "0.75rem",
              }}
            >
              <div
                style={{
                  fontSize: "0.75rem",
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                  fontWeight: 700,
                }}
              >
                Execution Engine
              </div>
              <div
                style={{
                  fontSize: "0.9375rem",
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  marginTop: "2px",
                }}
              >
                OpenCV ({device})
              </div>
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
