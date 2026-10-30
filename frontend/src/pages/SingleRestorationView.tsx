import React, { useState } from "react";
import { Sparkles, Download, Layers, Columns, Image as ImageIcon, Loader2 } from "lucide-react";
import { DropZone } from "../components/upload/DropZone";
import { RestorationControls } from "../components/editor/RestorationControls";
import { ImageSlider } from "../components/comparison/ImageSlider";
import { SplitView } from "../components/comparison/SplitView";
import { QualityMetricsPanel } from "../components/metrics/QualityMetricsPanel";
import { Button } from "../components/common/Button";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { RestorationOptions, SingleRestorationResponse } from "../types/api";
import { restoreSingleImage, downloadDataUri } from "../services/api";

interface SingleRestorationViewProps {
  isModelReady: boolean;
}

export const SingleRestorationView: React.FC<SingleRestorationViewProps> = ({ isModelReady }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [originalUrl, setOriginalUrl] = useState<string | null>(null);
  const [options, setOptions] = useState<RestorationOptions>({
    denoise: true,
    contrast: true,
    sharpen: true,
    colorize: true,
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<SingleRestorationResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"slider" | "split">("slider");

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
        {/* Left Column: Upload & Configuration Controls */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <DropZone
            selectedFile={selectedFile}
            onFileSelect={handleFileSelect}
            onClear={handleClear}
            disabled={isProcessing}
          />

          <RestorationControls
            options={options}
            onChange={setOptions}
            disabled={isProcessing}
            isModelReady={isModelReady}
          />

          <Button
            variant="primary"
            block
            icon={<Sparkles size={18} />}
            isLoading={isProcessing}
            disabled={!selectedFile || isProcessing}
            onClick={handleProcess}
          >
            {options.colorize ? "Restore & Colorize" : "Apply Classical Restoration"}
          </Button>
        </div>

        {/* Right Column: Comparison, Results & Metrics */}
        <div>
          {isProcessing ? (
            <div
              className="card"
              style={{
                minHeight: "480px",
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
                  width: "64px",
                  height: "64px",
                  borderRadius: "50%",
                  background: "rgba(99, 102, 241, 0.12)",
                  color: "var(--accent-primary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Loader2 size={32} className="spinner" />
              </div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700 }}>
                Applying Computer Vision Pipeline...
              </div>
              <div style={{ color: "var(--text-muted)", fontSize: "0.875rem", maxWidth: "340px" }}>
                Running Non-Local Means denoising, CLAHE contrast equalization, Laplacian sharpening,
                and Caffe deep convolutional colorization.
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
                  marginBottom: "1rem",
                  flexWrap: "wrap",
                  gap: "0.75rem",
                }}
              >
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button
                    className={`btn ${viewMode === "slider" ? "btn-secondary" : "btn-outline"}`}
                    style={{ padding: "0.4rem 0.8rem", fontSize: "0.8125rem" }}
                    onClick={() => setViewMode("slider")}
                  >
                    <Layers size={14} />
                    <span>Comparison Slider</span>
                  </button>
                  <button
                    className={`btn ${viewMode === "split" ? "btn-secondary" : "btn-outline"}`}
                    style={{ padding: "0.4rem 0.8rem", fontSize: "0.8125rem" }}
                    onClick={() => setViewMode("split")}
                  >
                    <Columns size={14} />
                    <span>Side-by-Side</span>
                  </button>
                </div>

                <Button
                  variant="primary"
                  icon={<Download size={16} />}
                  onClick={handleDownload}
                  style={{ padding: "0.45rem 1rem", fontSize: "0.875rem" }}
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
                  processedLabel={options.colorize ? "Restored & Colorized" : "Restored"}
                />
              ) : (
                <SplitView
                  originalUrl={originalUrl}
                  processedUrl={result.image_base64}
                />
              )}

              {/* Quality Metrics */}
              <QualityMetricsPanel
                metrics={result.metrics}
                originalWidth={result.original_width}
                originalHeight={result.original_height}
                processedWidth={result.processed_width}
                processedHeight={result.processed_height}
                wasResized={result.was_resized}
              />
            </div>
          ) : (
            <div
              className="card"
              style={{
                minHeight: "480px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
                padding: "3rem 1.5rem",
              }}
            >
              <div
                style={{
                  width: "60px",
                  height: "60px",
                  borderRadius: "50%",
                  background: "var(--bg-surface)",
                  color: "var(--text-muted)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "1.25rem",
                }}
              >
                <ImageIcon size={30} />
              </div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700, marginBottom: "0.5rem" }}>
                Interactive Restoration Workspace
              </div>
              <div style={{ color: "var(--text-muted)", fontSize: "0.875rem", maxWidth: "420px", lineHeight: "1.6" }}>
                Upload a damaged, noisy, or monochrome photograph to begin. Once processed, an interactive
                before-and-after slider will allow you to inspect pixel recovery and color transitions in real time.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

