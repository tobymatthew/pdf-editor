import React, { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import { DocumentMetadata, PageCropBox, PageInfo } from "../types/document";
import { NativeTextBlock, NativeTextPageResult } from "../types/nativeText";
import { OCRBlock, OCRPageResult } from "../types/ocr";
import { Edit, EditCreate, EditTargetBBox, FontInfo } from "../types/edit";
import * as api from "../api/client";
import Toolbar from "./Toolbar";
import EditPanel from "./EditPanel";

const PageCanvas = dynamic(() => import("./PageCanvas"), { ssr: false });
type SaveStatus = "idle" | "saving" | "saved" | "error";

function cloneEdits(edits: Edit[]): Edit[] {
  return edits.map((edit) => ({
    ...edit,
    target_bbox: { ...edit.target_bbox },
    cover: { ...edit.cover },
    text: { ...edit.text },
  }));
}

export default function PdfEditor({ docId }: { docId: string }) {
  const [meta, setMeta] = useState<DocumentMetadata | null>(null);
  const [pages, setPages] = useState<PageInfo[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [imageUrl, setImageUrl] = useState("");
  const [ocrResult, setOcrResult] = useState<OCRPageResult | null>(null);
  const [nativeTextResult, setNativeTextResult] = useState<NativeTextPageResult | null>(null);
  const [edits, setEdits] = useState<Edit[]>([]);
  const [fonts, setFonts] = useState<FontInfo[]>([]);
  const [selectedEditId, setSelectedEditId] = useState<string | null>(null);
  const [showOcr, setShowOcr] = useState(true);
  const [ocrRunning, setOcrRunning] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [cropMode, setCropMode] = useState(false);
  const [cropBox, setCropBox] = useState<PageCropBox | null>(null);
  const [zoom, setZoom] = useState(1);
  const [undoStack, setUndoStack] = useState<Edit[][]>([]);
  const [redoStack, setRedoStack] = useState<Edit[][]>([]);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("saved");

  const scale = zoom;
  const formatFontLabel = useCallback(
    (font: FontInfo) => (font.style === "Regular" ? font.family : `${font.family} ${font.style}`),
    []
  );

  const matchesFontFamily = useCallback((font: FontInfo, family: string) => {
    const normalize = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, "");
    const requested = normalize(family);
    const candidates = new Set([
      normalize(font.family),
      normalize(`${font.family} ${font.style}`),
      normalize(`${font.family}-${font.style}`),
    ]);
    return candidates.has(requested);
  }, []);

  useEffect(() => {
    api.getDocument(docId).then(setMeta);
    api.listPages(docId).then(setPages);
    api.listFonts().then(setFonts).catch(() => setFonts([]));
  }, [docId]);

  useEffect(() => {
    if (!meta) return;
    const page = pages.find((p) => p.page_number === currentPage);
    if (!page) return;

    setCropBox(page.crop_box);
    api.getPageImageUrl(docId, currentPage, true).then(setImageUrl);
    api.listEdits(docId, currentPage).then((items) => {
      setEdits(items);
      setUndoStack([]);
      setRedoStack([]);
      setSaveStatus("saved");
    });
    api
      .getNativeTextResult(docId, currentPage)
      .then(setNativeTextResult)
      .catch(() => setNativeTextResult(null));
    api
      .getOcrResult(docId, currentPage)
      .then(setOcrResult)
      .catch(() => setOcrResult(null));
  }, [docId, currentPage, meta, pages]);

  const pageInfo = pages.find((p) => p.page_number === currentPage);
  const pageW = pageInfo?.width || 612;
  const pageH = pageInfo?.height || 792;

  const selectedEdit = edits.find((e) => e.id === selectedEditId) || null;

  const refreshPages = useCallback(async () => {
    const updated = await api.listPages(docId);
    setPages(updated);
    const current = updated.find((page) => page.page_number === currentPage);
    setCropBox(current?.crop_box || null);
  }, [currentPage, docId]);

  const rememberHistory = useCallback((previousEdits: Edit[]) => {
    setUndoStack((prev) => [...prev.slice(-49), cloneEdits(previousEdits)]);
    setRedoStack([]);
  }, []);

  const handleZoomIn = useCallback(() => {
    setZoom((value) => Math.min(3, Number((value + 0.1).toFixed(2))));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom((value) => Math.max(0.5, Number((value - 0.1).toFixed(2))));
  }, []);

  const handleResetZoom = useCallback(() => {
    setZoom(1);
  }, []);

  const handleToggleCrop = useCallback(async () => {
    if (!cropMode && !cropBox) {
      const initial = {
        x: pageW * 0.05,
        y: pageH * 0.05,
        w: pageW * 0.9,
        h: pageH * 0.9,
      };
      setCropBox(initial);
      try {
        const saved = await api.setPageCrop(docId, currentPage, initial);
        setCropBox(saved);
        await refreshPages();
      } catch (e) {
        console.error("Failed to initialize crop", e);
      }
    }
    setCropMode((value) => !value);
  }, [cropBox, cropMode, currentPage, docId, pageH, pageW, refreshPages]);

  const handleUpdateCropBox = useCallback(
    async (bbox: PageCropBox) => {
      setCropBox(bbox);
      try {
        const saved = await api.setPageCrop(docId, currentPage, bbox);
        setCropBox(saved);
        await refreshPages();
      } catch (e) {
        console.error("Failed to update crop", e);
      }
    },
    [currentPage, docId, refreshPages]
  );

  const handleClearCrop = useCallback(async () => {
    try {
      await api.clearPageCrop(docId, currentPage);
      setCropBox(null);
      setCropMode(false);
      await refreshPages();
    } catch (e) {
      console.error("Failed to clear crop", e);
    }
  }, [currentPage, docId, refreshPages]);

  const restoreEditSnapshot = useCallback(
    async (snapshot: Edit[], direction: "undo" | "redo") => {
      const currentSnapshot = cloneEdits(edits);
      setSaveStatus("saving");
      try {
        const restored = await api.replaceEdits(docId, currentPage, snapshot);
        setEdits(restored);
        setSelectedEditId((selectedId) =>
          selectedId && restored.some((edit) => edit.id === selectedId) ? selectedId : null
        );
        if (direction === "undo") {
          setUndoStack((prev) => prev.slice(0, -1));
          setRedoStack((prev) => [...prev.slice(-49), currentSnapshot]);
        } else {
          setRedoStack((prev) => prev.slice(0, -1));
          setUndoStack((prev) => [...prev.slice(-49), currentSnapshot]);
        }
        setSaveStatus("saved");
      } catch (e) {
        console.error(`Failed to ${direction}`, e);
        setSaveStatus("error");
      }
    },
    [currentPage, docId, edits]
  );

  const handleUndo = useCallback(async () => {
    const snapshot = undoStack[undoStack.length - 1];
    if (!snapshot) return;
    await restoreEditSnapshot(snapshot, "undo");
  }, [restoreEditSnapshot, undoStack]);

  const handleRedo = useCallback(async () => {
    const snapshot = redoStack[redoStack.length - 1];
    if (!snapshot) return;
    await restoreEditSnapshot(snapshot, "redo");
  }, [redoStack, restoreEditSnapshot]);

  const handlePrevPage = useCallback(() => {
    setCurrentPage((p) => Math.max(1, p - 1));
    setSelectedEditId(null);
  }, []);

  const handleNextPage = useCallback(() => {
    if (!meta) return;
    setCurrentPage((p) => Math.min(meta.page_count, p + 1));
    setSelectedEditId(null);
  }, [meta]);

  const handleRunOcr = useCallback(async () => {
    setOcrRunning(true);
    try {
      const result = await api.runOcr(docId, currentPage);
      setOcrResult(result);
      setShowOcr(true);
    } catch (e) {
      console.error("OCR failed", e);
      alert("OCR failed. Make sure EasyOCR is installed.");
    }
    setOcrRunning(false);
  }, [docId, currentPage]);

  const createEditFromBlock = useCallback(
    async (
      block: { text: string; bbox: EditTargetBBox },
      textStyle?: {
        fontSize?: number;
        fontFamily?: string;
        color?: string | null;
        bold?: boolean;
        italic?: boolean;
      }
    ) => {
      const matchedFont =
        fonts.find((font) => matchesFontFamily(font, textStyle?.fontFamily || "Arial")) ||
        null;
      const createData: EditCreate = {
        page_number: currentPage,
        type: "text_replacement",
        target_bbox: {
          x: block.bbox.x,
          y: block.bbox.y,
          w: block.bbox.w,
          h: block.bbox.h,
        },
        cover: {
          enabled: true,
          method: "sampled_background",
          padding: 4,
        },
        text: {
          value: block.text,
          x: block.bbox.x,
          y: block.bbox.y,
          font_size: textStyle?.fontSize || Math.max(8, Math.round(block.bbox.h * 0.7)),
          font_id: matchedFont?.id || undefined,
          font_family: matchedFont ? formatFontLabel(matchedFont) : textStyle?.fontFamily || "Arial",
          color: textStyle?.color || "#111111",
          bold: textStyle?.bold || false,
          italic: textStyle?.italic || false,
        },
      };
      try {
        const previousEdits = cloneEdits(edits);
        setSaveStatus("saving");
        const edit = await api.createEdit(docId, currentPage, createData);
        rememberHistory(previousEdits);
        setEdits((prev) => [...prev, edit]);
        setSelectedEditId(edit.id);
        setSaveStatus("saved");
      } catch (e) {
        console.error("Failed to create edit", e);
        setSaveStatus("error");
      }
    },
    [docId, currentPage, edits, fonts, formatFontLabel, matchesFontFamily, rememberHistory]
  );

  const handleSelectOcrBlock = useCallback(
    async (block: OCRBlock) => {
      await createEditFromBlock(block);
    },
    [createEditFromBlock]
  );

  const handleSelectNativeTextBlock = useCallback(
    async (block: NativeTextBlock) => {
      await createEditFromBlock(block, {
        fontSize: block.style.font_size,
        fontFamily: block.style.font_name,
        color: block.style.color,
        bold: block.style.bold,
        italic: block.style.italic,
      });
    },
    [createEditFromBlock]
  );

  const handleUpdateEditText = useCallback(
    async (value: string) => {
      if (!selectedEditId) return;
      try {
        const previousEdits = cloneEdits(edits);
        setSaveStatus("saving");
        const edit = await api.updateEdit(docId, currentPage, selectedEditId, {
          text: { ...selectedEdit!.text, value },
        });
        rememberHistory(previousEdits);
        setEdits((prev) => prev.map((e) => (e.id === edit.id ? edit : e)));
        setSaveStatus("saved");
      } catch (e) {
        console.error("Failed to update edit", e);
        setSaveStatus("error");
      }
    },
    [docId, currentPage, edits, rememberHistory, selectedEditId, selectedEdit]
  );

  const handleUpdateFontSize = useCallback(
    async (size: number) => {
      if (!selectedEditId) return;
      try {
        const previousEdits = cloneEdits(edits);
        setSaveStatus("saving");
        const edit = await api.updateEdit(
          docId,
          currentPage,
          selectedEditId,
          { text: { ...selectedEdit!.text, font_size: size } }
        );
        rememberHistory(previousEdits);
        setEdits((prev) => prev.map((e) => (e.id === edit.id ? edit : e)));
        setSaveStatus("saved");
      } catch (e) {
        console.error("Failed to update font size", e);
        setSaveStatus("error");
      }
    },
    [docId, currentPage, edits, rememberHistory, selectedEditId, selectedEdit]
  );

  const handleUpdateColor = useCallback(
    async (color: string) => {
      if (!selectedEditId) return;
      try {
        const previousEdits = cloneEdits(edits);
        setSaveStatus("saving");
        const edit = await api.updateEdit(
          docId,
          currentPage,
          selectedEditId,
          { text: { ...selectedEdit!.text, color } }
        );
        rememberHistory(previousEdits);
        setEdits((prev) => prev.map((e) => (e.id === edit.id ? edit : e)));
        setSaveStatus("saved");
      } catch (e) {
        console.error("Failed to update color", e);
        setSaveStatus("error");
      }
    },
    [docId, currentPage, edits, rememberHistory, selectedEditId, selectedEdit]
  );

  const handleUpdateFont = useCallback(
    async (font: FontInfo | null) => {
      if (!selectedEditId) return;
      try {
        const previousEdits = cloneEdits(edits);
        setSaveStatus("saving");
        const edit = await api.updateEdit(docId, currentPage, selectedEditId, {
          text: {
            ...selectedEdit!.text,
            font_id: font?.id || null,
            font_family: font ? formatFontLabel(font) : selectedEdit!.text.font_family,
          },
        });
        rememberHistory(previousEdits);
        setEdits((prev) => prev.map((e) => (e.id === edit.id ? edit : e)));
        setSaveStatus("saved");
      } catch (e) {
        console.error("Failed to update font", e);
        setSaveStatus("error");
      }
    },
    [docId, currentPage, edits, rememberHistory, selectedEditId, selectedEdit, formatFontLabel]
  );

  const handleUpdateCoverMethod = useCallback(
    async (method: "white" | "sampled_background" | "inpaint") => {
      if (!selectedEditId) return;
      try {
        const previousEdits = cloneEdits(edits);
        setSaveStatus("saving");
        const edit = await api.updateEdit(
          docId,
          currentPage,
          selectedEditId,
          { cover: { ...selectedEdit!.cover, method } }
        );
        rememberHistory(previousEdits);
        setEdits((prev) => prev.map((e) => (e.id === edit.id ? edit : e)));
        setSaveStatus("saved");
      } catch (e) {
        console.error("Failed to update cover method", e);
        setSaveStatus("error");
      }
    },
    [docId, currentPage, edits, rememberHistory, selectedEditId, selectedEdit]
  );

  const handleDeleteEdit = useCallback(async () => {
    if (!selectedEditId) return;
    try {
      const previousEdits = cloneEdits(edits);
      setSaveStatus("saving");
      await api.deleteEdit(docId, currentPage, selectedEditId);
      rememberHistory(previousEdits);
      setEdits((prev) => prev.filter((e) => e.id !== selectedEditId));
      setSelectedEditId(null);
      setSaveStatus("saved");
    } catch (e) {
      console.error("Failed to delete edit", e);
      setSaveStatus("error");
    }
  }, [docId, currentPage, edits, rememberHistory, selectedEditId]);

  const handleUpdateEditBbox = useCallback(
    async (editId: string, bbox: EditTargetBBox) => {
      try {
        const previousEdits = cloneEdits(edits);
        setSaveStatus("saving");
        const edit = await api.updateEdit(docId, currentPage, editId, {
          target_bbox: bbox,
          text: { ...edits.find((e) => e.id === editId)!.text, x: bbox.x, y: bbox.y },
        });
        rememberHistory(previousEdits);
        setEdits((prev) => prev.map((e) => (e.id === edit.id ? edit : e)));
        setSaveStatus("saved");
      } catch (e) {
        console.error("Failed to update bbox", e);
        setSaveStatus("error");
      }
    },
    [docId, currentPage, edits, rememberHistory]
  );

  const handleExport = useCallback(async () => {
    setExporting(true);
    try {
      const blob = await api.exportDocument(docId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "edited.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Export failed", e);
      alert("Export failed");
    }
    setExporting(false);
  }, [docId]);

  const handlePreview = useCallback(async () => {
    setPreviewing(true);
    try {
      const blob = await api.exportDocument(docId);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener,noreferrer");
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (e) {
      console.error("Preview failed", e);
      alert("Preview failed");
    }
    setPreviewing(false);
  }, [docId]);

  if (!meta) {
    return <div style={{ padding: 40, textAlign: "center" }}>Loading document...</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <Toolbar
        pageNumber={currentPage}
        totalPages={meta.page_count}
        onPrevPage={handlePrevPage}
        onNextPage={handleNextPage}
        onRunOcr={handleRunOcr}
        onToggleOcr={() => setShowOcr((v) => !v)}
        showOcr={showOcr}
        zoom={zoom}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onResetZoom={handleResetZoom}
        canUndo={undoStack.length > 0}
        canRedo={redoStack.length > 0}
        onUndo={handleUndo}
        onRedo={handleRedo}
        saveStatus={saveStatus}
        cropMode={cropMode}
        hasCrop={!!cropBox}
        onToggleCrop={handleToggleCrop}
        onClearCrop={handleClearCrop}
        onPreview={handlePreview}
        onExport={handleExport}
        previewing={previewing}
        exporting={exporting}
        ocrRunning={ocrRunning}
        hasSelectableText={
          Boolean(ocrResult?.blocks.length) || Boolean(nativeTextResult?.blocks.length)
        }
      />

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <div
          style={{
            flex: 1,
            display: "flex",
            justifyContent: "center",
            alignItems: "flex-start",
            padding: 24,
            overflow: "auto",
            background: "#f3f4f6",
          }}
        >
          <PageCanvas
            imageUrl={imageUrl}
            pageWidth={pageW}
            pageHeight={pageH}
            ocrBlocks={ocrResult?.blocks || []}
            nativeTextBlocks={nativeTextResult?.blocks || []}
            edits={edits}
            selectedEditId={selectedEditId}
            cropBox={cropBox}
            cropMode={cropMode}
            onSelectEdit={setSelectedEditId}
            onUpdateEditBbox={handleUpdateEditBbox}
            onUpdateCropBox={handleUpdateCropBox}
            onSelectOcrBlock={handleSelectOcrBlock}
            onSelectNativeTextBlock={handleSelectNativeTextBlock}
            showOcr={showOcr}
            scale={scale}
          />
        </div>

        <EditPanel
          selectedEdit={selectedEdit}
          fonts={fonts}
          onUpdateText={handleUpdateEditText}
          onUpdateFontSize={handleUpdateFontSize}
          onUpdateColor={handleUpdateColor}
          onUpdateFont={handleUpdateFont}
          onUpdateCoverMethod={handleUpdateCoverMethod}
          onDeleteEdit={handleDeleteEdit}
        />
      </div>
    </div>
  );
}
