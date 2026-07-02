import React, { useRef, useEffect, useState, useCallback } from "react";
import { Stage, Layer, Image as KonvaImage, Rect, Text, Transformer, Group } from "react-konva";
import type Konva from "konva";
import { NativeTextBlock } from "../types/nativeText";
import { OCRBlock } from "../types/ocr";
import { Edit, EditTargetBBox } from "../types/edit";
import { PageCropBox } from "../types/document";
import {
  canvasToPdfBbox,
  pdfToCanvasBbox,
  pdfToCanvasX,
  pdfToCanvasY,
} from "../utils/coordinates";

interface PageCanvasProps {
  imageUrl: string;
  pageWidth: number;
  pageHeight: number;
  ocrBlocks: OCRBlock[];
  nativeTextBlocks: NativeTextBlock[];
  edits: Edit[];
  selectedEditId: string | null;
  cropBox: PageCropBox | null;
  cropMode: boolean;
  onSelectEdit: (id: string | null) => void;
  onUpdateEditBbox: (id: string, bbox: EditTargetBBox) => void;
  onUpdateCropBox: (bbox: PageCropBox) => void;
  onSelectOcrBlock: (block: OCRBlock) => void;
  onSelectNativeTextBlock: (block: NativeTextBlock) => void;
  onCreateTextField: (bbox: EditTargetBBox) => void;
  showOcr: boolean;
  scale: number;
  getSignatureImageUrl: (editId: string) => string;
  insertTextMode: boolean;
}

function useHtmlImage(url: string): HTMLImageElement | null {
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  useEffect(() => {
    if (!url) {
      setImage(null);
      return;
    }
    const img = new window.Image();
    img.crossOrigin = "anonymous";
    const handleLoad = () => setImage(img);
    img.onload = handleLoad;
    img.src = url;
    if (img.complete) handleLoad();
    return () => {
      img.onload = null;
    };
  }, [url]);
  return image;
}

