import React, { useState, useRef, useCallback, useEffect } from "react";
import { MoveHorizontal, ZoomIn, ZoomOut, RotateCcw } from "lucide-react";

interface ImageSliderProps {
  originalUrl: string;
  processedUrl: string;
  originalLabel?: string;
  processedLabel?: string;
}

export const ImageSlider: React.FC<ImageSliderProps> = ({
  originalUrl,
  processedUrl,
  originalLabel = "Original",
  processedLabel = "Restored",
}) => {
  const [sliderPosition, setSliderPosition] = useState(50); // percentage 0 - 100
  const [isDragging, setIsDragging] = useState(false);
  const [zoomLevel, setZoomLevel] = useState<number>(1.0); // 1.0, 1.75, 2.5
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMove = useCallback((clientX: number) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
    setSliderPosition(percentage);
  }, []);

  const handleTouchMove = useCallback(
    (e: TouchEvent) => {
      if (!isDragging) return;
      handleMove(e.touches[0].clientX);
    },
    [isDragging, handleMove]
  );

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging) return;
      handleMove(e.clientX);
    },
    [isDragging, handleMove]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const step = e.shiftKey ? 1 : 5;
    if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
      e.preventDefault();
      setSliderPosition((prev) => Math.max(0, prev - step));
    } else if (e.key === "ArrowRight" || e.key === "ArrowUp") {
      e.preventDefault();
      setSliderPosition((prev) => Math.min(100, prev + step));
    } else if (e.key === "Home") {
      e.preventDefault();
      setSliderPosition(0);
    } else if (e.key === "End") {
      e.preventDefault();
      setSliderPosition(100);
    }
  };

  useEffect(() => {
    if (isDragging) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
      window.addEventListener("touchmove", handleTouchMove);
      window.addEventListener("touchend", handleMouseUp);
    }
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", handleMouseUp);
    };
  }, [isDragging, handleMouseMove, handleMouseUp, handleTouchMove]);

  const cycleZoom = () => {
    if (zoomLevel === 1.0) setZoomLevel(1.75);
    else if (zoomLevel === 1.75) setZoomLevel(2.5);
    else setZoomLevel(1.0);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      {/* Zoom Toolbar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "0.25rem 0.5rem",
          fontSize: "0.75rem",
          color: "var(--text-secondary)",
        }}
      >
        <span>
          Use mouse or arrow keys to drag slider. Current: <strong>{sliderPosition.toFixed(0)}%</strong>
        </span>

        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
          <button
            type="button"
            className="btn btn-outline"
            style={{ padding: "0.2rem 0.5rem", fontSize: "0.6875rem" }}
            onClick={cycleZoom}
            title="Inspect fine pixel details"
          >
            {zoomLevel === 1.0 ? <ZoomIn size={12} /> : <ZoomOut size={12} />}
            <span>Zoom: {zoomLevel}×</span>
          </button>
          {zoomLevel > 1.0 && (
            <button
              type="button"
              className="btn btn-outline"
              style={{ padding: "0.2rem 0.4rem", fontSize: "0.6875rem" }}
              onClick={() => setZoomLevel(1.0)}
              title="Reset Zoom"
            >
              <RotateCcw size={12} />
            </button>
          )}
        </div>
      </div>

      <div
        ref={containerRef}
        tabIndex={0}
        role="slider"
        aria-label="Image comparison slider"
        aria-valuenow={Math.round(sliderPosition)}
        aria-valuemin={0}
        aria-valuemax={100}
        onKeyDown={handleKeyDown}
        className="comparison-wrapper"
        style={{
          outline: "none",
          cursor: isDragging ? "ew-resize" : "default",
          overflow: "hidden",
        }}
        onMouseDown={(e) => {
          setIsDragging(true);
          handleMove(e.clientX);
        }}
        onTouchStart={(e) => {
          setIsDragging(true);
          handleMove(e.touches[0].clientX);
        }}
      >
        <div
          className="comparison-image-container"
          style={{
            transform: `scale(${zoomLevel})`,
            transformOrigin: "center center",
            transition: isDragging ? "none" : "transform 150ms ease",
          }}
        >
          {/* Background Image: Processed Result */}
          <img
            src={processedUrl}
            alt="Restored Result"
            className="comparison-image"
            draggable={false}
          />

          {/* Foreground Overlay: Original Image clipped by sliderPosition */}
          <div
            className="comparison-overlay"
            style={{ width: `${sliderPosition}%` }}
          >
            <img
              src={originalUrl}
              alt="Original Photograph"
              draggable={false}
              style={{
                width: containerRef.current ? `${containerRef.current.clientWidth}px` : "100%",
              }}
            />
          </div>

          {/* Slider Divider Line */}
          <div
            className="comparison-divider"
            style={{ left: `${sliderPosition}%` }}
          >
            <div className="comparison-handle" title="Drag or use arrow keys to compare">
              <MoveHorizontal size={18} />
            </div>
          </div>

          {/* Floating Badges */}
          <div className="comparison-badge left">{originalLabel}</div>
          <div className="comparison-badge right">{processedLabel}</div>
        </div>
      </div>
    </div>
  );
};
