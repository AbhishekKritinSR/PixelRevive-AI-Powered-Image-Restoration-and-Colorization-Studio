import React, { useState } from "react";
import { Images, Download, Play, FileArchive } from "lucide-react";
import { BatchDropZone } from "../components/batch/BatchDropZone";
import { BatchQueue, BatchFileEntry } from "../components/batch/BatchQueue";
import { RestorationControls } from "../components/editor/RestorationControls";
import { Button } from "../components/common/Button";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { RestorationOptions, BatchRestorationResponse } from "../types/api";
import { restoreBatchImages, downloadDataUri } from "../services/api";

interface BatchRestorationViewProps {
  isModelReady: boolean;
}

export const BatchRestorationView: React.FC<BatchRestorationViewProps> = ({ isModelReady }) => {
  const [entries, setEntries] = useState<BatchFileEntry[]>([]);
  const [options, setOptions] = useState<RestorationOptions>({
    denoise: true,
    contrast: true,
    sharpen: true,
    colorize: true,
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [batchResponse, setBatchResponse] = useState<BatchRestorationResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div className="card">
            <div className="card-header">
              <div className="card-title">
                <Images size={18} color="var(--accent-primary)" />
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
          />

          <Button
            variant="primary"
            block
            icon={<Play size={18} />}
            isLoading={isProcessing}
            disabled={entries.length === 0 || isProcessing}
            onClick={handleProcessBatch}
          >
            Process Batch ({entries.length} {entries.length === 1 ? "Image" : "Images"})
          </Button>

          {batchResponse?.zip_base64 && (
            <Button
              variant="secondary"
              block
              icon={<FileArchive size={18} color="#34d399" />}
              onClick={handleDownloadZip}
            >
              Download Batch ZIP ({batchResponse.total_succeeded} files)
            </Button>
          )}
        </div>

        {/* Right Column: Queue & Results */}
        <div>
          {batchResponse && (
            <div
              className="card"
              style={{
                marginBottom: "1.25rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: "1rem",
              }}
            >
              <div>
                <div style={{ fontSize: "1.125rem", fontWeight: 700 }}>
                  Batch Processing Completed
                </div>
                <div style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginTop: "2px" }}>
                  {batchResponse.total_succeeded} succeeded • {batchResponse.total_failed} failed •{" "}
                  {(batchResponse.elapsed_seconds * 1000).toFixed(0)} ms total
                </div>
              </div>

              {batchResponse.zip_base64 && (
                <Button
                  variant="primary"
                  icon={<Download size={16} />}
                  onClick={handleDownloadZip}
                  style={{ padding: "0.45rem 1rem", fontSize: "0.875rem" }}
                >
                  Download All (ZIP)
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

          {entries.length === 0 && (
            <div
              className="card"
              style={{
                minHeight: "420px",
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
                <Images size={30} />
              </div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700, marginBottom: "0.5rem" }}>
                Multi-Image Batch Queue
              </div>
              <div style={{ color: "var(--text-muted)", fontSize: "0.875rem", maxWidth: "420px", lineHeight: "1.6" }}>
                Add up to 10 photographs to restore and colorize them in a single batch.
                The system features isolated per-item error handling: individual corrupted photos will not
                abort the remaining items.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
