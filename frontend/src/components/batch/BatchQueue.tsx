import React from "react";
import { Trash2, CheckCircle2, XCircle, Clock, Download } from "lucide-react";
import { BatchItemResult } from "../../types/api";
import { downloadDataUri } from "../../services/api";

export interface BatchFileEntry {
  id: string;
  file: File;
  previewUrl: string;
  result?: BatchItemResult;
}

interface BatchQueueProps {
  entries: BatchFileEntry[];
  onRemove: (id: string) => void;
  onClearAll: () => void;
  disabled?: boolean;
}

export const BatchQueue: React.FC<BatchQueueProps> = ({
  entries,
  onRemove,
  onClearAll,
  disabled = false,
}) => {
  if (entries.length === 0) return null;

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="card" style={{ marginTop: "1.5rem" }}>
      <div className="card-header">
        <div className="card-title">
          <span>Batch Queue ({entries.length}/10)</span>
        </div>
        {!disabled && (
          <button
            onClick={onClearAll}
            className="btn btn-outline"
            style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
          >
            Clear All
          </button>
        )}
      </div>

      <div className="batch-queue">
        {entries.map((entry) => {
          const res = entry.result;
          return (
            <div key={entry.id} className="batch-item">
              <div className="batch-item-left">
                <img
                  src={res?.image_base64 || entry.previewUrl}
                  alt={entry.file.name}
                  className="batch-item-thumb"
                />
                <div className="batch-item-meta">
                  <div className="batch-item-name" title={entry.file.name}>
                    {entry.file.name}
                  </div>
                  <div className="batch-item-size">
                    {formatFileSize(entry.file.size)}
                    {res?.elapsed_seconds
                      ? ` • ${(res.elapsed_seconds * 1000).toFixed(0)} ms`
                      : ""}
                  </div>
                  {res?.error && (
                    <div style={{ color: "#f87171", fontSize: "0.75rem", marginTop: "2px" }}>
                      {res.error}
                    </div>
                  )}
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                {!res ? (
                  <span className="badge badge-pending">
                    <Clock size={12} />
                    <span>Ready</span>
                  </span>
                ) : res.status === "success" ? (
                  <>
                    <span className="badge badge-success">
                      <CheckCircle2 size={12} />
                      <span>Restored</span>
                    </span>
                    {res.image_base64 && (
                      <button
                        onClick={() =>
                          downloadDataUri(
                            res.image_base64!,
                            `restored_${entry.file.name.replace(/\.[^/.]+$/, "")}.png`
                          )
                        }
                        className="btn btn-secondary"
                        style={{ padding: "0.35rem 0.6rem", fontSize: "0.75rem" }}
                        title="Download restored image"
                      >
                        <Download size={14} />
                      </button>
                    )}
                  </>
                ) : (
                  <span className="badge badge-danger">
                    <XCircle size={12} />
                    <span>Failed</span>
                  </span>
                )}

                {!disabled && (
                  <button
                    onClick={() => onRemove(entry.id)}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "var(--text-muted)",
                      cursor: "pointer",
                      padding: "4px",
                    }}
                    title="Remove item"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
