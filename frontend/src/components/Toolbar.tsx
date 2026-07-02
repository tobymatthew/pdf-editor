import React from "react";

interface ToolbarProps {
  pageNumber: number;
  totalPages: number;
  onPrevPage: () => void;
  onNextPage: () => void;
  onRunOcr: () => void;
  onToggleOcr: () => void;
  showOcr: boolean;
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetZoom: () => void;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  saveStatus: "idle" | "saving" | "saved" | "error";
  cropMode: boolean;
  hasCrop: boolean;
  onToggleCrop: () => void;
  onClearCrop: () => void;
  onPreview: () => void;
  onExport: () => void;
  previewing: boolean;
  exporting: boolean;
  ocrRunning: boolean;
  hasSelectableText: boolean;
  onAddSignature: () => void;
  insertTextMode: boolean;
  onToggleInsertText: () => void;
}

export default function Toolbar({
  pageNumber,
  totalPages,
  onPrevPage,
  onNextPage,
  onRunOcr,
  onToggleOcr,
  showOcr,
  zoom,
  onZoomIn,
  onZoomOut,
  onResetZoom,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  saveStatus,
  cropMode,
  hasCrop,
  onToggleCrop,
  onClearCrop,
  onPreview,
  onExport,
  previewing,
  exporting,
  ocrRunning,
  hasSelectableText,
  onAddSignature,
  insertTextMode,
  onToggleInsertText,
}: ToolbarProps) {
  return (
    <div style={styles.toolbar}>
      <div style={styles.group}>
        <button
          style={styles.btn}
          onClick={onPrevPage}
          disabled={pageNumber <= 1}
        >
          ◀ Prev
        </button>
        <span style={styles.pageInfo}>
          Page {pageNumber} of {totalPages}
        </span>
        <button
          style={styles.btn}
          onClick={onNextPage}
          disabled={pageNumber >= totalPages}
        >
          Next ▶
        </button>
      </div>

      <div style={styles.group}>
        <button style={styles.iconBtn} onClick={onZoomOut} disabled={zoom <= 0.5} title="Zoom out">
          -
        </button>
        <button style={styles.zoomBtn} onClick={onResetZoom} title="Reset zoom">
          {Math.round(zoom * 100)}%
        </button>
        <button style={styles.iconBtn} onClick={onZoomIn} disabled={zoom >= 3} title="Zoom in">
          +
        </button>
      </div>

      <div style={styles.group}>
        <button style={styles.btn} onClick={onUndo} disabled={!canUndo}>
          Undo
        </button>
        <button style={styles.btn} onClick={onRedo} disabled={!canRedo}>
          Redo
        </button>
        <span
          style={{
            ...styles.saveStatus,
            color: saveStatus === "error" ? "#b91c1c" : "#4b5563",
          }}
        >
          {saveStatus === "saving"
            ? "Saving..."
            : saveStatus === "error"
            ? "Save failed"
            : "Saved"}
        </span>
      </div>

      <div style={styles.group}>
        <button
          style={styles.btn}
          onClick={onRunOcr}
          disabled={ocrRunning}
        >
          {ocrRunning ? "OCR running..." : "Run OCR"}
        </button>
        {hasSelectableText && (
          <button
            style={{
              ...styles.btn,
              background: showOcr ? "#3b82f6" : "#e5e7eb",
              color: showOcr ? "#fff" : "#000",
            }}
            onClick={onToggleOcr}
          >
            {showOcr ? "Hide Text Blocks" : "Show Text Blocks"}
          </button>
        )}
      </div>

      <div style={styles.group}>
        <button
          style={{
            ...styles.btn,
            background: cropMode ? "#f59e0b" : "#fff",
            color: cropMode ? "#111827" : "#000",
          }}
          onClick={onToggleCrop}
        >
          {cropMode ? "Done Crop" : "Crop"}
        </button>
        {hasCrop && (
          <button style={styles.btn} onClick={onClearCrop}>
            Clear Crop
          </button>
        )}
      </div>

      <div style={styles.group}>
        <button
          style={{
            ...styles.btn,
            background: insertTextMode ? "#dbeafe" : "#fff",
            color: insertTextMode ? "#1d4ed8" : "#000",
            borderColor: insertTextMode ? "#93c5fd" : "#d1d5db",
          }}
          onClick={onToggleInsertText}
        >
          {insertTextMode ? "Click Page To Place Text" : "Add Text"}
        </button>
        <button style={{ ...styles.btn, background: "#eef2ff", color: "#4338ca" }} onClick={onAddSignature}>
          ✎ Add Signature
        </button>
      </div>

      <div style={styles.group}>
        <button
          style={styles.btn}
          onClick={onPreview}
          disabled={previewing || exporting}
        >
          {previewing ? "Previewing..." : "Preview PDF"}
        </button>
        <button
          style={{ ...styles.btn, background: "#059669", color: "#fff" }}
          onClick={onExport}
          disabled={exporting || previewing}
        >
          {exporting ? "Exporting..." : "Export PDF"}
        </button>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  toolbar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "8px 16px",
    background: "#fff",
    borderBottom: "1px solid #e5e7eb",
    gap: 12,
    flexWrap: "wrap",
  },
  group: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  btn: {
    padding: "6px 12px",
    fontSize: 13,
    border: "1px solid #d1d5db",
    borderRadius: 4,
    background: "#fff",
    cursor: "pointer",
  },
  iconBtn: {
    width: 30,
    height: 30,
    fontSize: 16,
    border: "1px solid #d1d5db",
    borderRadius: 4,
    background: "#fff",
    cursor: "pointer",
  },
  zoomBtn: {
    minWidth: 56,
    height: 30,
    padding: "0 8px",
    fontSize: 13,
    border: "1px solid #d1d5db",
    borderRadius: 4,
    background: "#fff",
    cursor: "pointer",
  },
  pageInfo: {
    fontSize: 13,
    fontWeight: 500,
  },
  saveStatus: {
    minWidth: 72,
    fontSize: 12,
  },
};
