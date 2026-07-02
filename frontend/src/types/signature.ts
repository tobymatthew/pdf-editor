export interface SignatureInfo {
  id: string;
  name: string;
  width: number;
  height: number;
  created_at: number;
}

export interface SignatureRef {
  image_filename: string;
  source_signature_id?: string | null;
  width: number;
  height: number;
}
