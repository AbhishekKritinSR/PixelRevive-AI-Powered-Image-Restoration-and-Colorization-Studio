import React, { useState, useEffect } from "react";
import { Sparkles, Download, Layers, Columns, Image as ImageIcon, Loader2 } from "lucide-react";
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
} from "../types/api";
import {
  restoreSingleImage,
  downloadDataUri,
  fetchModelRegistry,
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
    upscale: false,
    scale: 2,
    colorization_model: "zhang_caffe",
    render_factor: 14,
  });
  const [availableModels, setAvailableModels] = useState<ModelRegistryItem[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<SingleRestorationResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"slider" | "split">("slider");

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
    setErrorMessage(null);
  };

  const handleClear = () => {
    if (originalUrl) {
      URL.revokeObjectURL(originalUrl);
    }
    setSelectedFile(null);
    setOriginalUrl(null);
    setResult(null);
    setErrorMessage(null);
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
