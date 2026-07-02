import React, { useState, useRef, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import * as api from "../api/client";
import { SignatureInfo } from "../types/signature";
import type { SignaturePadHandle } from "./SignaturePad";

const SignaturePad = dynamic(() => import("./SignaturePad"), { ssr: false });

interface SignatureManagerProps {
  onPick: (signature: SignatureInfo) => void;
  onClose: () => void;
}

type Tab = "library" | "draw" | "upload";

export default function SignatureManager({ onPick, onClose }: SignatureManagerProps) {
  const [tab, setTab] = useState<Tab>("library");
  const [signatures, setSignatures] = useState<SignatureInfo[]>([]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const padRef = useRef<SignaturePadHandle | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [aggressiveCleanup, setAggressiveCleanup] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setSignatures(await api.listSignatures());
    } catch (e) {
      console.error("Failed to load signatures", e);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleSaveDraw = useCallback(async () => {
    setError(null);
    const result = padRef.current?.exportPng();
    if (!result) {
      setError("Draw a signature first.");
      return;
    }
    setBusy(true);
    try {
      await api.createSignature(result.blob, name.trim() || undefined);
      padRef.current?.clear();
      setName("");
      await refresh();
      setTab("library");
    } catch (e) {
      setError("Failed to save signature.");
    } finally {
      setBusy(false);
    }
  }, [name, refresh]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setPendingFile(file);
    setError(null);
  }, []);

  const handleSaveUpload = useCallback(async () => {
    setError(null);
    if (!pendingFile) {
      setError("Choose an image file first.");
      return;
    }
    setBusy(true);
    try {
      await api.createSignature(pendingFile, name.trim() || undefined, {
        aggressive: aggressiveCleanup,
      });
      setPendingFile(null);
      if (fileRef.current) fileRef.current.value = "";
      setName("");
      await refresh();
      setTab("library");
    } catch (e) {
      setError("Failed to save signature.");
    } finally {
      setBusy(false);
    }
  }, [aggressiveCleanup, name, pendingFile, refresh]);

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await api.deleteSignature(id);
        setSignatures((prev) => prev.filter((s) => s.id !== id));
      } catch (e) {
        console.error("Failed to delete signature", e);
      }
    },
    []
  );

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div style={styles.header}>
          <h2 style={styles.title}>Signatures</h2>
          <button style={styles.closeBtn} onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div style={styles.tabs}>
          <TabBtn active={tab === "library"} onClick={() => setTab("library")}>
            Library ({signatures.length})
          </TabBtn>
          <TabBtn active={tab === "draw"} onClick={() => setTab("draw")}>
            Draw new
          </TabBtn>
          <TabBtn active={tab === "upload"} onClick={() => setTab("upload")}>
            Upload
          </TabBtn>
        </div>

        {error && <div style={styles.error}>{error}</div>}

        {tab === "library" && (
          <div style={styles.libraryBody}>
            {signatures.length === 0 ? (
              <p style={styles.empty}>
                No saved signatures yet. Draw or upload one to get started.
              </p>
            ) : (
              <div style={styles.grid}>
                {signatures.map((sig) => (
                  <div key={sig.id} style={styles.card}>
                    <img
                      src={api.getSignatureImageUrl(sig.id)}
                      alt={sig.name}
                      style={styles.thumb}
                    />
                    <div style={styles.cardMeta}>
                      <span style={styles.cardName}>{sig.name}</span>
                      <span style={styles.cardDims}>
                        {sig.width}×{sig.height}
                      </span>
                    </div>
                    <div style={styles.cardActions}>
                      <button
                        style={styles.useBtn}
                        onClick={() => onPick(sig)}
                      >
                        Use
                      </button>
                      <button
                        style={styles.delBtn}
                        onClick={() => handleDelete(sig.id)}
                        aria-label="Delete"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "draw" && (
          <div style={styles.drawBody}>
            <p style={styles.hint}>
              Draw your signature below. The background is transparent.
            </p>
            <SignaturePad ref={padRef} width={480} height={200} />
            <label style={styles.label}>Name (optional)</label>
            <input
              style={styles.input}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. John Doe"
            />
            <div style={styles.row}>
              <button
                style={styles.secondaryBtn}
                onClick={() => padRef.current?.clear()}
                disabled={busy}
              >
                Clear
              </button>
              <button style={styles.primaryBtn} onClick={handleSaveDraw} disabled={busy}>
                {busy ? "Saving..." : "Save to library"}
              </button>
            </div>
          </div>
        )}

        {tab === "upload" && (
          <div style={styles.drawBody}>
            <p style={styles.hint}>
              Upload a PNG or JPG of your signature. White backgrounds are made
              transparent automatically.
            </p>
            <input
              ref={fileRef}
              type="file"
              accept="image/png,image/jpeg"
              onChange={handleFileChange}
              style={styles.fileInput}
            />
            {pendingFile && (
              <div style={styles.previewWrap}>
                <img
                  src={URL.createObjectURL(pendingFile)}
                  alt="preview"
                  style={styles.preview}
                />
              </div>
            )}
            <label style={styles.checkRow}>
              <input
                type="checkbox"
                checked={aggressiveCleanup}
                onChange={(e) => setAggressiveCleanup(e.target.checked)}
              />
              <span>Use aggressive background removal</span>
            </label>
            <p style={styles.smallHint}>
              Best for signatures photographed on paper with shadows, beige tone, or visible page texture.
            </p>
            <label style={styles.label}>Name (optional)</label>
            <input
              style={styles.input}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. John Doe"
            />
            <div style={styles.row}>
              <button
                style={styles.secondaryBtn}
                onClick={() => {
                  setPendingFile(null);
                  if (fileRef.current) fileRef.current.value = "";
                }}
                disabled={busy}
              >
                Reset
              </button>
              <button
                style={styles.primaryBtn}
                onClick={handleSaveUpload}
                disabled={busy}
              >
                {busy ? "Saving..." : "Save to library"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function TabBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      style={{
        ...styles.tab,
        borderBottom: active ? "2px solid #3b82f6" : "2px solid transparent",
        color: active ? "#3b82f6" : "#6b7280",
      }}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(0,0,0,0.4)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
  },
  modal: {
    width: 560,
    maxHeight: "85vh",
    overflowY: "auto",
    background: "#fff",
    borderRadius: 10,
    boxShadow: "0 10px 40px rgba(0,0,0,0.25)",
    padding: 20,
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 12,
  },
  title: { margin: 0, fontSize: 18, fontWeight: 600 },
  closeBtn: {
    fontSize: 22,
    lineHeight: 1,
    border: "none",
    background: "transparent",
    cursor: "pointer",
    color: "#6b7280",
  },
  tabs: { display: "flex", gap: 4, borderBottom: "1px solid #e5e7eb", marginBottom: 16 },
  tab: {
    padding: "8px 14px",
    fontSize: 14,
    background: "transparent",
    border: "none",
    cursor: "pointer",
    fontWeight: 500,
  },
  libraryBody: { marginTop: 4 },
  empty: { color: "#6b7280", fontSize: 14, textAlign: "center", padding: "24px 0" },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(2, 1fr)",
    gap: 12,
  },
  card: {
    border: "1px solid #e5e7eb",
    borderRadius: 8,
    padding: 10,
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  thumb: {
    width: "100%",
    height: 70,
    objectFit: "contain",
    background:
      "repeating-linear-gradient(45deg, #fafafa, #fafafa 10px, #f3f4f6 10px, #f3f4f6 20px)",
    borderRadius: 4,
  },
  cardMeta: { display: "flex", justifyContent: "space-between", alignItems: "center" },
  cardName: { fontSize: 13, fontWeight: 500 },
  cardDims: { fontSize: 11, color: "#9ca3af" },
  cardActions: { display: "flex", gap: 8 },
  useBtn: {
    flex: 1,
    padding: "6px 10px",
    fontSize: 13,
    border: "1px solid #3b82f6",
    borderRadius: 4,
    background: "#3b82f6",
    color: "#fff",
    cursor: "pointer",
  },
  delBtn: {
    padding: "6px 10px",
    fontSize: 13,
    border: "1px solid #e5e7eb",
    borderRadius: 4,
    background: "#fff",
    color: "#b91c1c",
    cursor: "pointer",
  },
  drawBody: { display: "flex", flexDirection: "column", gap: 8 },
  hint: { color: "#6b7280", fontSize: 13, margin: "0 0 4px 0" },
  smallHint: { color: "#6b7280", fontSize: 12, margin: "-2px 0 4px 0", lineHeight: 1.5 },
  label: { fontSize: 12, fontWeight: 500, color: "#374151", marginTop: 8 },
  checkRow: { display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "#374151" },
  input: {
    width: "100%",
    padding: "6px 8px",
    fontSize: 14,
    border: "1px solid #d1d5db",
    borderRadius: 4,
    boxSizing: "border-box",
  },
  row: { display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 12 },
  primaryBtn: {
    padding: "8px 16px",
    fontSize: 14,
    border: "none",
    borderRadius: 4,
    background: "#059669",
    color: "#fff",
    cursor: "pointer",
  },
  secondaryBtn: {
    padding: "8px 16px",
    fontSize: 14,
    border: "1px solid #d1d5db",
    borderRadius: 4,
    background: "#fff",
    cursor: "pointer",
  },
  fileInput: { fontSize: 13 },
  previewWrap: {
    border: "1px solid #e5e7eb",
    borderRadius: 6,
    padding: 8,
    background: "#f9fafb",
  },
  preview: { maxHeight: 120, display: "block", margin: "0 auto" },
  error: {
    background: "#fef2f2",
    color: "#b91c1c",
    border: "1px solid #fecaca",
    borderRadius: 4,
    padding: "6px 10px",
    fontSize: 13,
    marginBottom: 12,
  },
};
