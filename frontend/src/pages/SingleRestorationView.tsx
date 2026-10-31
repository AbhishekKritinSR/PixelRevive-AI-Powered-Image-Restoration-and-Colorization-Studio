import React, { useState, useEffect } from "react";
import { Sparkles, Download, Layers, Columns, Image as ImageIcon, Loader2, ShieldAlert } from "lucide-react";
import { DropZone } from "../components/upload/DropZone";
import { RestorationControls } from "../components/editor/RestorationControls";
import { ImageAnalysisPanel } from "../components/analysis/ImageAnalysisPanel";
import { ImageSlider } from "../components/comparison/ImageSlider";
import { SplitView } from "../components/comparison/SplitView";
import { QualityMetricsPanel } from "../components/metrics/QualityMetricsPanel";
import { QualityDashboard } from "../components/metrics/QualityDashboard";
import { Button } from "../components/common/Button";
import { ErrorBanner } from "../components/common/ErrorBanner";
import {
  RestorationOptions,
  SingleRestorationResponse,
  ModelRegistryItem,
  DamageMaskResponse,
} from "../types/api";
import {
  restoreSingleImage,
  downloadDataUri,
  fetchModelRegistry,
  previewDamageMask,
} from "../services/api";

interface SingleRestorationViewProps {
  isModelReady: boolean;
}

