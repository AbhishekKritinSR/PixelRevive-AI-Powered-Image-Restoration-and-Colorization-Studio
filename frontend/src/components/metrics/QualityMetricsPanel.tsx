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
}

export const QualityMetricsPanel: React.FC<QualityMetricsPanelProps> = ({
  metrics,
  originalWidth,
  originalHeight,
  processedWidth,
  processedHeight,
  wasResized,
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
    </div>
  );
};
