import React, { useState } from "react";
import {
  Search,
  AlertTriangle,
  Clock,
  Layers,
  ShieldCheck,
  Check,
} from "lucide-react";
import { ImageAnalysisResponse, RestorationOptions } from "../../types/api";
import { analyzeImage } from "../../services/api";

interface ImageAnalysisPanelProps {
  file: File | null;
  onApplyRecommendations: (recommendedOptions: Partial<RestorationOptions>) => void;
  disabled?: boolean;
}

export const ImageAnalysisPanel: React.FC<ImageAnalysisPanelProps> = ({
  file,
  onApplyRecommendations,
  disabled = false,
}) => {
  const [analysis, setAnalysis] = useState<ImageAnalysisResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [appliedFeedback, setAppliedFeedback] = useState(false);

  const handleRunAnalysis = async () => {
    if (!file) return;

    setIsAnalyzing(true);
    setErrorMessage(null);
    setAppliedFeedback(false);

    try {
      const result = await analyzeImage(file);
      setAnalysis(result);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Image analysis failed.");
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleApply = () => {
    if (!analysis) return;

    const rec = analysis.recommended_options;
    const newOptions: Partial<RestorationOptions> = {
      denoise: rec.denoise.recommended,
      contrast: rec.contrast.recommended,
      sharpen: rec.sharpen.recommended,
      colorize: rec.colorize.recommended,
    };

    onApplyRecommendations(newOptions);
    setAppliedFeedback(true);
    setTimeout(() => setAppliedFeedback(false), 2500);
  };

  if (!file) {
    return null;
  }

  return (
    <div className="card analysis-panel">
      <div className="card-header" style={{ paddingBottom: "0.5rem" }}>
        <div className="card-title">
          <Search size={16} color="var(--accent-primary)" />
          <span>Image Degradation Analysis</span>
        </div>
        {analysis && (
          <div style={{ display: "flex", gap: "0.35rem" }}>
            <span className="badge badge-success">
              <ShieldCheck size={11} />
              <span>Complete</span>
            </span>
            <span className="badge badge-outline">
              <Clock size={11} />
              <span>{(analysis.elapsed_seconds * 1000).toFixed(0)} ms</span>
            </span>
          </div>
        )}
      </div>

      {!analysis && !isAnalyzing && (
        <div>
          <p
            style={{
              fontSize: "0.75rem",
              color: "var(--text-secondary)",
              marginBottom: "0.625rem",
              lineHeight: 1.4,
            }}
          >
            Compute noise residuals, edge sharpness variance, and chromatic saturation to generate optimal restoration recommendations.
          </p>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleRunAnalysis}
            disabled={disabled || isAnalyzing}
            style={{ width: "100%", justifyContent: "center", fontSize: "0.8125rem", padding: "0.45rem" }}
          >
            <Search size={14} />
            <span>Analyze Photograph</span>
          </button>
        </div>
      )}

      {isAnalyzing && (
        <div
          style={{
            padding: "1.25rem",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "0.5rem",
          }}
        >
          <div
            className="spinner"
            style={{
              width: "20px",
              height: "20px",
              border: "2px solid var(--border-primary)",
              borderTopColor: "var(--accent-primary)",
              borderRadius: "50%",
            }}
          />
          <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
            Computing Laplacian variance & chromatic dispersion...
          </span>
        </div>
      )}

      {errorMessage && (
        <div className="alert alert-warning" style={{ marginTop: "0.5rem", fontSize: "0.75rem", padding: "0.5rem 0.75rem" }}>
          <AlertTriangle size={14} />
          <span>{errorMessage}</span>
        </div>
      )}

      {analysis && !isAnalyzing && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {/* Key Metrics Chips */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
              gap: "0.5rem",
            }}
          >
            {/* Noise */}
            <div className="analysis-stat-box">
              <div className="analysis-stat-label">Estimated Noise</div>
              <div className="analysis-stat-val">
                {analysis.analysis.noise.noise_score.toFixed(1)} σ
              </div>
              <span
                className={`badge ${
                  analysis.analysis.noise.noise_level === "low"
                    ? "badge-success"
                    : analysis.analysis.noise.noise_level === "medium"
                    ? "badge-pending"
                    : "badge-danger"
                }`}
                style={{ fontSize: "0.625rem", marginTop: "0.25rem", alignSelf: "flex-start" }}
              >
                {analysis.analysis.noise.noise_level.toUpperCase()} NOISE
              </span>
            </div>

            {/* Sharpness */}
            <div className="analysis-stat-box">
              <div className="analysis-stat-label">Sharpness</div>
              <div className="analysis-stat-val">
                {analysis.analysis.sharpness.sharpness_score.toFixed(0)}
              </div>
              <span
                className={`badge ${
                  analysis.analysis.sharpness.sharpness_level === "sharp"
                    ? "badge-success"
                    : analysis.analysis.sharpness.sharpness_level === "moderate"
                    ? "badge-pending"
                    : "badge-warning"
                }`}
                style={{ fontSize: "0.625rem", marginTop: "0.25rem", alignSelf: "flex-start" }}
              >
                {analysis.analysis.sharpness.sharpness_level.toUpperCase()}
              </span>
            </div>

            {/* Contrast */}
            <div className="analysis-stat-box">
              <div className="analysis-stat-label">Dynamic Contrast</div>
              <div className="analysis-stat-val">
                {analysis.analysis.contrast.contrast_score.toFixed(1)} σ
              </div>
              <span
                className={`badge ${
                  analysis.analysis.contrast.contrast_level === "high" ||
                  analysis.analysis.contrast.contrast_level === "moderate"
                    ? "badge-success"
                    : "badge-warning"
                }`}
                style={{ fontSize: "0.625rem", marginTop: "0.25rem", alignSelf: "flex-start" }}
              >
                {analysis.analysis.contrast.contrast_level.toUpperCase()}
              </span>
            </div>

            {/* Monochrome */}
            <div className="analysis-stat-box">
              <div className="analysis-stat-label">Color Mode</div>
              <div className="analysis-stat-val" style={{ fontSize: "0.875rem" }}>
                {analysis.analysis.monochrome.is_monochrome ? "Monochrome" : "Color"}
              </div>
              <span
                className="badge badge-outline"
                style={{ fontSize: "0.625rem", marginTop: "0.25rem", alignSelf: "flex-start" }}
              >
                {(analysis.analysis.monochrome.confidence * 100).toFixed(0)}% CONFIDENCE
              </span>
            </div>
          </div>

          {/* Detected Photographic Issues */}
          {analysis.detected_issues.length > 0 && (
            <div style={{ fontSize: "0.75rem" }}>
              <div style={{ color: "var(--text-secondary)", marginBottom: "0.25rem", fontWeight: 600, fontSize: "0.6875rem", textTransform: "uppercase" }}>
                Detected Characteristics:
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem" }}>
                {analysis.detected_issues.map((issue, idx) => (
                  <span
                    key={idx}
                    className="badge badge-outline"
                    style={{ fontSize: "0.6875rem" }}
                  >
                    {issue}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations Breakdown */}
          <div
            style={{
              background: "var(--bg-subtle)",
              borderRadius: "var(--radius-sm)",
              padding: "0.625rem 0.75rem",
              fontSize: "0.75rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.4rem",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <div
              style={{
                fontWeight: 600,
                color: "var(--text-primary)",
                fontSize: "0.75rem",
                marginBottom: "0.15rem",
              }}
            >
              Restoration Recommendations
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
              <div className="recommendation-row">
                <span className="recommendation-target">Denoising:</span>
                <span className={analysis.recommended_options.denoise.recommended ? "rec-badge-yes" : "rec-badge-no"}>
                  {analysis.recommended_options.denoise.recommended ? "Recommended" : "Optional"}
                </span>
                <span className="recommendation-reason">{analysis.recommended_options.denoise.reason}</span>
              </div>

              <div className="recommendation-row">
                <span className="recommendation-target">Contrast:</span>
                <span className={analysis.recommended_options.contrast.recommended ? "rec-badge-yes" : "rec-badge-no"}>
                  {analysis.recommended_options.contrast.recommended ? "Recommended" : "Optional"}
                </span>
                <span className="recommendation-reason">{analysis.recommended_options.contrast.reason}</span>
              </div>

              <div className="recommendation-row">
                <span className="recommendation-target">Sharpen:</span>
                <span className={analysis.recommended_options.sharpen.recommended ? "rec-badge-yes" : "rec-badge-no"}>
                  {analysis.recommended_options.sharpen.recommended ? "Recommended" : "Optional"}
                </span>
                <span className="recommendation-reason">{analysis.recommended_options.sharpen.reason}</span>
              </div>

              <div className="recommendation-row">
                <span className="recommendation-target">Colorize:</span>
                <span className={analysis.recommended_options.colorize.recommended ? "rec-badge-yes" : "rec-badge-no"}>
                  {analysis.recommended_options.colorize.recommended ? "Recommended" : "Optional"}
                </span>
                <span className="recommendation-reason">{analysis.recommended_options.colorize.reason}</span>
              </div>
            </div>
          </div>

          {/* 1-Click Apply Action */}
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleApply}
            disabled={disabled}
            style={{
              width: "100%",
              justifyContent: "center",
              fontSize: "0.75rem",
              padding: "0.45rem",
              borderColor: appliedFeedback ? "var(--success)" : undefined,
              color: appliedFeedback ? "var(--success)" : undefined,
            }}
          >
            {appliedFeedback ? (
              <>
                <Check size={13} />
                <span>Recommendations Applied to Settings</span>
              </>
            ) : (
              <>
                <Layers size={13} />
                <span>Apply Recommendations to Settings</span>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};
