import { OCRBBox } from "./ocr";

export interface NativeTextStyle {
  font_name: string;
  font_size: number;
  color: string | null;
  bold: boolean;
  italic: boolean;
}

export interface NativeTextBlock {
  id: string;
  text: string;
  bbox: OCRBBox;
  style: NativeTextStyle;
}

export interface NativeTextPageResult {
  page_number: number;
  page_width: number;
  page_height: number;
  coordinate_space: string;
  blocks: NativeTextBlock[];
}
