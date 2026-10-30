import React, { useRef, useState } from "react";
import { UploadCloud, X, AlertTriangle } from "lucide-react";

interface DropZoneProps {
  selectedFile: File | null;
  onFileSelect: (file: File) => void;
  onClear: () => void;
  disabled?: boolean;
}

const ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];
const MAX_SIZE_BYTES = 25 * 1024 * 1024; // 25 MB

export const DropZone: React.FC<DropZoneProps> = ({
  selectedFile,
  onFileSelect,
  onClear,
  disabled = false,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imageDims, setImageDims] = useState<{ width: number; height: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateAndProcessFile = (file: File) => {
    setValidationError(null);
    const ext = "." + file.name.split(".").pop()?.toLowerCase();

    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setValidationError(
        `Unsupported format (${ext}). Supported formats: ${ALLOWED_EXTENSIONS.join(", ")}`
      );
      return;
    }

    if (file.size > MAX_SIZE_BYTES) {
      setValidationError(
        `File size (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds 25 MB limit.`
      );
      return;
    }

    // Read dimensions via HTML Image object
    const objectUrl = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      setImageDims({ width: img.naturalWidth, height: img.naturalHeight });
    };
    img.src = objectUrl;

    setPreviewUrl(objectUrl);
    onFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndProcessFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndProcessFile(e.target.files[0]);
    }
  };

  const handleClear = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(null);
    setImageDims(null);
    setValidationError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    onClear();
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (selectedFile && previewUrl) {
    return (
      <div className="card" style={{ padding: "1rem" }}>
        <div style={{ position: "relative", borderRadius: "var(--radius-md)", overflow: "hidden", background: "#000" }}>
          <img
            src={previewUrl}
            alt="Original Preview"
            style={{ width: "100%", maxHeight: "280px", objectFit: "contain", display: "block" }}
          />
          {!disabled && (
            <button
              onClick={handleClear}
              className="btn btn-danger"
              style={{
                position: "absolute",
                top: "0.5rem",
                right: "0.5rem",
                padding: "0.35rem 0.6rem",
                fontSize: "0.75rem",
              }}
              title="Remove image"
            >
              <X size={14} />
              <span>Change</span>
            </button>
          )}
        </div>

        <div style={{ marginTop: "0.75rem", display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
          <div style={{ fontWeight: 600, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "180px" }}>
            {selectedFile.name}
          </div>
          <div style={{ fontFamily: "var(--font-mono)" }}>
            {imageDims ? `${imageDims.width}×${imageDims.height} • ` : ""}
            {formatFileSize(selectedFile.size)}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInputChange}
        accept={ALLOWED_EXTENSIONS.join(",")}
        style={{ display: "none" }}
        disabled={disabled}
      />
      <div
        className={`dropzone ${isDragging ? "active" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
      >
        <div className="dropzone-icon">
          <UploadCloud size={28} />
        </div>
        <div className="dropzone-title">Upload a photograph to restore</div>
        <div className="dropzone-desc">Drag and drop here, or click to browse files</div>
        <div className="dropzone-limits">JPG, PNG, WEBP • Max 25 MB</div>
      </div>

      {validationError && (
        <div className="alert alert-warning" style={{ marginTop: "0.75rem", padding: "0.625rem 0.875rem" }}>
          <AlertTriangle size={16} style={{ flexShrink: 0 }} />
          <span style={{ fontSize: "0.8125rem" }}>{validationError}</span>
        </div>
      )}
    </div>
  );
};
