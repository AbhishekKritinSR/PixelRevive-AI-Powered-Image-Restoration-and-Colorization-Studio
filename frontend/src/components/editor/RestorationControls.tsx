import React from "react";
import {
  Sliders,
  Feather,
  Paintbrush,
  Sun,
  Sparkles,
  Wand2,
  Maximize2,
  ScanFace,
  Eye,
} from "lucide-react";
import { RestorationOptions, ModelRegistryItem } from "../../types/api";

interface RestorationControlsProps {
  options: RestorationOptions;
  onChange: (options: RestorationOptions) => void;
  disabled?: boolean;
  isModelReady?: boolean;
  availableModels?: ModelRegistryItem[];
  onPreviewMask?: () => void;
  isPreviewingMask?: boolean;
}

export const RestorationControls: React.FC<RestorationControlsProps> = ({
  options,
  onChange,
  disabled = false,
  isModelReady = true,
  availableModels = [],
  onPreviewMask,
  isPreviewingMask = false,
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
                {(options.inpaint_method ?? "lama") === "lama" ? "LaMa AI" : "OpenCV"}
              </span>
            </div>
            <div className="option-desc">
              Detects linear scratches and physical surface defects, reconstructing damaged pixels using deep AI or PDE inpainting.
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

        {/* Sub-option: Inpainting Engine Selection */}
        {options.repair && (
          <div
            className="sub-option-container"
            onClick={(e) => e.stopPropagation()}
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Inpainting Engine
              </label>
              <span className="badge badge-accent" style={{ fontSize: "0.625rem" }}>
                {(options.inpaint_method ?? "lama") === "lama" ? "Deep AI (FFC)" : "OpenCV PDE"}
              </span>
            </div>
            <select
              className="select-input"
              value={options.inpaint_method || "lama"}
              disabled={disabled}
              onChange={(e) => updateStringOption("inpaint_method", e.target.value)}
              aria-label="Select Inpainting Engine"
            >
              <option value="lama">LaMa Deep AI – Fast Fourier Convolutions (Recommended)</option>
              <option value="telea">OpenCV Fast Marching (Telea)</option>
              <option value="ns">OpenCV Navier-Stokes (Fluid Dynamics)</option>
            </select>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)" }}>
              {(options.inpaint_method ?? "lama") === "lama"
                ? "Deep neural inpainting with global receptive field; cleanly eliminates wide diagonal scratches without edge blur."
                : "Classical partial differential equation inpainting; optimal for fine hairline scratches."}
            </div>

            {onPreviewMask && (
              <button
                type="button"
                className="btn btn-outline"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "0.375rem",
                  marginTop: "0.35rem",
                  padding: "0.35rem 0.6rem",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  borderColor: "var(--border-subtle)",
                  color: "var(--text-primary)",
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  onPreviewMask();
                }}
                disabled={disabled || isPreviewingMask}
                aria-label="Preview Damage Mask"
              >
                <Eye size={13} color="var(--accent-primary)" />
                <span>{isPreviewingMask ? "Detecting Scratches..." : "Preview Damage Mask & Overlay"}</span>
              </button>
            )}
          </div>
        )}

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

        {/* Sub-option: Adaptive Contrast Safeguard */}
        {options.contrast && (
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
                Adaptive Dynamic Range Safeguard
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)" }}>
                Auto-bypasses CLAHE when natural contrast distribution is already adequate. Disable to force contrast recovery.
              </div>
            </div>
            <label className="switch">
              <input
                type="checkbox"
                checked={options.adaptive_contrast ?? true}
                disabled={disabled}
                onChange={() =>
                  onChange({
                    ...options,
                    adaptive_contrast: !(options.adaptive_contrast ?? true),
                  })
                }
                aria-label="Toggle Adaptive Contrast Safeguard"
              />
              <span className="slider" />
            </label>
          </div>
        )}

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

        {/* Sub-option: Adaptive Edge Safeguard */}
        {options.sharpen && (
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
                Adaptive Edge Safeguard
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)" }}>
                Auto-bypasses sharpening on already-crisp or noisy photographs. Disable to force edge sharpening.
              </div>
            </div>
            <label className="switch">
              <input
                type="checkbox"
                checked={options.adaptive_sharpen ?? true}
                disabled={disabled}
                onChange={() =>
                  onChange({
                    ...options,
                    adaptive_sharpen: !(options.adaptive_sharpen ?? true),
                  })
                }
                aria-label="Toggle Adaptive Edge Safeguard"
              />
              <span className="slider" />
            </label>
          </div>
        )}

        {/* ============================================================= */}
        {/* 5. Face Detail Enhancement (Identity-Preserving)              */}
        {/* ============================================================= */}
        <div
          className={`option-item ${options.face_restore ? "active" : ""}`}
          onClick={() => toggleOption("face_restore")}
          style={{ cursor: disabled ? "not-allowed" : "pointer" }}
        >
          <div className="option-info">
            <div className="option-title">
              <ScanFace size={15} color="var(--accent-primary)" />
              <span>Face Detail Enhancement</span>
              <span className="badge badge-outline" style={{ fontSize: "0.625rem" }}>
                Identity-Safe
              </span>
            </div>
            <div className="option-desc">
              Locates facial landmarks and applies localized adaptive contrast and edge sharpening while preserving identity.
            </div>
          </div>
          <label className="switch" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={options.face_restore ?? false}
              disabled={disabled}
              onChange={() => toggleOption("face_restore")}
              aria-label="Toggle Face Detail Enhancement"
            />
            <span className="slider" />
          </label>
        </div>

        {/* ============================================================= */}
        {/* 6. AI Colorization & Render Factor Tuning (Phase 5.5)         */}
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

            {/* Chroma Saturation Slider */}
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
                  Chroma Saturation
                </label>
                <span
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: "var(--accent-primary)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {Math.round((options.color_saturation ?? 0.85) * 100)}%
                  <span style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", marginLeft: "0.25rem" }}>
                    {(options.color_saturation ?? 0.85) <= 0.75 ? "(Muted)" : (options.color_saturation ?? 0.85) >= 1.0 ? "(Vivid)" : "(Natural)"}
                  </span>
                </span>
              </div>

              <input
                type="range"
                min="0.5"
                max="1.3"
                step="0.05"
                value={options.color_saturation ?? 0.85}
                disabled={disabled}
                onChange={(e) => updateNumericOption("color_saturation", parseFloat(e.target.value))}
                style={{ width: "100%", accentColor: "var(--accent-primary)", cursor: "pointer" }}
                aria-label="Chroma Saturation Slider"
              />

              <div style={{ display: "flex", gap: "0.25rem", marginTop: "0.35rem" }}>
                {[
                  { label: "Muted (70%)", val: 0.7 },
                  { label: "Natural (85%)", val: 0.85 },
                  { label: "Full (100%)", val: 1.0 },
                  { label: "Vivid (115%)", val: 1.15 },
                ].map((preset) => (
                  <button
                    key={preset.val}
                    type="button"
                    className={`btn ${
                      Math.abs((options.color_saturation ?? 0.85) - preset.val) < 0.02
                        ? "btn-secondary"
                        : "btn-outline"
                    }`}
                    style={{
                      flex: 1,
                      padding: "0.2rem 0.35rem",
                      fontSize: "0.6875rem",
                      justifyContent: "center",
                      borderColor:
                        Math.abs((options.color_saturation ?? 0.85) - preset.val) < 0.02
                          ? "var(--accent-primary)"
                          : undefined,
                      color:
                        Math.abs((options.color_saturation ?? 0.85) - preset.val) < 0.02
                          ? "var(--accent-primary)"
                          : undefined,
                    }}
                    onClick={() => updateNumericOption("color_saturation", preset.val)}
                    disabled={disabled}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Color Balance (Temperature) Slider */}
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
                  Color Balance (Temperature)
                </label>
                <span
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: "var(--accent-primary)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {(options.color_temperature ?? 0.0) > 0 ? "+" : ""}
                  {(options.color_temperature ?? 0.0).toFixed(1)}
                  <span style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", marginLeft: "0.25rem" }}>
                    {(options.color_temperature ?? 0.0) === 0 ? "(Neutral)" : (options.color_temperature ?? 0.0) > 0 ? "(Warm Amber)" : "(Cool Slate)"}
                  </span>
                </span>
              </div>

              <input
                type="range"
                min="-1.0"
                max="1.0"
                step="0.1"
                value={options.color_temperature ?? 0.0}
                disabled={disabled}
                onChange={(e) => updateNumericOption("color_temperature", parseFloat(e.target.value))}
                style={{ width: "100%", accentColor: "var(--accent-primary)", cursor: "pointer" }}
                aria-label="Color Temperature Slider"
              />

              <div style={{ display: "flex", gap: "0.25rem", marginTop: "0.35rem" }}>
                {[
                  { label: "Cool (-0.4)", val: -0.4 },
                  { label: "Neutral (0.0)", val: 0.0 },
                  { label: "Warm (+0.4)", val: 0.4 },
                ].map((preset) => (
                  <button
                    key={preset.val}
                    type="button"
                    className={`btn ${
                      Math.abs((options.color_temperature ?? 0.0) - preset.val) < 0.05
                        ? "btn-secondary"
                        : "btn-outline"
                    }`}
                    style={{
                      flex: 1,
                      padding: "0.2rem 0.35rem",
                      fontSize: "0.6875rem",
                      justifyContent: "center",
                      borderColor:
                        Math.abs((options.color_temperature ?? 0.0) - preset.val) < 0.05
                          ? "var(--accent-primary)"
                          : undefined,
                      color:
                        Math.abs((options.color_temperature ?? 0.0) - preset.val) < 0.05
                          ? "var(--accent-primary)"
                          : undefined,
                    }}
                    onClick={() => updateNumericOption("color_temperature", preset.val)}
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
        {/* 7. AI Super-Resolution Upscaling (Phase 5.4)                 */}
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
                {(options.sr_model ?? "fsrcnn") === "realesrgan" ? "Real-ESRGAN" : "FSRCNN"}
              </span>
            </div>
            <div className="option-desc">
              Neural upscaling magnifies photograph resolution by 2× or 4×, reconstructing fine spatial details.
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

        {/* Super-Resolution Scale & Architecture Selection */}
        {options.upscale && (
          <div
            className="sub-option-container"
            onClick={(e) => e.stopPropagation()}
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.625rem",
            }}
          >
            {/* Model Architecture */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.25rem" }}>
                <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-primary)" }}>
                  Upscaling Model Architecture
                </label>
              </div>
              <select
                className="select-input"
                value={options.sr_model || "fsrcnn"}
                disabled={disabled}
                onChange={(e) => updateStringOption("sr_model", e.target.value)}
                aria-label="Select Upscaling Model Architecture"
              >
                <option value="fsrcnn">FSRCNN – Fast Super-Resolution CNN (Lightweight)</option>
                <option value="realesrgan">Real-ESRGAN x4+ – Deep Residual Network (High Quality)</option>
              </select>
            </div>

            {/* Magnification Scale */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                paddingTop: "0.25rem",
              }}
            >
              <div>
                <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-primary)" }}>
                  Magnification Scale
                </div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)" }}>
                  {(options.sr_model ?? "fsrcnn") === "realesrgan" && (options.scale ?? 2) === 2
                    ? "Native 4× inference with 2× Lanczos downsampling"
                    : "Target output multiplier"}
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
          </div>
        )}
      </div>
    </div>
  );
};
