import React from "react";
import {
  Sliders,
  Wand2,
  Sun,
  Sparkles,
  Feather,
  Paintbrush,
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
          <Sliders size={18} color="var(--accent-primary)" />
          <span>Restoration Settings</span>
        </div>
      </div>

      <div className="options-group">
        {/* 1. Denoise & Adaptive Denoising */}
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
              Non-Local Means filter removes photographic grain and sensor noise while preserving structural edges.
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

        {/* Sub-option: Adaptive Noise Denoising (Phase 5.2) */}
        {options.denoise && (
          <div
            className="sub-option-container"
            onClick={(e) => e.stopPropagation()}
            style={{
              marginLeft: "1.25rem",
              padding: "0.625rem 0.875rem",
              background: "var(--bg-surface)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "0.75rem",
            }}
          >
            <div>
              <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Adaptive Noise Scaling
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                Automatically calibrates filtering strength ($h \in [3, 15]$) based on estimated noise standard deviation.
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
              />
              <span className="slider" />
            </label>
          </div>
        )}

        {/* 2. Archival Scratch Repair & Inpainting (Phase 5.3) */}
        <div
          className={`option-item ${options.repair ? "active" : ""}`}
          onClick={() => toggleOption("repair")}
          style={{ cursor: disabled ? "not-allowed" : "pointer" }}
        >
          <div className="option-info">
            <div className="option-title">
              <Paintbrush size={16} color="#10b981" />
              <span>Archival Scratch Repair</span>
              <span className="badge badge-success" style={{ fontSize: "0.6875rem" }}>
                Phase 5.3
              </span>
            </div>
            <div className="option-desc">
              Detects physical scratches, paper cracks, dust spots, and handling creases, reconstructing missing pixels with morphological inpainting.
            </div>
          </div>
          <label className="switch" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={options.repair ?? false}
              disabled={disabled}
              onChange={() => toggleOption("repair")}
            />
            <span className="slider" />
          </label>
        </div>

        {/* 3. Contrast Recovery (CLAHE) */}
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
              Adaptive histogram equalization (CLAHE) on the L channel recovers faded details in deep shadows and highlights.
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

        {/* 4. Laplacian Sharpening */}
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
              Laplacian unsharp masking enhances soft textural transitions without shifting overall luminance balance.
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

        {/* 5. AI Colorization & Render Factor Tuning (Phase 5.5) */}
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
              Deep convolutional neural network predicts plausible vibrant colors for monochrome photographic prints.
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

        {/* Colorization Tuning Sub-Panel (Phase 5.5) */}
        {options.colorize && (
          <div
            className="sub-option-container"
            onClick={(e) => e.stopPropagation()}
            style={{
              marginLeft: "1.25rem",
              padding: "0.875rem",
              background: "var(--bg-surface)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-subtle)",
              display: "flex",
              flexDirection: "column",
              gap: "0.75rem",
            }}
          >
            {/* Model Selection */}
            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "0.35rem",
                }}
              >
                <label
                  style={{
                    fontSize: "0.8125rem",
                    fontWeight: 600,
                    color: "var(--text-primary)",
                  }}
                >
                  Neural Architecture:
                </label>
                <span
                  style={{
                    fontSize: "0.6875rem",
                    color: "var(--accent-secondary)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {options.colorization_model || "zhang_caffe"}
                </span>
              </div>
              <select
                className="select-input"
                value={options.colorization_model || "zhang_caffe"}
                disabled={disabled}
                onChange={(e) => updateStringOption("colorization_model", e.target.value)}
                style={{
                  width: "100%",
                  padding: "0.4rem 0.6rem",
                  background: "var(--bg-card)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.8125rem",
                }}
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
                    fontSize: "0.8125rem",
                    fontWeight: 600,
                    color: "var(--text-primary)",
                  }}
                >
                  Render Factor:
                </label>
                <span
                  style={{
                    fontSize: "0.8125rem",
                    fontWeight: 700,
                    color: "var(--accent-primary)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {options.render_factor ?? 14}
                  <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginLeft: "0.25rem" }}>
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
              />

              {/* Presets */}
              <div style={{ display: "flex", gap: "0.35rem", marginTop: "0.35rem" }}>
                {[
                  { label: "Fast", val: 12 },
                  { label: "Balanced (14)", val: 14 },
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
                    }}
                    onClick={() => updateNumericOption("render_factor", preset.val)}
                    disabled={disabled}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>

              <div
                style={{
                  fontSize: "0.6875rem",
                  color: "var(--text-muted)",
                  marginTop: "0.35rem",
                  lineHeight: 1.4,
                }}
              >
                14 matches native 224×224 receptive field. Higher values preserve finer chromatic transitions for large subjects.
              </div>
            </div>
          </div>
        )}

        {/* 6. AI Super-Resolution Upscaling (Phase 5.4) */}
        <div
          className={`option-item ${options.upscale ? "active" : ""}`}
          onClick={() => toggleOption("upscale")}
          style={{ cursor: disabled ? "not-allowed" : "pointer" }}
        >
          <div className="option-info">
            <div className="option-title">
              <Maximize2 size={16} color="#06b6d4" />
              <span>AI Super-Resolution</span>
              <span className="badge badge-success" style={{ fontSize: "0.6875rem" }}>
                Phase 5.4
              </span>
            </div>
            <div className="option-desc">
              FSRCNN deep learning upscales photograph resolution by 2× or 4×, reconstructing fine spatial details.
            </div>
          </div>
          <label className="switch" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={options.upscale ?? false}
              disabled={disabled}
              onChange={() => toggleOption("upscale")}
            />
            <span className="slider" />
          </label>
        </div>

        {/* Super-Resolution Scale Factor Selection */}
        {options.upscale && (
          <div
            className="sub-option-container"
            onClick={(e) => e.stopPropagation()}
            style={{
              marginLeft: "1.25rem",
              padding: "0.625rem 0.875rem",
              background: "var(--bg-surface)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div>
              <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Upscale Factor
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                Select target spatial magnification multiplier.
              </div>
            </div>

            <div style={{ display: "flex", gap: "0.35rem" }}>
              <button
                type="button"
                className={`btn ${(options.scale ?? 2) === 2 ? "btn-primary" : "btn-outline"}`}
                style={{ padding: "0.3rem 0.75rem", fontSize: "0.75rem" }}
                onClick={() => updateNumericOption("scale", 2)}
                disabled={disabled}
              >
                2× Scale
              </button>
              <button
                type="button"
                className={`btn ${(options.scale ?? 2) === 4 ? "btn-primary" : "btn-outline"}`}
                style={{ padding: "0.3rem 0.75rem", fontSize: "0.75rem" }}
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
