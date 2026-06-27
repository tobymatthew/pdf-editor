import { DocumentMetadata, PageCropBox, PageInfo } from "../types/document";
import { NativeTextPageResult } from "../types/nativeText";
import { OCRPageResult } from "../types/ocr";
import { Edit, EditCreate, EditUpdate, FontInfo } from "../types/edit";

const BASE = "http://localhost:8000";

async function request<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    ...opts,
    headers: {
      ...(opts?.headers || {}),
      ...(opts?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export async function uploadDocument(file: File): Promise<DocumentMetadata> {
  const form = new FormData();
  form.append("file", file);
  return request("/documents", { method: "POST", body: form });
}

export async function getDocument(id: string): Promise<DocumentMetadata> {
  return request(`/documents/${id}`);
}

export async function deleteDocument(id: string): Promise<void> {
  await fetch(`${BASE}/documents/${id}`, { method: "DELETE" });
}

export async function listPages(documentId: string): Promise<PageInfo[]> {
  return request(`/documents/${documentId}/pages`);
}

export async function setPageCrop(
  documentId: string,
  pageNumber: number,
  crop: PageCropBox
): Promise<PageCropBox> {
  return request(`/documents/${documentId}/pages/${pageNumber}/crop`, {
    method: "PUT",
    body: JSON.stringify(crop),
  });
}

export async function clearPageCrop(
  documentId: string,
  pageNumber: number
): Promise<void> {
  await fetch(`${BASE}/documents/${documentId}/pages/${pageNumber}/crop`, {
    method: "DELETE",
  });
}

export async function listFonts(): Promise<FontInfo[]> {
  return request("/fonts");
}

export async function getPageImageUrl(
  documentId: string,
  pageNumber: number,
  preview: boolean = true
): Promise<string> {
  return `${BASE}/documents/${documentId}/pages/${pageNumber}/image?preview=${preview}`;
}

export async function runOcr(
  documentId: string,
  pageNumber: number
): Promise<OCRPageResult> {
  return request(`/documents/${documentId}/pages/${pageNumber}/ocr`, {
    method: "POST",
  });
}

export async function getOcrResult(
  documentId: string,
  pageNumber: number
): Promise<OCRPageResult> {
  return request(`/documents/${documentId}/pages/${pageNumber}/ocr`);
}

export async function getNativeTextResult(
  documentId: string,
  pageNumber: number
): Promise<NativeTextPageResult> {
  return request(`/documents/${documentId}/pages/${pageNumber}/native-text`);
}

export async function listEdits(
  documentId: string,
  pageNumber: number
): Promise<Edit[]> {
  return request(`/documents/${documentId}/pages/${pageNumber}/edits`);
}

export async function createEdit(
  documentId: string,
  pageNumber: number,
  data: EditCreate
): Promise<Edit> {
  return request(`/documents/${documentId}/pages/${pageNumber}/edits`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateEdit(
  documentId: string,
  pageNumber: number,
  editId: string,
  data: EditUpdate
): Promise<Edit> {
  return request(
    `/documents/${documentId}/pages/${pageNumber}/edits/${editId}`,
    { method: "PATCH", body: JSON.stringify(data) }
  );
}

export async function replaceEdits(
  documentId: string,
  pageNumber: number,
  edits: Edit[]
): Promise<Edit[]> {
  return request(`/documents/${documentId}/pages/${pageNumber}/edits`, {
    method: "PUT",
    body: JSON.stringify(edits),
  });
}

export async function deleteEdit(
  documentId: string,
  pageNumber: number,
  editId: string
): Promise<void> {
  await fetch(
    `${BASE}/documents/${documentId}/pages/${pageNumber}/edits/${editId}`,
    { method: "DELETE" }
  );
}

export async function exportDocument(documentId: string): Promise<Blob> {
  const res = await fetch(`${BASE}/documents/${documentId}/export`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Export failed");
  return res.blob();
}
