import React, { useRef, useState } from "react";
import { UploadCloud, AlertTriangle } from "lucide-react";

interface BatchDropZoneProps {
  currentCount: number;
  maxFiles?: number;
  onFilesAdded: (newFiles: File[]) => void;
  disabled?: boolean;
}

const ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];
const MAX_SIZE_BYTES = 25 * 1024 * 1024; // 25 MB

export const BatchDropZone: React.FC<BatchDropZoneProps> = ({
  currentCount,
  maxFiles = 10,
  onFilesAdded,
  disabled = false,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (incomingList: FileList | File[]) => {
    setValidationError(null);
    const valid: File[] = [];
    const availableSlots = maxFiles - currentCount;

    if (availableSlots <= 0) {
      setValidationError(`Batch limit of ${maxFiles} images has already been reached.`);
      return;
    }

    const filesToExamine = Array.from(incomingList).slice(0, availableSlots);
    if (incomingList.length > availableSlots) {
      setValidationError(
        `Added first ${availableSlots} files. Maximum batch limit is ${maxFiles}.`
      );
    }

    for (const file of filesToExamine) {
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        setValidationError(`Skipped '${file.name}': Unsupported format.`);
        continue;
      }
      if (file.size > MAX_SIZE_BYTES) {
        setValidationError(`Skipped '${file.name}': Exceeds 25 MB limit.`);
        continue;
      }
      valid.push(file);
    }

    if (valid.length > 0) {
      onFilesAdded(valid);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled && currentCount < maxFiles) setIsDragging(true);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled || currentCount >= maxFiles) return;
    if (e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files);
    }
  };

  return (
    <div>
      <input
        type="file"
        ref={fileInputRef}
        multiple
        accept={ALLOWED_EXTENSIONS.join(",")}
        style={{ display: "none" }}
        disabled={disabled || currentCount >= maxFiles}
        onChange={(e) => e.target.files && handleFiles(e.target.files)}
      />

      <div
        className={`dropzone ${isDragging ? "active" : ""}`}
        style={{ minHeight: "180px", padding: "2rem 1.5rem" }}
        onDragOver={handleDragOver}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && currentCount < maxFiles && fileInputRef.current?.click()}
      >
        <div className="dropzone-icon" style={{ width: "44px", height: "44px", marginBottom: "0.75rem" }}>
          <UploadCloud size={24} />
        </div>
        <div className="dropzone-title">Add multiple photographs</div>
        <div className="dropzone-desc">
          Drag & drop up to {maxFiles} images ({maxFiles - currentCount} slots remaining)
        </div>
        <div className="dropzone-limits">JPG, PNG, WEBP • Max 25 MB per photo</div>
      </div>

      {validationError && (
        <div className="alert alert-warning" style={{ marginTop: "0.75rem", padding: "0.5rem 0.75rem" }}>
          <AlertTriangle size={16} style={{ flexShrink: 0 }} />
          <span style={{ fontSize: "0.8125rem" }}>{validationError}</span>
        </div>
      )}
    </div>
  );
};

