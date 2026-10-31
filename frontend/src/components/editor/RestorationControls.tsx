import React from "react";
import {
  Sliders,
  Feather,
  Paintbrush,
  Sun,
  Sparkles,
  Wand2,
  Maximize2,
} from "lucide-react";
import { RestorationOptions, ModelRegistryItem } from "../../types/api";

interface RestorationControlsProps {
  options: RestorationOptions;
  onChange: (options: RestorationOptions) => void;
  disabled?: boolean;
  isModelReady?: boolean;
  availableModels?: ModelRegistryItem[];
}

export const RestorationControls: React.FC<RestorationControlsProps> = ({
  options,
  onChange,
  disabled = false,
  isModelReady = true,
  availableModels = [],
}) => {
  const toggleOption = (key: keyof RestorationOptions) => {
    if (disabled) return;
    onChange({
      ...options,
      [key]: !options[key],
    });
  };

  const updateNumericOption = (key: keyof RestorationOptions, value: number) => {
    if (disabled) return;
    onChange({
      ...options,
      [key]: value,
    });
  };

  const updateStringOption = (key: keyof RestorationOptions, value: string) => {
    if (disabled) return;
    onChange({
      ...options,
      [key]: value,
    });
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          <Sliders size={16} color="var(--accent-primary)" />
          <span>Restoration Settings</span>
        </div>
      </div>

      <div className="options-group">
        {/* ============================================================= */}
        {/* 1. Denoise & Adaptive Denoising                               */}
        {/* ============================================================= */}
        <div
          className={`option-item ${options.denoise ? "active" : ""}`}
          onClick={() => toggleOption("denoise")}
          style={{ cursor: disabled ? "not-allowed" : "pointer" }}
        >
          <div className="option-info">
            <div className="option-title">
              <Feather size={15} color="var(--accent-primary)" />
              <span>Denoising</span>
            </div>
            <div className="option-desc">
              Non-Local Means filter suppresses grain and photographic noise while retaining edge sharpness.
            </div>
          </div>
          <label className="switch" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={options.denoise}
              disabled={disabled}
              onChange={() => toggleOption("denoise")}
              aria-label="Toggle Denoising"
            />
            <span className="slider" />
          </label>
        </div>

        {/* Sub-option: Adaptive Noise Denoising (Phase 5.2) */}
        {options.denoise && (
          <div
            className="sub-option-container"
            onClick={(e) => e.stopPropagation()}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "0.75rem",
            }}
          >
            <div>
              <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Adaptive Noise Calibration
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)" }}>
                Auto-tunes filter strength based on estimated noise standard deviation ($\sigma$).
              </div>
            </div>
            <label className="switch">
              <input
                type="checkbox"
                checked={options.adaptive_denoise ?? true}
                disabled={disabled}
                onChange={() =>
                  onChange({
                    ...options,
                    adaptive_denoise: !(options.adaptive_denoise ?? true),
                  })
                }
                aria-label="Toggle Adaptive Noise Calibration"
              />
              <span className="slider" />
            </label>
          </div>
        )}

        {/* ============================================================= */}
        {/* 2. Archival Scratch Repair & Inpainting (Phase 5.3)           */}
        {/* ============================================================= */}
        <div
          className={`option-item ${options.repair ? "active" : ""}`}
          onClick={() => toggleOption("repair")}
          style={{ cursor: disabled ? "not-allowed" : "pointer" }}
        >
          <div className="option-info">
            <div className="option-title">
              <Paintbrush size={15} color="var(--success)" />
              <span>Scratch Repair & Inpainting</span>
              <span className="badge badge-outline" style={{ fontSize: "0.625rem" }}>
                Archival
              </span>
            </div>
            <div className="option-desc">
              Detects linear scratches and physical surface defects, reconstructing damaged pixels using OpenCV inpainting.
            </div>
          </div>
          <label className="switch" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={options.repair ?? false}
              disabled={disabled}
              onChange={() => toggleOption("repair")}
              aria-label="Toggle Scratch Repair"
            />
            <span className="slider" />
          </label>
        </div>

        {/* ============================================================= */}
        {/* 3. Contrast Recovery (CLAHE)                                 */}
        {/* ============================================================= */}
        <div
          className={`option-item ${options.contrast ? "active" : ""}`}
          onClick={() => toggleOption("contrast")}
          style={{ cursor: disabled ? "not-allowed" : "pointer" }}
        >
          <div className="option-info">
            <div className="option-title">
              <Sun size={15} color="var(--warning)" />
              <span>Contrast Enhancement (CLAHE)</span>
            </div>
            <div className="option-desc">
              Contrast Limited Adaptive Histogram Equalization recovers faded dynamic range in highlights and shadows.
            </div>
          </div>
          <label className="switch" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={options.contrast}
              disabled={disabled}
              onChange={() => toggleOption("contrast")}
              aria-label="Toggle Contrast Enhancement"
            />
            <span className="slider" />
          </label>
        </div>

        {/* ============================================================= */}
        {/* 4. Laplacian Sharpening                                       */}
        {/* ============================================================= */}
        <div
          className={`option-item ${options.sharpen ? "active" : ""}`}
          onClick={() => toggleOption("sharpen")}
          style={{ cursor: disabled ? "not-allowed" : "pointer" }}
        >
          <div className="option-info">
            <div className="option-title">
              <Sparkles size={15} color="var(--accent-primary)" />
              <span>Sharpening</span>
            </div>
            <div className="option-desc">
              Laplacian unsharp masking enhances soft transitions and fine contours without altering luminance.
            </div>
          </div>
          <label className="switch" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={options.sharpen}
              disabled={disabled}
              onChange={() => toggleOption("sharpen")}
              aria-label="Toggle Sharpening"
            />
            <span className="slider" />
          </label>
        </div>

        {/* ============================================================= */}
        {/* 5. AI Colorization & Render Factor Tuning (Phase 5.5)         */}
        {/* ============================================================= */}
        <div
          className={`option-item ${options.colorize ? "active" : ""}`}
          onClick={() => toggleOption("colorize")}
          style={{ cursor: disabled ? "not-allowed" : "pointer" }}
        >
          <div className="option-info">
            <div className="option-title">
              <Wand2 size={15} color="var(--accent-primary)" />
              <span>AI Colorization</span>
              {!isModelReady && (
                <span className="badge badge-warning" style={{ fontSize: "0.625rem" }}>
                  Loading Weights
                </span>
              )}
            </div>
            <div className="option-desc">
              Deep convolutional network predicts plausible chromatic distributions for monochrome images.
            </div>
          </div>
          <label className="switch" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={options.colorize}
              disabled={disabled}
              onChange={() => toggleOption("colorize")}
              aria-label="Toggle AI Colorization"
            />
            <span className="slider" />
          </label>
        </div>

        {/* Colorization Tuning Sub-Panel */}
        {options.colorize && (
          <div
            className="sub-option-container"
            onClick={(e) => e.stopPropagation()}
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.625rem",
            }}
          >
            {/* Model Selection */}
            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "0.25rem",
                }}
              >
                <label
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: "var(--text-primary)",
                  }}
                >
                  Model Architecture
                </label>
              </div>
              <select
                className="select-input"
                value={options.colorization_model || "zhang_caffe"}
                disabled={disabled}
                onChange={(e) => updateStringOption("colorization_model", e.target.value)}
                aria-label="Select Colorization Model"
              >
                {availableModels.length > 0 ? (
                  availableModels.map((m) => (
                    <option key={m.model_id} value={m.model_id}>
                      {m.display_name} {m.is_default ? "(Default)" : ""}
                    </option>
                  ))
                ) : (
                  <option value="zhang_caffe">Zhang et al. ECCV 2016 Caffe (Default)</option>
                )}
              </select>
            </div>

            {/* Render Factor Slider */}
            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "0.25rem",
                }}
              >
                <label
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: "var(--text-primary)",
                  }}
                >
                  Render Factor
                </label>
                <span
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: "var(--accent-primary)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {options.render_factor ?? 14}
                  <span style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", marginLeft: "0.25rem" }}>
                    ({(options.render_factor ?? 14) * 16}×{(options.render_factor ?? 14) * 16} grid)
                  </span>
                </span>
              </div>

              <input
                type="range"
                min="10"
                max="40"
                step="1"
                value={options.render_factor ?? 14}
                disabled={disabled}
                onChange={(e) => updateNumericOption("render_factor", parseInt(e.target.value, 10))}
                style={{ width: "100%", accentColor: "var(--accent-primary)", cursor: "pointer" }}
                aria-label="Render Factor Slider"
              />

              {/* Presets */}
              <div style={{ display: "flex", gap: "0.25rem", marginTop: "0.35rem" }}>
                {[
                  { label: "Fast", val: 12 },
                  { label: "Standard (14)", val: 14 },
                  { label: "Detailed", val: 24 },
                  { label: "Max HD", val: 36 },
                ].map((preset) => (
                  <button
                    key={preset.val}
                    type="button"
                    className={`btn ${
                      (options.render_factor ?? 14) === preset.val ? "btn-secondary" : "btn-outline"
                    }`}
                    style={{
                      flex: 1,
                      padding: "0.2rem 0.35rem",
                      fontSize: "0.6875rem",
                      justifyContent: "center",
                      borderColor:
                        (options.render_factor ?? 14) === preset.val
                          ? "var(--accent-primary)"
                          : undefined,
                      color:
                        (options.render_factor ?? 14) === preset.val
                          ? "var(--accent-primary)"
                          : undefined,
                    }}
                    onClick={() => updateNumericOption("render_factor", preset.val)}
                    disabled={disabled}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ============================================================= */}
        {/* 6. AI Super-Resolution Upscaling (Phase 5.4)                 */}
        {/* ============================================================= */}
        <div
          className={`option-item ${options.upscale ? "active" : ""}`}
          onClick={() => toggleOption("upscale")}
          style={{ cursor: disabled ? "not-allowed" : "pointer" }}
        >
          <div className="option-info">
            <div className="option-title">
              <Maximize2 size={15} color="var(--accent-primary)" />
              <span>AI Super-Resolution</span>
              <span className="badge badge-outline" style={{ fontSize: "0.625rem" }}>
                FSRCNN
              </span>
            </div>
            <div className="option-desc">
              FSRCNN neural upscaling magnifies photograph resolution by 2× or 4×, reconstructing fine spatial details.
            </div>
          </div>
          <label className="switch" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={options.upscale ?? false}
              disabled={disabled}
              onChange={() => toggleOption("upscale")}
              aria-label="Toggle Super-Resolution"
            />
            <span className="slider" />
          </label>
        </div>

        {/* Super-Resolution Scale Selection */}
        {options.upscale && (
          <div
            className="sub-option-container"
            onClick={(e) => e.stopPropagation()}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div>
              <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Magnification Scale
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)" }}>
                Select target upscaling multiplier.
              </div>
            </div>

            <div style={{ display: "flex", gap: "0.25rem" }}>
              <button
                type="button"
                className={`btn ${(options.scale ?? 2) === 2 ? "btn-primary" : "btn-secondary"}`}
                style={{ padding: "0.25rem 0.625rem", fontSize: "0.75rem" }}
                onClick={() => updateNumericOption("scale", 2)}
                disabled={disabled}
              >
                2× Scale
              </button>
              <button
                type="button"
                className={`btn ${(options.scale ?? 2) === 4 ? "btn-primary" : "btn-secondary"}`}
                style={{ padding: "0.25rem 0.625rem", fontSize: "0.75rem" }}
                onClick={() => updateNumericOption("scale", 4)}
                disabled={disabled}
              >
                4× Scale
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
