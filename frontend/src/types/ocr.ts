export interface OCRBBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface OCRBlock {
  id: string;
  text: string;
  bbox: OCRBBox;
  confidence: number;
}

export interface OCRPageResult {
  page_number: number;
  image_width: number;
  image_height: number;
  page_width: number | null;
  page_height: number | null;
  coordinate_space: string;
  blocks: OCRBlock[];
}
