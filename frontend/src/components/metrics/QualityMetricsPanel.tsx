import React from "react";
import { Activity, Clock, Cpu, Maximize2, Zap } from "lucide-react";
import { QualityMetricsResponse } from "../../types/api";

interface QualityMetricsPanelProps {
  metrics: QualityMetricsResponse;
  originalWidth: number;
  originalHeight: number;
  processedWidth: number;
  processedHeight: number;
  wasResized: boolean;
  operationsSummary?: Record<string, string>;
}

export const QualityMetricsPanel: React.FC<QualityMetricsPanelProps> = ({
  metrics,
  originalWidth,
  originalHeight,
  processedWidth,
  processedHeight,
  wasResized,
  operationsSummary,
}) => {
  const formatDelta = (delta: number) => {
    if (delta > 0) return `+${delta.toFixed(2)}`;
    return delta.toFixed(2);
  };

  return (
    <div className="card" style={{ marginTop: "1rem" }}>
      <div className="card-header">
        <div className="card-title">
          <Activity size={16} color="var(--accent-primary)" />
          <span>Pipeline Diagnostic Metrics</span>
        </div>
        <div style={{ display: "flex", gap: "0.35rem" }}>
          <span className="badge badge-success">
            <Cpu size={11} />
            <span>{metrics.device}</span>
          </span>
          <span className="badge badge-outline">
            <Clock size={11} />
            <span>{(metrics.elapsed_seconds * 1000).toFixed(0)} ms</span>
          </span>
        </div>
      </div>

      <div className="metrics-grid">
        {/* Sharpness */}
        <div className="metric-card">
          <div className="metric-label">Sharpness (Laplacian Var)</div>
          <div className="metric-value">{metrics.sharpness.toFixed(1)}</div>
          <div
            className={`metric-delta ${
              metrics.sharpness_delta >= 0 ? "delta-positive" : "delta-neutral"
            }`}
          >
            <Zap size={11} />
            <span>{formatDelta(metrics.sharpness_delta)} change</span>
          </div>
        </div>

        {/* Contrast */}
        <div className="metric-card">
          <div className="metric-label">Dynamic Contrast (Std Dev)</div>
          <div className="metric-value">{metrics.contrast.toFixed(1)}</div>
          <div
            className={`metric-delta ${
              metrics.contrast_delta >= 0 ? "delta-positive" : "delta-neutral"
            }`}
          >
            <span>{formatDelta(metrics.contrast_delta)} change</span>
          </div>
        </div>

        {/* Brightness */}
        <div className="metric-card">
          <div className="metric-label">Mean Luminance</div>
          <div className="metric-value">{metrics.brightness.toFixed(1)}</div>
          <div className="metric-delta delta-neutral">
            <span>Range: 0 - 255</span>
          </div>
        </div>

        {/* Dimensions & Resolution */}
        <div className="metric-card">
          <div className="metric-label">Output Resolution</div>
          <div className="metric-value">
            {processedWidth}×{processedHeight}
          </div>
          <div className="metric-delta delta-neutral">
            <Maximize2 size={11} />
            <span>
              {wasResized
                ? `Downscaled from ${originalWidth}×${originalHeight}`
                : "Original Scale"}
            </span>
          </div>
        </div>
      </div>

      {/* Adaptive Pipeline Execution & Protection Log */}
      {operationsSummary && Object.keys(operationsSummary).length > 0 && (
        <div
          style={{
            marginTop: "1rem",
            paddingTop: "0.85rem",
            borderTop: "1px solid var(--border-color)",
          }}
        >
          <div
            style={{
              fontSize: "0.8rem",
              fontWeight: 600,
              color: "var(--text-secondary)",
              marginBottom: "0.5rem",
            }}
          >
            Adaptive Pipeline Execution & Quality Safeguard Log:
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.45rem" }}>
            {Object.entries(operationsSummary).map(([stage, explanation]) => {
              const isBypassed =
                explanation.toLowerCase().startsWith("bypassed") ||
                explanation.toLowerCase().startsWith("skipped");
              return (
                <div
                  key={stage}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "0.5rem",
                    fontSize: "0.8rem",
                    lineHeight: 1.4,
                  }}
                >
                  <span
                    className={`badge ${isBypassed ? "badge-outline" : "badge-success"}`}
                    style={{
                      minWidth: "95px",
                      textTransform: "capitalize",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    {stage.replace("_", " ")}
                  </span>
                  <span
                    style={{
                      color: isBypassed
                        ? "var(--text-secondary)"
                        : "var(--text-primary)",
                    }}
                  >
                    {explanation}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
