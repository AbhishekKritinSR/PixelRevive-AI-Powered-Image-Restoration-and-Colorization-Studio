import React, { useState } from "react";
import {
  Sparkles,
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
    <div className="card analysis-panel" style={{ marginTop: "1rem" }}>
      <div className="card-header" style={{ paddingBottom: "0.5rem" }}>
        <div className="card-title">
          <Search size={18} color="var(--accent-primary)" />
          <span>Intelligent Image Analysis</span>
        </div>
        {analysis && (
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <span className="badge badge-success">
              <ShieldCheck size={12} />
              <span>Diagnostic Pass</span>
            </span>
            <span className="badge badge-pending">
              <Clock size={12} />
              <span>{(analysis.elapsed_seconds * 1000).toFixed(0)} ms</span>
            </span>
          </div>
        )}
      </div>

      {!analysis && !isAnalyzing && (
        <div style={{ padding: "0.75rem 0" }}>
          <p
            style={{
              fontSize: "0.8125rem",
              color: "var(--text-secondary)",
              marginBottom: "0.75rem",
              lineHeight: 1.5,
            }}
          >
            Run heuristic noise, sharpness, and chromatic diagnostics to evaluate photograph
            degradations and generate explainable restoration settings.
          </p>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleRunAnalysis}
            disabled={disabled || isAnalyzing}
            style={{ width: "100%", justifyContent: "center", fontSize: "0.8125rem", padding: "0.5rem" }}
          >
            <Search size={14} />
            <span>Analyze Image Diagnostics</span>
          </button>
        </div>
      )}

      {isAnalyzing && (
        <div
          style={{
            padding: "1.5rem",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "0.75rem",
          }}
        >
          <div className="spinner" style={{ width: "24px", height: "24px", borderTopColor: "var(--accent-primary)" }} />
          <span style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
            Computing Laplacian variance, noise residuals & chromatic dispersion...
          </span>
        </div>
      )}

      {errorMessage && (
        <div className="alert alert-warning" style={{ marginTop: "0.5rem", fontSize: "0.8125rem" }}>
          <AlertTriangle size={14} />
          <span>{errorMessage}</span>
        </div>
      )}

      {analysis && !isAnalyzing && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.875rem", marginTop: "0.5rem" }}>
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
                style={{ fontSize: "0.6875rem", marginTop: "0.25rem" }}
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
                style={{ fontSize: "0.6875rem", marginTop: "0.25rem" }}
              >
                {analysis.analysis.sharpness.sharpness_level.toUpperCase()}
              </span>
            </div>

            {/* Contrast */}
            <div className="analysis-stat-box">
              <div className="analysis-stat-label">Contrast Dynamic</div>
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
                style={{ fontSize: "0.6875rem", marginTop: "0.25rem" }}
              >
                {analysis.analysis.contrast.contrast_level.toUpperCase()} CONTRAST
              </span>
            </div>

            {/* Monochrome */}
            <div className="analysis-stat-box">
              <div className="analysis-stat-label">Color Mode</div>
              <div className="analysis-stat-val" style={{ fontSize: "0.875rem" }}>
                {analysis.analysis.monochrome.is_monochrome ? "Monochrome" : "Color"}
              </div>
              <span
                className="badge badge-success"
                style={{ fontSize: "0.6875rem", marginTop: "0.25rem" }}
              >
                {(analysis.analysis.monochrome.confidence * 100).toFixed(0)}% CONFIDENCE
              </span>
            </div>
          </div>

          {/* Detected Photographic Issues */}
          {analysis.detected_issues.length > 0 && (
            <div style={{ fontSize: "0.75rem" }}>
              <div style={{ color: "var(--text-muted)", marginBottom: "0.35rem", fontWeight: 600 }}>
                DETECTED CHARACTERISTICS:
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
                {analysis.detected_issues.map((issue, idx) => (
                  <span
                    key={idx}
                    className="badge badge-pending"
                    style={{ fontSize: "0.6875rem", padding: "0.2rem 0.5rem" }}
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
              background: "var(--bg-surface)",
              borderRadius: "var(--radius-md)",
              padding: "0.75rem",
              fontSize: "0.8125rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.35rem",
                fontWeight: 600,
                color: "var(--text-primary)",
              }}
            >
              <Sparkles size={14} color="var(--accent-primary)" />
              <span>Restoration Recommendations</span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
              <div className="recommendation-row">
                <span className="recommendation-target">Denoising:</span>
                <span className={analysis.recommended_options.denoise.recommended ? "rec-badge-yes" : "rec-badge-no"}>
                  {analysis.recommended_options.denoise.recommended ? "Recommended" : "Not Recommended"}
                </span>
                <span className="recommendation-reason">{analysis.recommended_options.denoise.reason}</span>
              </div>

              <div className="recommendation-row">
                <span className="recommendation-target">Contrast:</span>
                <span className={analysis.recommended_options.contrast.recommended ? "rec-badge-yes" : "rec-badge-no"}>
                  {analysis.recommended_options.contrast.recommended ? "Recommended" : "Not Recommended"}
                </span>
                <span className="recommendation-reason">{analysis.recommended_options.contrast.reason}</span>
              </div>

              <div className="recommendation-row">
                <span className="recommendation-target">Sharpen:</span>
                <span className={analysis.recommended_options.sharpen.recommended ? "rec-badge-yes" : "rec-badge-no"}>
                  {analysis.recommended_options.sharpen.recommended ? "Recommended" : "Not Recommended"}
                </span>
                <span className="recommendation-reason">{analysis.recommended_options.sharpen.reason}</span>
              </div>

              <div className="recommendation-row">
                <span className="recommendation-target">Colorize:</span>
                <span className={analysis.recommended_options.colorize.recommended ? "rec-badge-yes" : "rec-badge-no"}>
                  {analysis.recommended_options.colorize.recommended ? "Recommended" : "Not Recommended"}
                </span>
                <span className="recommendation-reason">{analysis.recommended_options.colorize.reason}</span>
              </div>
            </div>
          </div>

          {/* 1-Click Apply Action */}
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleApply}
            disabled={disabled}
            style={{
              width: "100%",
              justifyContent: "center",
              fontSize: "0.8125rem",
              padding: "0.5rem",
              background: appliedFeedback ? "var(--success)" : undefined,
              borderColor: appliedFeedback ? "var(--success)" : undefined,
            }}
          >
            {appliedFeedback ? (
              <>
                <Check size={14} />
                <span>Recommendations Applied!</span>
              </>
            ) : (
              <>
                <Layers size={14} />
                <span>Apply Recommended Settings</span>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};
