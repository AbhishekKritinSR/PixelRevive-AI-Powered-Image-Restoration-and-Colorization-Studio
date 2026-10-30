import React from "react";
import { Sliders, Wand2, Sun, Sparkles, Feather } from "lucide-react";
import { RestorationOptions } from "../../types/api";

interface RestorationControlsProps {
  options: RestorationOptions;
  onChange: (options: RestorationOptions) => void;
  disabled?: boolean;
  isModelReady?: boolean;
}

export const RestorationControls: React.FC<RestorationControlsProps> = ({
  options,
  onChange,
  disabled = false,
  isModelReady = true,
}) => {
  const toggleOption = (key: keyof RestorationOptions) => {
    if (disabled) return;
    onChange({
      ...options,
      [key]: !options[key],
    });
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          <Sliders size={18} color="var(--accent-primary)" />
          <span>Restoration Settings</span>
        </div>
      </div>

      <div className="options-group">
        {/* Denoise */}
        <div
          className={`option-item ${options.denoise ? "active" : ""}`}
          onClick={() => toggleOption("denoise")}
          style={{ cursor: disabled ? "not-allowed" : "pointer" }}
        >
          <div className="option-info">
            <div className="option-title">
              <Feather size={16} color="#60a5fa" />
              <span>Denoise</span>
            </div>
            <div className="option-desc">
              Non-Local Means filter removes photographic grain and sensor noise while preserving edges.
            </div>
          </div>
          <label className="switch" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={options.denoise}
              disabled={disabled}
              onChange={() => toggleOption("denoise")}
            />
            <span className="slider" />
          </label>
        </div>

        {/* Contrast */}
        <div
          className={`option-item ${options.contrast ? "active" : ""}`}
          onClick={() => toggleOption("contrast")}
          style={{ cursor: disabled ? "not-allowed" : "pointer" }}
        >
          <div className="option-info">
            <div className="option-title">
              <Sun size={16} color="#f59e0b" />
              <span>Contrast Enhancement</span>
            </div>
            <div className="option-desc">
              Adaptive histogram equalization (CLAHE) on the L channel recovers faded details in shadows and highlights.
            </div>
          </div>
          <label className="switch" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={options.contrast}
              disabled={disabled}
              onChange={() => toggleOption("contrast")}
            />
            <span className="slider" />
          </label>
        </div>

        {/* Sharpen */}
        <div
          className={`option-item ${options.sharpen ? "active" : ""}`}
          onClick={() => toggleOption("sharpen")}
          style={{ cursor: disabled ? "not-allowed" : "pointer" }}
        >
          <div className="option-info">
            <div className="option-title">
              <Sparkles size={16} color="#a855f7" />
              <span>Sharpening</span>
            </div>
            <div className="option-desc">
              Laplacian unsharp masking sharpens soft textures without shifting overall luminance balance.
            </div>
          </div>
          <label className="switch" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={options.sharpen}
              disabled={disabled}
              onChange={() => toggleOption("sharpen")}
            />
            <span className="slider" />
          </label>
        </div>

        {/* AI Colorization */}
        <div
          className={`option-item ${options.colorize ? "active" : ""}`}
          onClick={() => toggleOption("colorize")}
          style={{ cursor: disabled ? "not-allowed" : "pointer" }}
        >
          <div className="option-info">
            <div className="option-title">
              <Wand2 size={16} color="#ec4899" />
              <span>AI Colorization</span>
              {!isModelReady && (
                <span className="badge badge-pending" style={{ fontSize: "0.6875rem" }}>
                  Initializing Weights
                </span>
              )}
            </div>
            <div className="option-desc">
              Zhang et al. (ECCV 2016) deep neural network automatically predicts plausible vibrant colors for monochrome photos.
            </div>
          </div>
          <label className="switch" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={options.colorize}
              disabled={disabled}
              onChange={() => toggleOption("colorize")}
            />
            <span className="slider" />
          </label>
        </div>
      </div>
    </div>
  );
};
