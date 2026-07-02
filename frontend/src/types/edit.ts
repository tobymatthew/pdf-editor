import { SignatureRef } from "./signature";

export interface EditTargetBBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface CoverConfig {
  enabled: boolean;
  method: "white" | "sampled_background" | "inpaint";
  padding: number;
}

export interface TextConfig {
  value: string;
  x: number;
  y: number;
  font_size: number;
  font_id?: string | null;
  font_family: string;
  color: string;
  bold: boolean;
  italic: boolean;
}

export interface Edit {
  id: string;
  page_number: number;
  type: string;
  target_bbox: EditTargetBBox;
  cover: CoverConfig;
  text: TextConfig;
  signature?: SignatureRef | null;
}

export interface EditCreate {
  page_number: number;
  type: string;
  target_bbox: EditTargetBBox;
  cover: CoverConfig;
  text: TextConfig;
  signature_id?: string | null;
}

export interface EditUpdate {
  target_bbox?: EditTargetBBox;
  cover?: CoverConfig;
  text?: TextConfig;
  signature?: SignatureRef | null;
}

export interface FontInfo {
  id: string;
  family: string;
  style: string;
  weight?: number | null;
  path: string;
}
