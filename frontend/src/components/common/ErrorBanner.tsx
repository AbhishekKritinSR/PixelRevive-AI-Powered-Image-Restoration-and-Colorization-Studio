import React from "react";
import { AlertCircle, X } from "lucide-react";

interface ErrorBannerProps {
  message: string | null;
  onDismiss?: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({ message, onDismiss }) => {
  if (!message) return null;

  return (
    <div className="alert alert-danger" role="alert" style={{ padding: "0.625rem 0.875rem", alignItems: "center" }}>
      <AlertCircle size={16} style={{ flexShrink: 0 }} />
      <div style={{ flex: 1, fontSize: "0.8125rem" }}>
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
            display: "flex",
            alignItems: "center",
          }}
          aria-label="Dismiss error"
        >
          <X size={15} />
        </button>
      )}
    </div>
  );
};
