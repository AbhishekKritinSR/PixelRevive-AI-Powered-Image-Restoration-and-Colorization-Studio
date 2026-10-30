import React, { useState, useRef, useCallback, useEffect } from "react";
import { MoveHorizontal } from "lucide-react";

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

  return (
    <div
      ref={containerRef}
      className="comparison-wrapper"
      onMouseDown={(e) => {
        setIsDragging(true);
        handleMove(e.clientX);
      }}
      onTouchStart={(e) => {
        setIsDragging(true);
        handleMove(e.touches[0].clientX);
      }}
    >
      <div className="comparison-image-container">
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
          <div className="comparison-handle" title="Drag to compare before & after">
            <MoveHorizontal size={18} />
          </div>
        </div>

        {/* Floating Badges */}
        <div className="comparison-badge left">{originalLabel}</div>
        <div className="comparison-badge right">{processedLabel}</div>
      </div>
    </div>
  );
};

