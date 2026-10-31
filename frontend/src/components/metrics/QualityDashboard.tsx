import React, { useState } from "react";
import {
  Activity,
  Award,
  Layers,
  Palette,
  Eye,
  Clock,
  UploadCloud,
  FileCheck,
  AlertCircle,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { ImageQualityAssessmentResponse } from "../../types/api";
import { assessQuality, dataUriToBlob } from "../../services/api";

interface QualityDashboardProps {
  originalFile: File | null;
  restoredDataUri: string | null;
  disabled?: boolean;
}

export const QualityDashboard: React.FC<QualityDashboardProps> = ({
  originalFile,
  restoredDataUri,
  disabled = false,
}) => {
  const [originalAssessment, setOriginalAssessment] = useState<ImageQualityAssessmentResponse | null>(null);
  const [restoredAssessment, setRestoredAssessment] = useState<ImageQualityAssessmentResponse | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);

  const handleRunEvaluation = async () => {
    if (!originalFile) return;

    setIsEvaluating(true);
    setErrorMessage(null);

    try {
      // 1. Evaluate original image
      const origRes = await assessQuality(originalFile, originalFile.name);
      setOriginalAssessment(origRes);

      // 2. Evaluate restored image if available, using original as reference for SSIM
      if (restoredDataUri) {
        const restoredBlob = dataUriToBlob(restoredDataUri);
        const refToUse = referenceFile || originalFile;
        const restRes = await assessQuality(
          restoredBlob,
          "restored.png",
          refToUse,
          refToUse.name
        );
        setRestoredAssessment(restRes);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Quality evaluation failed.");
      }
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleCustomReferenceUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setReferenceFile(e.target.files[0]);
    }
  };

  const brisqueOrig = originalAssessment?.metrics["brisque"];
  const brisqueRest = restoredAssessment?.metrics["brisque"];
  const ssimRest = restoredAssessment?.metrics["ssim"];
  const colorOrig = originalAssessment?.metrics["colorfulness"];
  const colorRest = restoredAssessment?.metrics["colorfulness"];

  return (
    <div className="card" style={{ marginTop: "1.25rem" }}>
      <div className="card-header">
        <div className="card-title">
          <Award size={16} color="var(--accent-primary)" />
          <span>Quality Assessment Dashboard</span>
        </div>

        {restoredAssessment && (
          <div style={{ display: "flex", gap: "0.35rem" }}>
            <span className="badge badge-outline">
              <Clock size={11} />
              <span>{(restoredAssessment.elapsed_seconds * 1000).toFixed(0)} ms latency</span>
            </span>
          </div>
        )}
      </div>

      <div>
        <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.75rem", lineHeight: 1.4 }}>
          Evaluate objective perceptual metrics including referenceless natural scene statistics (BRISQUE),
          structural similarity (SSIM), and chromatic variance (Hasler–Süsstrunk Colorfulness).
        </p>

        {/* Optional Reference Upload for SSIM */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "var(--bg-subtle)",
            padding: "0.5rem 0.75rem",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-subtle)",
            marginBottom: "0.75rem",
            fontSize: "0.75rem",
            flexWrap: "wrap",
            gap: "0.5rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <FileCheck size={14} color="var(--accent-primary)" />
            <span>
              SSIM Reference:{" "}
              <strong>{referenceFile ? referenceFile.name : "Original Uploaded Image (Default)"}</strong>
            </span>
          </div>
          <label className="btn btn-secondary" style={{ padding: "0.2rem 0.5rem", fontSize: "0.6875rem" }}>
            <UploadCloud size={12} />
            <span>{referenceFile ? "Change Ground-Truth" : "Upload Custom Ground-Truth"}</span>
            <input
              type="file"
              accept=".jpg,.jpeg,.png,.webp"
              onChange={handleCustomReferenceUpload}
              style={{ display: "none" }}
              disabled={disabled || isEvaluating}
            />
          </label>
        </div>

        {/* Action Button */}
        <button
          type="button"
          className="btn btn-secondary"
          onClick={handleRunEvaluation}
          disabled={disabled || isEvaluating || !originalFile}
          style={{ width: "100%", justifyContent: "center", fontSize: "0.8125rem", padding: "0.5rem" }}
        >
          {isEvaluating ? (
            <>
              <div
                className="spinner"
                style={{
                  width: "14px",
                  height: "14px",
                  border: "2px solid var(--border-primary)",
                  borderTopColor: "var(--accent-primary)",
                  borderRadius: "50%",
                }}
              />
              <span>Evaluating Natural Scene Statistics & SSIM...</span>
            </>
          ) : (
            <>
              <Activity size={14} />
              <span>Compute Perceptual Quality & Similarity Metrics</span>
            </>
          )}
        </button>

        {errorMessage && (
          <div className="alert alert-warning" style={{ marginTop: "0.75rem", fontSize: "0.75rem", padding: "0.5rem 0.75rem" }}>
            <AlertCircle size={14} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Evaluation Results Cards */}
        {restoredAssessment && originalAssessment && (
          <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {/* Metric 1: BRISQUE */}
            <div className="quality-metric-block">
              <div className="quality-metric-header">
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <Eye size={15} color="var(--accent-primary)" />
                  <strong>BRISQUE Perceptual Distortion (0–100)</strong>
                </div>
                <span className="badge badge-outline" style={{ fontSize: "0.625rem" }}>
                  Lower Score is Better
                </span>
              </div>

              <div className="quality-metric-content">
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", marginBottom: "0.5rem" }}>
                  <div className="metric-sub-card">
                    <div className="metric-sub-title">Original Score</div>
                    <div className="metric-sub-score">
                      {brisqueOrig?.score !== null && brisqueOrig?.score !== undefined
                        ? brisqueOrig.score.toFixed(2)
                        : "N/A"}
                    </div>
                  </div>
                  <div className="metric-sub-card">
                    <div className="metric-sub-title">Restored Score</div>
                    <div className="metric-sub-score" style={{ color: "var(--accent-primary)" }}>
                      {brisqueRest?.score !== null && brisqueRest?.score !== undefined
                        ? brisqueRest.score.toFixed(2)
                        : "N/A"}
                    </div>
                  </div>
                </div>

                {brisqueOrig?.score !== null &&
                  brisqueOrig?.score !== undefined &&
                  brisqueRest?.score !== null &&
                  brisqueRest?.score !== undefined && (
                    <div
                      style={{
                        fontSize: "0.75rem",
                        display: "flex",
                        alignItems: "center",
                        gap: "0.3rem",
                        color:
                          brisqueRest.score <= brisqueOrig.score
                            ? "var(--success)"
                            : "var(--warning)",
                        fontWeight: 600,
                        marginBottom: "0.25rem",
                      }}
                    >
                      {brisqueRest.score <= brisqueOrig.score ? (
                        <>
                          <TrendingDown size={14} />
                          <span>
                            {(brisqueOrig.score - brisqueRest.score).toFixed(2)} point distortion reduction
                          </span>
                        </>
                      ) : (
                        <>
                          <TrendingUp size={14} />
                          <span>
                            +{(brisqueRest.score - brisqueOrig.score).toFixed(2)} point shift
                          </span>
                        </>
                      )}
                    </div>
                  )}

                <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                  {brisqueRest?.interpretation ||
                    "BRISQUE evaluates locally normalized luminance coefficients (AGGD). Natural undistorted images score lower."}
                </div>
              </div>
            </div>

            {/* Metric 2: SSIM */}
            <div className="quality-metric-block">
              <div className="quality-metric-header">
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <Layers size={15} color="var(--accent-primary)" />
                  <strong>Structural Similarity Index (SSIM)</strong>
                </div>
                <span className="badge badge-success" style={{ fontSize: "0.625rem" }}>
                  Range: [-1.0, 1.0] (1.0 = Identical Structure)
                </span>
              </div>

              <div className="quality-metric-content">
                <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginBottom: "0.35rem" }}>
                  <div style={{ fontSize: "1.25rem", fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-primary)" }}>
                    {ssimRest?.score !== null && ssimRest?.score !== undefined
                      ? ssimRest.score.toFixed(4)
                      : "N/A"}
                  </div>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    structural fidelity against {referenceFile ? referenceFile.name : "original input"}
                  </span>
                </div>

                {/* Per-channel breakdown */}
                {ssimRest?.details && typeof ssimRest.details === "object" && "channel_scores" in ssimRest.details && (
                  <div
                    style={{
                      display: "flex",
                      gap: "0.35rem",
                      marginBottom: "0.35rem",
                      fontSize: "0.6875rem",
                    }}
                  >
                    {Object.entries(
                      ssimRest.details.channel_scores as Record<string, number>
                    ).map(([ch, val]) => (
                      <span key={ch} className="badge badge-outline" style={{ fontFamily: "var(--font-mono)" }}>
                        {ch.toUpperCase()}: {val.toFixed(4)}
                      </span>
                    ))}
                  </div>
                )}

                <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                  {ssimRest?.interpretation ||
                    "Wang et al. (2004) measures luminance, contrast, and structure preservation."}
                </div>
              </div>
            </div>

            {/* Metric 3: Colorfulness */}
            <div className="quality-metric-block">
              <div className="quality-metric-header">
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <Palette size={15} color="var(--accent-primary)" />
                  <strong>Hasler–Süsstrunk Colorfulness Metric</strong>
                </div>
                <span className="badge badge-outline" style={{ fontSize: "0.625rem" }}>
                  Chromatic Dispersion
                </span>
              </div>

              <div className="quality-metric-content">
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", marginBottom: "0.5rem" }}>
                  <div className="metric-sub-card">
                    <div className="metric-sub-title">Original Colorfulness</div>
                    <div className="metric-sub-score">
                      {colorOrig?.score !== null && colorOrig?.score !== undefined
                        ? colorOrig.score.toFixed(2)
                        : "N/A"}
                    </div>
                  </div>
                  <div className="metric-sub-card">
                    <div className="metric-sub-title">Restored Colorfulness</div>
                    <div className="metric-sub-score" style={{ color: "var(--text-primary)" }}>
                      {colorRest?.score !== null && colorRest?.score !== undefined
                        ? colorRest.score.toFixed(2)
                        : "N/A"}
                    </div>
                  </div>
                </div>

                {colorOrig?.score !== null &&
                  colorOrig?.score !== undefined &&
                  colorRest?.score !== null &&
                  colorRest?.score !== undefined && (
                    <div
                      style={{
                        fontSize: "0.75rem",
                        color: "var(--text-secondary)",
                        fontWeight: 600,
                        marginBottom: "0.25rem",
                      }}
                    >
                      Chromatic dispersion delta: {colorRest.score >= colorOrig.score ? "+" : ""}
                      {(colorRest.score - colorOrig.score).toFixed(2)} (quantifies opponent chromatic variance;
                      not historical color accuracy)
                    </div>
                  )}

                <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                  {colorRest?.interpretation ||
                    "Quantifies dispersion across opponent color planes (rg-yb). Pure grayscale images score exactly 0.0."}
                </div>
              </div>
            </div>

            {/* Quality Comparison Table */}
            <div style={{ marginTop: "0.5rem" }}>
              <div style={{ fontSize: "0.75rem", fontWeight: 600, marginBottom: "0.35rem", color: "var(--text-primary)", textTransform: "uppercase" }}>
                Objective Quality Comparison Summary
              </div>
              <div className="table-responsive">
                <table className="quality-table">
                  <thead>
                    <tr>
                      <th>Evaluated Metric</th>
                      <th>Original</th>
                      <th>Restored</th>
                      <th>Relative Change</th>
                      <th>Technical Meaning</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>
                        <strong>BRISQUE</strong>
                        <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)" }}>Perceptual Distortion</div>
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)" }}>
                        {brisqueOrig?.score !== null && brisqueOrig?.score !== undefined
                          ? brisqueOrig.score.toFixed(2)
                          : "N/A"}
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--text-primary)" }}>
                        {brisqueRest?.score !== null && brisqueRest?.score !== undefined
                          ? brisqueRest.score.toFixed(2)
                          : "N/A"}
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", color: "var(--success)" }}>
                        {brisqueOrig?.score !== null &&
                        brisqueOrig?.score !== undefined &&
                        brisqueRest?.score !== null &&
                        brisqueRest?.score !== undefined
                          ? (brisqueRest.score - brisqueOrig.score).toFixed(2)
                          : "—"}
                      </td>
                      <td style={{ fontSize: "0.6875rem" }}>
                        Natural scene statistical distortion (lower is cleaner)
                      </td>
                    </tr>
                    <tr>
                      <td>
                        <strong>SSIM</strong>
                        <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)" }}>Structural Fidelity</div>
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)" }}>1.0000 (Ref)</td>
                      <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--text-primary)" }}>
                        {ssimRest?.score !== null && ssimRest?.score !== undefined
                          ? ssimRest.score.toFixed(4)
                          : "N/A"}
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)" }}>
                        {ssimRest?.score !== null && ssimRest?.score !== undefined
                          ? `Fidelity: ${ssimRest.score.toFixed(4)}`
                          : "—"}
                      </td>
                      <td style={{ fontSize: "0.6875rem" }}>
                        Structural preservation of edges and contours
                      </td>
                    </tr>
                    <tr>
                      <td>
                        <strong>Colorfulness</strong>
                        <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)" }}>Hasler–Süsstrunk</div>
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)" }}>
                        {colorOrig?.score !== null && colorOrig?.score !== undefined
                          ? colorOrig.score.toFixed(2)
                          : "N/A"}
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--text-primary)" }}>
                        {colorRest?.score !== null && colorRest?.score !== undefined
                          ? colorRest.score.toFixed(2)
                          : "N/A"}
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", color: "var(--success)" }}>
                        {colorOrig?.score !== null &&
                        colorOrig?.score !== undefined &&
                        colorRest?.score !== null &&
                        colorRest?.score !== undefined
                          ? `+${(colorRest.score - colorOrig.score).toFixed(2)}`
                          : "—"}
                      </td>
                      <td style={{ fontSize: "0.6875rem" }}>
                        Opponent chromatic space dispersion
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