export const SingleRestorationView: React.FC<SingleRestorationViewProps> = ({ isModelReady }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [originalUrl, setOriginalUrl] = useState<string | null>(null);
  const [options, setOptions] = useState<RestorationOptions>({
    denoise: true,
    adaptive_denoise: true,
    contrast: true,
    sharpen: true,
    colorize: true,
    repair: false,
    inpaint_method: "lama",
    face_restore: false,
    upscale: false,
    scale: 2,
    sr_model: "fsrcnn",
    colorization_model: "zhang_caffe",
    render_factor: 14,
    color_saturation: 0.85,
    color_temperature: 0.0,
  });
  const [availableModels, setAvailableModels] = useState<ModelRegistryItem[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<SingleRestorationResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"slider" | "split">("slider");
  const [damageMaskResult, setDamageMaskResult] = useState<DamageMaskResponse | null>(null);
  const [isPreviewingMask, setIsPreviewingMask] = useState(false);
  const [maskViewMode, setMaskViewMode] = useState<"overlay" | "mask">("overlay");

  useEffect(() => {
    fetchModelRegistry()
      .then((res) => {
        if (res && res.models) {
          setAvailableModels(res.models);
        }
      })
      .catch(() => {});
  }, []);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    if (originalUrl) {
      URL.revokeObjectURL(originalUrl);
    }
    setOriginalUrl(URL.createObjectURL(file));
    setResult(null);
    setDamageMaskResult(null);
    setErrorMessage(null);
  };

  const handleClear = () => {
    if (originalUrl) {
      URL.revokeObjectURL(originalUrl);
    }
    setSelectedFile(null);
    setOriginalUrl(null);
    setResult(null);
    setDamageMaskResult(null);
    setErrorMessage(null);
  };

  const handlePreviewDamageMask = async () => {
    if (!selectedFile) return;
    setIsPreviewingMask(true);
    setErrorMessage(null);
    try {
      const res = await previewDamageMask(selectedFile);
      setDamageMaskResult(res);
      // Automatically ensure scratch repair toggle is enabled for seamless workflow
      setOptions((prev) => ({ ...prev, repair: true }));
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to generate scratch damage mask preview.");
      }
    } finally {
      setIsPreviewingMask(false);
    }
  };

  const handleApplyRecommendations = (recommended: Partial<RestorationOptions>) => {
    setOptions((prev) => ({
      ...prev,
      ...recommended,
    }));
  };

  const handleProcess = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setErrorMessage(null);

    try {
      const response = await restoreSingleImage(selectedFile, options);
      setResult(response);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("An unexpected error occurred during processing.");
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = () => {
    if (!result) return;
    const downloadName = `restored_${result.filename.replace(/\.[^/.]+$/, "")}.png`;
    downloadDataUri(result.image_base64, downloadName);
  };

  return (
    <div>
      <ErrorBanner message={errorMessage} onDismiss={() => setErrorMessage(null)} />

      <div className="workspace-grid">
        {/* Left Column: Upload, Image Analysis & Configuration Controls */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <DropZone
            selectedFile={selectedFile}
            onFileSelect={handleFileSelect}
            onClear={handleClear}
            disabled={isProcessing}
          />

          {/* Phase 5.1 Intelligent Analysis Panel */}
          {selectedFile && (
            <ImageAnalysisPanel
              file={selectedFile}
              onApplyRecommendations={handleApplyRecommendations}
              disabled={isProcessing}
            />
          )}

          {/* Restoration Controls */}
          <RestorationControls
            options={options}
            onChange={setOptions}
            disabled={isProcessing}
            isModelReady={isModelReady}
            availableModels={availableModels}
            onPreviewMask={selectedFile ? handlePreviewDamageMask : undefined}
            isPreviewingMask={isPreviewingMask}
          />

          <Button
            variant="primary"
            block
            icon={<Sparkles size={16} />}
            isLoading={isProcessing}
            disabled={!selectedFile || isProcessing}
            onClick={handleProcess}
            style={{ padding: "0.625rem 1rem", fontSize: "0.875rem", fontWeight: 600 }}
          >
            {options.colorize ? "Restore & Colorize" : "Apply Restoration Pipeline"}
          </Button>
        </div>

        {/* Right Column: Comparison, Results, Metrics & Quality Dashboard */}
        <div>
          {damageMaskResult && (
            <div className="card" style={{ marginBottom: "1rem", border: "1px solid var(--accent-subtle-border)" }}>
              <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div className="card-title" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <ShieldAlert size={16} color="var(--accent-primary)" />
                  <span>Scratch Damage Detection Preview</span>
                  <span className="badge badge-accent" style={{ fontSize: "0.6875rem" }}>
                    {damageMaskResult.detected_components} defect(s) ({damageMaskResult.coverage_percentage}% area)
                  </span>
                </div>
                <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
                  <button
                    type="button"
                    className={`btn ${maskViewMode === "overlay" ? "btn-secondary" : "btn-outline"}`}
                    style={{ padding: "0.2rem 0.5rem", fontSize: "0.6875rem" }}
                    onClick={() => setMaskViewMode("overlay")}
                  >
                    Overlay
                  </button>
                  <button
                    type="button"
                    className={`btn ${maskViewMode === "mask" ? "btn-secondary" : "btn-outline"}`}
                    style={{ padding: "0.2rem 0.5rem", fontSize: "0.6875rem" }}
                    onClick={() => setMaskViewMode("mask")}
                  >
                    Binary Mask
                  </button>
                  <button
                    type="button"
                    className="btn btn-outline"
                    style={{ padding: "0.2rem 0.5rem", fontSize: "0.6875rem" }}
                    onClick={() => setDamageMaskResult(null)}
                    title="Dismiss damage preview"
                  >
                    ✕
                  </button>
                </div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "0.75rem", background: "var(--bg-subtle)", borderRadius: "var(--radius-sm)" }}>
                <img
                  src={maskViewMode === "overlay" ? damageMaskResult.overlay_base64 : damageMaskResult.mask_base64}
                  alt="Detected Scratch Damage"
                  style={{ maxHeight: "300px", maxWidth: "100%", objectFit: "contain", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}
                />
                <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", marginTop: "0.5rem" }}>
                  {maskViewMode === "overlay"
                    ? "Red highlights indicate detected linear scratches & surface abrasions with biological landmark protection."
                    : "Binary morphological mask used to target LaMa neural Fast Fourier Convolution or Telea inpainting."}
                </div>
              </div>
            </div>
          )}

          {isProcessing ? (
            <div
              className="card"
              style={{
                minHeight: "440px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
                gap: "1rem",
              }}
            >
              <div
                style={{
                  width: "52px",
                  height: "52px",
                  borderRadius: "var(--radius-md)",
                  background: "var(--accent-subtle)",
                  border: "1px solid var(--accent-subtle-border)",
                  color: "var(--accent-primary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Loader2 size={26} className="spinner" />
              </div>
              <div>
                <div style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text-primary)" }}>
                  Processing Image Restoration...
                </div>
                <div style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", maxWidth: "380px", lineHeight: "1.5", marginTop: "0.25rem" }}>
                  Applying Non-Local Means denoising, CLAHE contrast recovery, Laplacian sharpening
                  {options.repair ? ", archival scratch inpainting" : ""}
                  {options.colorize ? ", neural deep colorization" : ""}
                  {options.upscale ? `, and FSRCNN ${options.scale ?? 2}× super-resolution` : ""}.
                </div>
              </div>
            </div>
          ) : result && originalUrl ? (
            <div>
              {/* Header with Mode Toggle & Download Button */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "0.75rem",
                  flexWrap: "wrap",
                  gap: "0.75rem",
                }}
              >
                <div style={{ display: "flex", gap: "0.35rem" }}>
                  <button
                    type="button"
                    className={`btn ${viewMode === "slider" ? "btn-secondary" : "btn-outline"}`}
                    style={{
                      padding: "0.35rem 0.75rem",
                      fontSize: "0.8125rem",
                      borderColor: viewMode === "slider" ? "var(--accent-primary)" : undefined,
                      color: viewMode === "slider" ? "var(--accent-primary)" : undefined,
                    }}
                    onClick={() => setViewMode("slider")}
                  >
                    <Layers size={14} />
                    <span>Comparison Slider</span>
                  </button>
                  <button
                    type="button"
                    className={`btn ${viewMode === "split" ? "btn-secondary" : "btn-outline"}`}
                    style={{
                      padding: "0.35rem 0.75rem",
                      fontSize: "0.8125rem",
                      borderColor: viewMode === "split" ? "var(--accent-primary)" : undefined,
                      color: viewMode === "split" ? "var(--accent-primary)" : undefined,
                    }}
                    onClick={() => setViewMode("split")}
                  >
                    <Columns size={14} />
                    <span>Side-by-Side</span>
                  </button>
                </div>

                <Button
                  variant="primary"
                  icon={<Download size={15} />}
                  onClick={handleDownload}
                  style={{ padding: "0.4rem 0.875rem", fontSize: "0.8125rem" }}
                >
                  Download Restored PNG
                </Button>
              </div>

              {/* Viewport */}
              {viewMode === "slider" ? (
                <ImageSlider
                  originalUrl={originalUrl}
                  processedUrl={result.image_base64}
                  originalLabel="Original"
                  processedLabel={
                    options.upscale
                      ? `Restored (${options.scale ?? 2}× Super-Res)`
                      : options.colorize
                      ? "Restored & Colorized"
                      : "Restored"
                  }
                />
              ) : (
                <SplitView
                  originalUrl={originalUrl}
                  processedUrl={result.image_base64}
                />
              )}

              {/* Core Quality Metrics */}
              <QualityMetricsPanel
                metrics={result.metrics}
                originalWidth={result.original_width}
                originalHeight={result.original_height}
                processedWidth={result.processed_width}
                processedHeight={result.processed_height}
                wasResized={result.was_resized}
              />

              {/* Phase 5.6 Advanced Image Quality Assessment Dashboard */}
              <QualityDashboard
                originalFile={selectedFile}
                restoredDataUri={result.image_base64}
                disabled={isProcessing}
              />
            </div>
          ) : (
            <div
              className="card"
              style={{
                minHeight: "440px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
                padding: "2.5rem 1.5rem",
              }}
            >
              <div
                style={{
                  width: "48px",
                  height: "48px",
                  borderRadius: "var(--radius-md)",
                  background: "var(--bg-subtle)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-secondary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "0.875rem",
                }}
              >
                <ImageIcon size={24} />
              </div>
              <div style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.25rem" }}>
                Image Workspace
              </div>
              <div style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", maxWidth: "380px", lineHeight: "1.5" }}>
                Upload a photograph on the left to begin restoration. Configure adaptive denoising, scratch repair, contrast recovery, and neural colorization to preview results.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