export default function PageCanvas({
  imageUrl,
  pageWidth,
  pageHeight,
  ocrBlocks,
  nativeTextBlocks,
  edits,
  selectedEditId,
  cropBox,
  cropMode,
  onSelectEdit,
  onUpdateEditBbox,
  onUpdateCropBox,
  onSelectOcrBlock,
  onSelectNativeTextBlock,
  onCreateTextField,
  showOcr,
  scale,
  getSignatureImageUrl,
  insertTextMode,
}: PageCanvasProps) {
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const transformerRef = useRef<Konva.Transformer>(null);

  useEffect(() => {
    if (!imageUrl) {
      setImage(null);
      return;
    }
    const img = new window.Image();
    img.crossOrigin = "anonymous";
    const handleLoad = () => setImage(img);
    img.onload = handleLoad;
    img.src = imageUrl;
    if (img.complete) handleLoad();
    return () => {
      img.onload = null;
    };
  }, [imageUrl]);

  const selectedEdit = edits.find((e) => e.id === selectedEditId) || null;
  const selectedIsSignature = selectedEdit?.type === "signature";

  useEffect(() => {
    if (transformerRef.current && cropMode) {
      const node = stageRef.current?.findOne("#page-crop-box");
      if (node) {
        transformerRef.current.nodes([node]);
        transformerRef.current.getLayer()?.batchDraw();
      }
    } else if (transformerRef.current && selectedEditId) {
      const node = stageRef.current?.findOne(`#edit-${selectedEditId}`);
      if (node) {
        transformerRef.current.nodes([node]);
        transformerRef.current.getLayer()?.batchDraw();
      }
    } else {
      transformerRef.current?.nodes([]);
      transformerRef.current?.getLayer()?.batchDraw();
    }
  }, [selectedEditId, edits, cropMode, cropBox]);

  const displayW = pageWidth * scale;
  const displayH = pageHeight * scale;

  const handleStageClick = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>) => {
      if (e.target === e.target.getStage()) {
        if (insertTextMode) {
          const stage = stageRef.current;
          const pointer = stage?.getPointerPosition();
          if (!stage || !pointer) return;
          const defaultWidth = Math.min(180, pageWidth * 0.45);
          const defaultHeight = Math.max(28, pageHeight * 0.035);
          const displayDefault = {
            x: pointer.x,
            y: pointer.y,
            w: defaultWidth * scale,
            h: defaultHeight * scale,
          };
          const bbox = canvasToPdfBbox(
            displayDefault,
            { width: pageWidth, height: pageHeight },
            { width: displayW, height: displayH }
          );
          const clamped: EditTargetBBox = {
            x: Math.max(0, Math.min(pageWidth - bbox.w, bbox.x)),
            y: Math.max(0, Math.min(pageHeight - bbox.h, bbox.y)),
            w: Math.min(bbox.w, pageWidth),
            h: Math.min(bbox.h, pageHeight),
          };
          onCreateTextField(clamped);
          return;
        }
        onSelectEdit(null);
      }
    },
    [displayH, displayW, insertTextMode, onCreateTextField, onSelectEdit, pageHeight, pageWidth, scale]
  );

  const handleDragEnd = useCallback(
    (editId: string, e: Konva.KonvaEventObject<DragEvent>) => {
      const node = e.target;
      onUpdateEditBbox(editId, {
        ...canvasToPdfBbox(
          {
            x: node.x(),
            y: node.y(),
            w: node.width() * node.scaleX(),
            h: node.height() * node.scaleY(),
          },
          { width: pageWidth, height: pageHeight },
          { width: displayW, height: displayH }
        ),
      });
    },
    [displayH, displayW, onUpdateEditBbox, pageHeight, pageWidth]
  );

  const handleTransformEnd = useCallback(
    (editId: string, e: Konva.KonvaEventObject<Event>) => {
      const node = e.target;
      const scaleX = node.scaleX();
      const scaleY = node.scaleY();
      node.scaleX(1);
      node.scaleY(1);
      onUpdateEditBbox(editId, {
        ...canvasToPdfBbox(
          {
            x: node.x(),
            y: node.y(),
            w: node.width() * scaleX,
            h: node.height() * scaleY,
          },
          { width: pageWidth, height: pageHeight },
          { width: displayW, height: displayH }
        ),
      });
    },
    [displayH, displayW, onUpdateEditBbox, pageHeight, pageWidth]
  );

  const handleCropChange = useCallback(
    (e: Konva.KonvaEventObject<DragEvent | Event>) => {
      const node = e.target;
      const scaleX = node.scaleX();
      const scaleY = node.scaleY();
      node.scaleX(1);
      node.scaleY(1);
      const bbox = canvasToPdfBbox(
        {
          x: node.x(),
          y: node.y(),
          w: node.width() * scaleX,
          h: node.height() * scaleY,
        },
        { width: pageWidth, height: pageHeight },
        { width: displayW, height: displayH }
      );
      onUpdateCropBox(bbox);
    },
    [displayH, displayW, onUpdateCropBox, pageHeight, pageWidth]
  );

  return (
    <Stage
      ref={stageRef}
      width={displayW}
      height={displayH}
      onClick={handleStageClick}
      onTap={handleStageClick}
      style={{
        background: "#e5e7eb",
        borderRadius: 4,
        overflow: "hidden",
        cursor: insertTextMode ? "crosshair" : "default",
      }}
    >
      <Layer>
        {image && (
          <KonvaImage
            image={image}
            width={displayW}
            height={displayH}
            listening={false}
          />
        )}

        {showOcr &&
          nativeTextBlocks.map((block) => {
            const canvasBbox = pdfToCanvasBbox(
              block.bbox,
              { width: pageWidth, height: pageHeight },
              { width: displayW, height: displayH }
            );
            return (
              <Rect
                key={block.id}
                x={canvasBbox.x}
                y={canvasBbox.y}
                width={canvasBbox.w}
                height={canvasBbox.h}
                stroke="#10b981"
                strokeWidth={1}
                dash={[6, 3]}
                fill="rgba(16, 185, 129, 0.12)"
                onClick={() => onSelectNativeTextBlock(block)}
                onTap={() => onSelectNativeTextBlock(block)}
              />
            );
          })}

        {showOcr &&
          ocrBlocks.map((block) => {
            const canvasBbox = pdfToCanvasBbox(
              block.bbox,
              { width: pageWidth, height: pageHeight },
              { width: displayW, height: displayH }
            );
            return (
              <Rect
                key={block.id}
                x={canvasBbox.x}
                y={canvasBbox.y}
                width={canvasBbox.w}
                height={canvasBbox.h}
                stroke="#3b82f6"
                strokeWidth={1}
                dash={[4, 2]}
                fill="rgba(59, 130, 246, 0.1)"
                onClick={() => onSelectOcrBlock(block)}
                onTap={() => onSelectOcrBlock(block)}
              />
            );
          })}

        {edits.map((edit) => {
          const canvasBbox = pdfToCanvasBbox(
            edit.target_bbox,
            { width: pageWidth, height: pageHeight },
            { width: displayW, height: displayH }
          );
          if (edit.type === "signature") {
            return (
              <SignatureEditNode
                key={edit.id}
                editId={edit.id}
                imageUrl={getSignatureImageUrl(edit.id)}
                x={canvasBbox.x}
                y={canvasBbox.y}
                width={canvasBbox.w}
                height={canvasBbox.h}
                selected={edit.id === selectedEditId}
                onSelect={() => onSelectEdit(edit.id)}
                onDragEnd={(e) => handleDragEnd(edit.id, e)}
                onTransformEnd={(e) => handleTransformEnd(edit.id, e)}
              />
            );
          }
          const textX = pdfToCanvasX(edit.text.x, pageWidth, displayW) - canvasBbox.x;
          const textY = pdfToCanvasY(edit.text.y, pageHeight, displayH) - canvasBbox.y;
          return (
            <Group
              key={edit.id}
              id={`edit-${edit.id}`}
              x={canvasBbox.x}
              y={canvasBbox.y}
              width={canvasBbox.w}
              height={canvasBbox.h}
              draggable
              onClick={() => onSelectEdit(edit.id)}
              onTap={() => onSelectEdit(edit.id)}
              onDragEnd={(e) => handleDragEnd(edit.id, e)}
              onTransformEnd={(e) => handleTransformEnd(edit.id, e)}
            >
              <Rect
                x={0}
                y={0}
                width={canvasBbox.w}
                height={canvasBbox.h}
                fill={edit.cover.enabled ? "#ffffff" : "rgba(59, 130, 246, 0.08)"}
                stroke={edit.id === selectedEditId ? "#ef4444" : "#3b82f6"}
                strokeWidth={edit.id === selectedEditId ? 2 : 1}
                dash={edit.cover.enabled ? undefined : [6, 4]}
              />
              {edit.text.value && (
                <Text
                  x={textX}
                  y={textY}
                  text={edit.text.value}
                  width={Math.max(canvasBbox.w, displayW - canvasBbox.x)}
                  height={Math.max(
                    canvasBbox.h,
                    (edit.text.font_size / pageHeight) * displayH * 1.4
                  )}
                  fontSize={(edit.text.font_size / pageHeight) * displayH}
                  fill={edit.text.color}
                  fontFamily={edit.text.font_family}
                  wrap="none"
                />
              )}
            </Group>
          );
        })}

        {cropMode &&
          (() => {
            const activeCrop =
              cropBox || { x: pageWidth * 0.05, y: pageHeight * 0.05, w: pageWidth * 0.9, h: pageHeight * 0.9 };
            const canvasCrop = pdfToCanvasBbox(
              activeCrop,
              { width: pageWidth, height: pageHeight },
              { width: displayW, height: displayH }
            );
            return (
              <Rect
                id="page-crop-box"
                x={canvasCrop.x}
                y={canvasCrop.y}
                width={canvasCrop.w}
                height={canvasCrop.h}
                fill="rgba(245, 158, 11, 0.08)"
                stroke="#f59e0b"
                strokeWidth={2}
                dash={[8, 4]}
                draggable
                onDragEnd={handleCropChange}
                onTransformEnd={handleCropChange}
              />
            );
          })()}

        <Transformer
          ref={transformerRef}
          rotateEnabled={false}
          keepRatio={selectedIsSignature}
          boundBoxFunc={(oldBox, newBox) => {
            if (newBox.width < 10 || newBox.height < 10) return oldBox;
            return newBox;
          }}
        />
      </Layer>
    </Stage>
  );
}

