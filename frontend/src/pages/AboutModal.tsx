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
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="about-dialog-title">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "1rem",
            borderBottom: "1px solid var(--border-subtle)",
            paddingBottom: "0.75rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
            <div className="logo-badge" style={{ width: "30px", height: "30px" }}>
              <Sparkles size={16} />
            </div>
            <div>
              <div id="about-dialog-title" style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)" }}>
                About PixelRevive
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)" }}>
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
              display: "flex",
              alignItems: "center",
            }}
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "0.875rem",
            fontSize: "0.8125rem",
            color: "var(--text-secondary)",
            lineHeight: "1.5",
          }}
        >
          <p>
            <strong style={{ color: "var(--text-primary)" }}>PixelRevive</strong> is a modular computer vision
            application designed to analyze, restore, and colorize damaged, noisy, and vintage monochrome photographs.
          </p>

          <div
            style={{
              background: "var(--bg-subtle)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              padding: "0.875rem",
            }}
          >
            <div
              style={{
                fontWeight: 600,
                color: "var(--text-primary)",
                marginBottom: "0.5rem",
                display: "flex",
                alignItems: "center",
                gap: "0.4rem",
                fontSize: "0.75rem",
                textTransform: "uppercase",
              }}
            >
              <Layers size={14} color="var(--accent-primary)" />
              <span>Core Image Restoration Architecture</span>
            </div>
            <ul
              style={{
                paddingLeft: "1.25rem",
                display: "flex",
                flexDirection: "column",
                gap: "0.35rem",
                fontSize: "0.75rem",
              }}
            >
              <li>
                <strong style={{ color: "var(--text-primary)" }}>Image Analysis:</strong> Blind
                Laplacian noise estimation, edge sharpness analysis, contrast dynamics, and monochrome detection.
              </li>
              <li>
                <strong style={{ color: "var(--text-primary)" }}>Adaptive Denoising:</strong> Non-Local
                Means filtering with automatic noise-aware parameter scaling ($h \in [3, 15]$).
              </li>
              <li>
                <strong style={{ color: "var(--text-primary)" }}>Archival Scratch Repair:</strong> Morphological
                defect detection and OpenCV inpainting to eliminate physical cracks, dust spots, and handling creases.
              </li>
              <li>
                <strong style={{ color: "var(--text-primary)" }}>Contrast & Sharpening:</strong> CLAHE on CIELAB L
                channel and Laplacian unsharp masking.
              </li>
              <li>
                <strong style={{ color: "var(--text-primary)" }}>AI Colorization & Model Registry:</strong> Deep
                learning colorization (Zhang et al. ECCV 2016) with extensible model registry and render factor tuning.
              </li>
              <li>
                <strong style={{ color: "var(--text-primary)" }}>AI Super-Resolution:</strong> FSRCNN
                neural network upscaling by 2× or 4×.
              </li>
              <li>
                <strong style={{ color: "var(--text-primary)" }}>Quality Assessment Dashboard:</strong> BRISQUE
                natural scene statistics distortion, SSIM structural fidelity, and Hasler–Süsstrunk Colorfulness.
              </li>
            </ul>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
            <div
              style={{
                background: "var(--bg-subtle)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                padding: "0.625rem",
              }}
            >
              <div
                style={{
                  fontSize: "0.6875rem",
                  color: "var(--text-secondary)",
                  textTransform: "uppercase",
                  fontWeight: 600,
                }}
              >
                Backend Framework
              </div>
              <div
                style={{
                  fontSize: "0.875rem",
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
                background: "var(--bg-subtle)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                padding: "0.625rem",
              }}
            >
              <div
                style={{
                  fontSize: "0.6875rem",
                  color: "var(--text-secondary)",
                  textTransform: "uppercase",
                  fontWeight: 600,
                }}
              >
                Execution Engine
              </div>
              <div
                style={{
                  fontSize: "0.875rem",
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
            <button className="btn btn-secondary" onClick={onClose} style={{ padding: "0.35rem 0.875rem", fontSize: "0.8125rem" }}>
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
