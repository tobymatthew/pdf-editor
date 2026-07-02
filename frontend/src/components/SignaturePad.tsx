import React, { useRef, useState, useCallback, forwardRef, useImperativeHandle } from "react";
import { Stage, Layer, Line } from "react-konva";
import type Konva from "konva";

interface Point {
  x: number;
  y: number;
}

export interface SignaturePadHandle {
  clear: () => void;
  exportPng: () => { blob: Blob; dataUrl: string } | null;
  hasInk: () => boolean;
}

interface SignaturePadProps {
  width?: number;
  height?: number;
  stroke?: string;
  strokeWidth?: number;
  onChange?: (hasInk: boolean) => void;
}

const SignaturePad = forwardRef<SignaturePadHandle, SignaturePadProps>(function SignaturePad(
  {
    width = 480,
    height = 200,
    stroke = "#111111",
    strokeWidth = 3,
    onChange,
  },
  ref
) {
  const [lines, setLines] = useState<Point[][]>([]);
  const isDrawing = useRef(false);
  const stageRef = useRef<Konva.Stage | null>(null);

  const getPointer = (): Point | null => {
    const stage = stageRef.current;
    if (!stage) return null;
    const pos = stage.getPointerPosition();
    if (!pos) return null;
    return { x: pos.x, y: pos.y };
  };

  const handleMouseDown = useCallback(() => {
    const point = getPointer();
    if (!point) return;
    isDrawing.current = true;
    setLines((prev) => [...prev, [point]]);
  }, []);

  const handleMouseMove = useCallback(() => {
    if (!isDrawing.current) return;
    const point = getPointer();
    if (!point) return;
    setLines((prev) => {
      const next = prev.slice();
      const current = next[next.length - 1];
      if (!current) return next;
      next[next.length - 1] = [...current, point];
      return next;
    });
  }, []);

  const handleMouseUp = useCallback(() => {
    isDrawing.current = false;
  }, []);

  const clear = useCallback(() => {
    setLines([]);
    onChange?.(false);
  }, [onChange]);

  const exportPng = useCallback((): { blob: Blob; dataUrl: string } | null => {
    const stage = stageRef.current;
    if (!stage || lines.length === 0) return null;
    const dataUrl = stage.toDataURL({ pixelRatio: 2, mimeType: "image/png" });
    return { blob: dataUrlToBlob(dataUrl), dataUrl };
  }, [lines]);

  useImperativeHandle(ref, () => ({
    clear,
    exportPng,
    hasInk: () => lines.length > 0,
  }));

  return (
    <div
      style={{
        width,
        height,
        border: "1px solid #d1d5db",
        borderRadius: 6,
        background:
          "repeating-linear-gradient(45deg, #fafafa, #fafafa 10px, #f3f4f6 10px, #f3f4f6 20px)",
        touchAction: "none",
        cursor: "crosshair",
      }}
    >
      <Stage
        ref={stageRef}
        width={width}
        height={height}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleMouseDown}
        onTouchMove={handleMouseMove}
        onTouchEnd={handleMouseUp}
      >
        <Layer>
          {lines.map((line, i) => (
            <Line
              key={i}
              points={line.flatMap((p) => [p.x, p.y])}
              stroke={stroke}
              strokeWidth={strokeWidth}
              lineJoin="round"
              lineCap="round"
            />
          ))}
        </Layer>
      </Stage>
    </div>
  );
});

export default SignaturePad;

function dataUrlToBlob(dataUrl: string): Blob {
  const [meta, b64] = dataUrl.split(",");
  const mime = /data:(.*?);base64/.exec(meta)?.[1] || "image/png";
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new Blob([bytes], { type: mime });
}
