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
        // Use referenceFile if uploaded, otherwise use originalFile
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
    <div className="card" style={{ marginTop: "1.5rem" }}>
      <div className="card-header">
        <div className="card-title">
          <Award size={18} color="var(--accent-primary)" />
          <span>Image Quality Assessment Dashboard</span>
          <span className="badge badge-success" style={{ fontSize: "0.6875rem" }}>
            Phase 5.6
          </span>
        </div>

        {restoredAssessment && (
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <span className="badge badge-pending">
              <Clock size={12} />
              <span>{(restoredAssessment.elapsed_seconds * 1000).toFixed(0)} ms latency</span>
            </span>
          </div>
        )}
      </div>

      <div style={{ padding: "0.25rem 0" }}>
        <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: "0.75rem", lineHeight: 1.5 }}>
          Scientific photographic evaluation via referenceless natural scene statistics (BRISQUE),
          structural similarity (SSIM), and chromatic variance (Hasler–Süsstrunk Colorfulness).
        </p>

        {/* Optional Reference Upload for SSIM */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "var(--bg-surface)",
            padding: "0.5rem 0.75rem",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
            marginBottom: "0.75rem",
            fontSize: "0.8125rem",
            flexWrap: "wrap",
            gap: "0.5rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <FileCheck size={16} color="var(--accent-secondary)" />
            <span>
              SSIM Reference:{" "}
              <strong>{referenceFile ? referenceFile.name : "Original Uploaded Image (Default)"}</strong>
            </span>
          </div>
          <label className="btn btn-outline" style={{ padding: "0.25rem 0.6rem", fontSize: "0.75rem" }}>
            <UploadCloud size={12} />
            <span>{referenceFile ? "Change Reference" : "Upload Pristine Ground-Truth"}</span>
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
              <div className="spinner" style={{ width: "16px", height: "16px", borderTopColor: "var(--accent-primary)" }} />
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
          <div className="alert alert-warning" style={{ marginTop: "0.75rem", fontSize: "0.8125rem" }}>
            <AlertCircle size={14} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Evaluation Results Cards */}
        {restoredAssessment && originalAssessment && (
          <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
            {/* Metric 1: BRISQUE */}
            <div className="quality-metric-block">
              <div className="quality-metric-header">
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <Eye size={16} color="#60a5fa" />
                  <strong>BRISQUE Perceptual Distortion (0–100)</strong>
                </div>
                <span className="badge badge-pending" style={{ fontSize: "0.6875rem" }}>
                  Lower is Better
                </span>
              </div>

              <div className="quality-metric-content">
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "0.5rem" }}>
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
                        gap: "0.35rem",
                        color:
                          brisqueRest.score <= brisqueOrig.score
                            ? "var(--success)"
                            : "var(--warning)",
                        fontWeight: 600,
                        marginBottom: "0.35rem",
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

                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", lineHeight: 1.4 }}>
                  {brisqueRest?.interpretation ||
                    "BRISQUE evaluates locally normalized luminance coefficients (AGGD). Natural undistorted images score lower."}
                </div>
              </div>
            </div>

            {/* Metric 2: SSIM */}
            <div className="quality-metric-block">
              <div className="quality-metric-header">
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <Layers size={16} color="#a855f7" />
                  <strong>Structural Similarity Index (SSIM)</strong>
                </div>
                <span className="badge badge-success" style={{ fontSize: "0.6875rem" }}>
                  Range: 0.0 – 1.0 (Higher is Better)
                </span>
              </div>

              <div className="quality-metric-content">
                <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginBottom: "0.5rem" }}>
                  <div style={{ fontSize: "1.5rem", fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-primary)" }}>
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
                      gap: "0.5rem",
                      marginBottom: "0.5rem",
                      fontSize: "0.75rem",
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

                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", lineHeight: 1.4 }}>
                  {ssimRest?.interpretation ||
                    "Wang et al. (2004) measures luminance, contrast, and structure preservation."}
                </div>
              </div>
            </div>

            {/* Metric 3: Colorfulness */}
            <div className="quality-metric-block">
              <div className="quality-metric-header">
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <Palette size={16} color="#ec4899" />
                  <strong>Hasler–Süsstrunk Colorfulness Metric</strong>
                </div>
                <span className="badge badge-pending" style={{ fontSize: "0.6875rem" }}>
                  Chromatic Dispersion
                </span>
              </div>

              <div className="quality-metric-content">
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "0.5rem" }}>
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
                    <div className="metric-sub-score" style={{ color: "#ec4899" }}>
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
                        color: "var(--success)",
                        fontWeight: 600,
                        marginBottom: "0.35rem",
                      }}
                    >
                      Colorfulness shift: +{(colorRest.score - colorOrig.score).toFixed(2)} (
                      {colorRest.score > 15 ? "Vibrant chromatic recovery" : "Subtle chromatic shift"})
                    </div>
                  )}

                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", lineHeight: 1.4 }}>
                  {colorRest?.interpretation ||
                    "Quantifies dispersion across opponent color planes (rg-yb). Pure grayscale images score exactly 0.0."}
                </div>
              </div>
            </div>

            {/* Quality Comparison Table */}
            <div style={{ marginTop: "0.5rem" }}>
              <div style={{ fontSize: "0.8125rem", fontWeight: 700, marginBottom: "0.5rem", color: "var(--text-primary)" }}>
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
                        <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Perceptual Distortion</div>
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)" }}>
                        {brisqueOrig?.score !== null && brisqueOrig?.score !== undefined
                          ? brisqueOrig.score.toFixed(2)
                          : "N/A"}
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", fontWeight: 700 }}>
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
                      <td style={{ fontSize: "0.75rem" }}>
                        Natural scene statistical distortion (lower is cleaner)
                      </td>
                    </tr>
                    <tr>
                      <td>
                        <strong>SSIM</strong>
                        <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Structural Fidelity</div>
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)" }}>1.0000 (Ref)</td>
                      <td style={{ fontFamily: "var(--font-mono)", fontWeight: 700 }}>
                        {ssimRest?.score !== null && ssimRest?.score !== undefined
                          ? ssimRest.score.toFixed(4)
                          : "N/A"}
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)" }}>
                        {ssimRest?.score !== null && ssimRest?.score !== undefined
                          ? `${(ssimRest.score * 100).toFixed(1)}% match`
                          : "—"}
                      </td>
                      <td style={{ fontSize: "0.75rem" }}>
                        Structural preservation of edges and contours
                      </td>
                    </tr>
                    <tr>
                      <td>
                        <strong>Colorfulness</strong>
                        <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Hasler–Süsstrunk</div>
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)" }}>
                        {colorOrig?.score !== null && colorOrig?.score !== undefined
                          ? colorOrig.score.toFixed(2)
                          : "N/A"}
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", fontWeight: 700 }}>
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
                      <td style={{ fontSize: "0.75rem" }}>
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
