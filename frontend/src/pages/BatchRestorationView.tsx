import React, { useState, useEffect } from "react";
import { Images, Play, FileArchive } from "lucide-react";
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
            availableModels={availableModels}
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
              Download Batch ZIP Archive
            </Button>
          )}
        </div>

        {/* Right Column: Batch Processing Queue List */}
        <div>
          <BatchQueue
            entries={entries}
            onRemove={handleRemove}
            onClearAll={handleClearAll}
            disabled={isProcessing}
          />
        </div>
      </div>
    </div>
  );
};
