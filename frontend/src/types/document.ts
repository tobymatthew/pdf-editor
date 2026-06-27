export interface PageSize {
  width: number;
  height: number;
}

export type PageLiteracyMode = "native_text" | "scanned" | "hybrid";

export interface DocumentMetadata {
  id: string;
  original_filename: string;
  page_count: number;
  page_sizes: PageSize[];
  render_scale: number;
  created_at: number;
}

export interface PageAnalysis {
  page_number: number;
  mode: PageLiteracyMode;
  has_meaningful_text: boolean;
  text_word_count: number;
  text_character_count: number;
  image_count: number;
  image_area_ratio: number;
}

export interface PageCropBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface PageInfo {
  page_number: number;
  width: number;
  height: number;
  preview_path: string | null;
  render_path: string | null;
  has_ocr: boolean;
  analysis: PageAnalysis | null;
  crop_box: PageCropBox | null;
}
