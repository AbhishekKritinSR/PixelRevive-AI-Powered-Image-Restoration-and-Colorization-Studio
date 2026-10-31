import React, { useState, useEffect } from "react";
import { Images, Play, FileArchive, CheckCircle2 } from "lucide-react";
import { BatchDropZone } from "../components/batch/BatchDropZone";
import { BatchQueue, BatchFileEntry } from "../components/batch/BatchQueue";
import { RestorationControls } from "../components/editor/RestorationControls";
import { Button } from "../components/common/Button";
import { ErrorBanner } from "../components/common/ErrorBanner";
import {
  RestorationOptions,
  BatchRestorationResponse,
  ModelRegistryItem,
} from "../types/api";
import {
  restoreBatchImages,
  downloadDataUri,
  fetchModelRegistry,
} from "../services/api";

interface BatchRestorationViewProps {
  isModelReady: boolean;
}

export const BatchRestorationView: React.FC<BatchRestorationViewProps> = ({ isModelReady }) => {
  const [entries, setEntries] = useState<BatchFileEntry[]>([]);
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
  const [batchResponse, setBatchResponse] = useState<BatchRestorationResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchModelRegistry()
      .then((res) => {
        if (res && res.models) {
          setAvailableModels(res.models);
        }
      })
      .catch(() => {});
  }, []);

  const handleFilesAdded = (newFiles: File[]) => {
    const newEntries: BatchFileEntry[] = newFiles.map((f) => ({
      id: `${f.name}_${Date.now()}_${Math.random()}`,
      file: f,
      previewUrl: URL.createObjectURL(f),
    }));
    setEntries((prev) => [...prev, ...newEntries]);
    setBatchResponse(null);
    setErrorMessage(null);
  };

  const handleRemove = (id: string) => {
    setEntries((prev) => {
      const target = prev.find((e) => e.id === id);
      if (target) {
        URL.revokeObjectURL(target.previewUrl);
      }
      return prev.filter((e) => e.id !== id);
    });
  };

  const handleClearAll = () => {
    entries.forEach((e) => URL.revokeObjectURL(e.previewUrl));
    setEntries([]);
    setBatchResponse(null);
    setErrorMessage(null);
  };

  const handleProcessBatch = async () => {
    if (entries.length === 0) return;

    setIsProcessing(true);
    setErrorMessage(null);

    try {
      const filesToProcess = entries.map((e) => e.file);
      const response = await restoreBatchImages(filesToProcess, options);
      setBatchResponse(response);

      // Match returned results to entries by filename
      setEntries((prev) =>
        prev.map((entry) => {
          const matchedResult = response.items.find(
            (item) => item.filename === entry.file.name
          );
          return {
            ...entry,
            result: matchedResult,
          };
        })
      );
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Batch processing failed unexpectedly.");
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownloadZip = () => {
    if (!batchResponse?.zip_base64) return;
    downloadDataUri(batchResponse.zip_base64, "restored_batch_archive.zip");
  };

  return (
    <div>
      <ErrorBanner message={errorMessage} onDismiss={() => setErrorMessage(null)} />

      <div className="workspace-grid">
        {/* Left Column: Dropzone & Global Batch Controls */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div className="card">
            <div className="card-header">
              <div className="card-title">
                <Images size={16} color="var(--accent-primary)" />
                <span>Batch Upload</span>
              </div>
            </div>

            <BatchDropZone
              currentCount={entries.length}
              maxFiles={10}
              onFilesAdded={handleFilesAdded}
              disabled={isProcessing}
            />
          </div>

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
            icon={<Play size={16} />}
            isLoading={isProcessing}
            disabled={entries.length === 0 || isProcessing}
            onClick={handleProcessBatch}
            style={{ padding: "0.625rem 1rem", fontSize: "0.875rem", fontWeight: 600 }}
          >
            Process Batch ({entries.length} {entries.length === 1 ? "Image" : "Images"})
          </Button>

          {batchResponse?.zip_base64 && (
            <Button
              variant="secondary"
              block
              icon={<FileArchive size={16} color="var(--success)" />}
              onClick={handleDownloadZip}
              style={{ padding: "0.625rem 1rem", fontSize: "0.875rem", fontWeight: 600 }}
            >
              Download Batch Archive (ZIP)
            </Button>
          )}
        </div>

        {/* Right Column: Batch Processing Queue List */}
        <div>
          {entries.length > 0 ? (
            <div>
              {batchResponse && (
                <div
                  className="card"
                  style={{
                    marginBottom: "1rem",
                    padding: "0.875rem 1.25rem",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    background: "var(--success-bg)",
                    borderColor: "var(--success-border)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <CheckCircle2 size={18} color="var(--success)" />
                    <div>
                      <div style={{ fontWeight: 600, fontSize: "0.875rem", color: "var(--success-text)" }}>
                        Batch Processing Completed
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                        {batchResponse.total_succeeded} succeeded, {batchResponse.total_failed} failed in{" "}
                        {(batchResponse.elapsed_seconds).toFixed(2)}s.
                      </div>
                    </div>
                  </div>
                  {batchResponse.zip_base64 && (
                    <Button
                      variant="primary"
                      icon={<FileArchive size={14} />}
                      onClick={handleDownloadZip}
                      style={{ padding: "0.35rem 0.75rem", fontSize: "0.75rem" }}
                    >
                      Download ZIP
                    </Button>
                  )}
                </div>
              )}

              <BatchQueue
                entries={entries}
                onRemove={handleRemove}
                onClearAll={handleClearAll}
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
                <Images size={24} />
              </div>
              <div style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.25rem" }}>
                Batch Processing Queue
              </div>
              <div style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", maxWidth: "380px", lineHeight: "1.5" }}>
                Add up to 10 photographs to restore them concurrently. Apply uniform restoration options across the entire collection and download results individually or as a single consolidated ZIP archive.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
