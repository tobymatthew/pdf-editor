import { EditTargetBBox } from "../types/edit";
import { OCRBBox } from "../types/ocr";

interface Size {
  width: number;
  height: number;
}

export function pdfToCanvasBbox(
  bbox: OCRBBox | EditTargetBBox,
  page: Size,
  canvas: Size
): EditTargetBBox {
  return {
    x: (bbox.x / page.width) * canvas.width,
    y: (bbox.y / page.height) * canvas.height,
    w: (bbox.w / page.width) * canvas.width,
    h: (bbox.h / page.height) * canvas.height,
  };
}

export function canvasToPdfBbox(
  bbox: EditTargetBBox,
  page: Size,
  canvas: Size
): EditTargetBBox {
  return {
    x: (bbox.x / canvas.width) * page.width,
    y: (bbox.y / canvas.height) * page.height,
    w: (bbox.w / canvas.width) * page.width,
    h: (bbox.h / canvas.height) * page.height,
  };
}

export function pdfToCanvasX(value: number, pageWidth: number, canvasWidth: number): number {
  return (value / pageWidth) * canvasWidth;
}

export function pdfToCanvasY(value: number, pageHeight: number, canvasHeight: number): number {
  return (value / pageHeight) * canvasHeight;
}
