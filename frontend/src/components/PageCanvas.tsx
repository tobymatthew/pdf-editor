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
  showOcr: boolean;
  scale: number;
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
  showOcr,
  scale,
}: PageCanvasProps) {
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const transformerRef = useRef<Konva.Transformer>(null);

  useEffect(() => {
    const img = new window.Image();
    img.src = imageUrl;
    img.onload = () => setImage(img);
    return () => {
      img.onload = null;
    };
  }, [imageUrl]);

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
        onSelectEdit(null);
      }
    },
    [onSelectEdit]
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
      style={{ background: "#e5e7eb", borderRadius: 4, overflow: "hidden" }}
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
              clipX={0}
              clipY={0}
              clipWidth={canvasBbox.w}
              clipHeight={canvasBbox.h}
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
                fill="#ffffff"
                stroke="#ef4444"
                strokeWidth={2}
              />
              {edit.text.value && (
                <Text
                  x={textX}
                  y={textY}
                  text={edit.text.value}
                  width={canvasBbox.w}
                  height={canvasBbox.h}
                  fontSize={(edit.text.font_size / pageHeight) * displayH}
                  fill={edit.text.color}
                  fontFamily={edit.text.font_family}
                  wrap="none"
                  ellipsis
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
          keepRatio={false}
          boundBoxFunc={(oldBox, newBox) => {
            if (newBox.width < 10 || newBox.height < 10) return oldBox;
            return newBox;
          }}
        />
      </Layer>
    </Stage>
  );
}
