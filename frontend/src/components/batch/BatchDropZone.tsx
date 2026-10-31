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
      setValidationError(`Maximum batch limit of ${maxFiles} images has already been reached.`);
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
        setValidationError(`Skipped '${file.name}': Unsupported format (${ext}).`);
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
        style={{ minHeight: "160px", padding: "1.5rem 1rem" }}
        onDragOver={handleDragOver}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && currentCount < maxFiles && fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Upload Multiple Images"
      >
        <div className="dropzone-icon" style={{ width: "40px", height: "40px", marginBottom: "0.5rem" }}>
          <UploadCloud size={20} />
        </div>
        <div className="dropzone-title">Upload Multiple Photographs</div>
        <div className="dropzone-desc">
          Drag & drop up to {maxFiles} images ({maxFiles - currentCount} slots available)
        </div>
        <div className="dropzone-limits">JPG, JPEG, PNG, WEBP • Up to 25 MB each</div>
      </div>

      {validationError && (
        <div className="alert alert-warning" style={{ marginTop: "0.5rem", padding: "0.5rem 0.75rem", fontSize: "0.75rem" }}>
          <AlertTriangle size={15} style={{ flexShrink: 0 }} />
          <span>{validationError}</span>
        </div>
      )}
    </div>
  );
};
