import React from "react";
import { AlertCircle, X } from "lucide-react";

interface ErrorBannerProps {
  message: string | null;
  onDismiss?: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({ message, onDismiss }) => {
  if (!message) return null;

  return (
    <div className="alert alert-danger" role="alert">
      <AlertCircle size={20} style={{ flexShrink: 0, marginTop: "2px" }} />
      <div style={{ flex: 1, fontSize: "0.875rem" }}>
        <strong>Error: </strong>
        {message}
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          style={{
            background: "transparent",
            border: "none",
            color: "inherit",
            cursor: "pointer",
            padding: "2px",
          }}
          aria-label="Dismiss error"
        >
          <X size={16} />
        </button>
      )}
    </div>
  );
};