interface SignatureEditNodeProps {
  editId: string;
  imageUrl: string;
  x: number;
  y: number;
  width: number;
  height: number;
  selected: boolean;
  onSelect: () => void;
  onDragEnd: (e: Konva.KonvaEventObject<DragEvent>) => void;
  onTransformEnd: (e: Konva.KonvaEventObject<Event>) => void;
}

function SignatureEditNode({
  editId,
  imageUrl,
  x,
  y,
  width,
  height,
  selected,
  onSelect,
  onDragEnd,
  onTransformEnd,
}: SignatureEditNodeProps) {
  const img = useHtmlImage(imageUrl);
  return (
    <Group
      id={`edit-${editId}`}
      x={x}
      y={y}
      width={width}
      height={height}
      draggable
      onMouseDown={onSelect}
      onTouchStart={onSelect}
      onClick={onSelect}
      onTap={onSelect}
      onDragStart={onSelect}
      onDragEnd={onDragEnd}
      onTransformEnd={onTransformEnd}
    >
      <Rect
        x={0}
        y={0}
        width={Math.max(width, 18)}
        height={Math.max(height, 18)}
        fill="rgba(0,0,0,0.001)"
        stroke={selected ? "#3b82f6" : "transparent"}
        strokeWidth={selected ? 1 : 0}
        dash={selected ? [6, 3] : undefined}
      />
      {selected && (
        <Rect
          x={-2}
          y={-2}
          width={width + 4}
          height={height + 4}
          fill="rgba(59,130,246,0.08)"
          stroke="#3b82f6"
          strokeWidth={1}
          dash={[6, 3]}
          listening={false}
        />
      )}
      {img && (
        <KonvaImage
          image={img}
          x={0}
          y={0}
          width={width}
          height={height}
          listening={false}
        />
      )}
    </Group>
  );
}
