import React, { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/router";
import { useDropzone } from "react-dropzone";
import * as api from "../api/client";
import PdfEditor from "../components/PdfEditor";

export default function Home() {
  const router = useRouter();
  const initialDocId = typeof router.query.docId === "string" ? router.query.docId : null;
  const [docId, setDocId] = useState<string | null>(initialDocId);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    if (typeof router.query.docId === "string") {
      setDocId(router.query.docId);
    }
  }, [router.query.docId]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;
    setUploading(true);
    try {
      const meta = await api.uploadDocument(file);
      setDocId(meta.id);
      router.replace({ pathname: "/", query: { docId: meta.id } }, undefined, {
        shallow: true,
      });
    } catch (e) {
      console.error("Upload failed", e);
      alert("Upload failed. Make sure backend is running.");
    }
    setUploading(false);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
  });

  if (docId) {
    return <PdfEditor docId={docId} />;
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        background: "#f3f4f6",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <h1 style={{ fontSize: 24, marginBottom: 8 }}>Scan-Aware PDF Editor</h1>
      <p style={{ color: "#6b7280", marginBottom: 24 }}>
        Upload a PDF to start editing (supports scanned documents, forms, tables)
      </p>
      <div
        {...getRootProps()}
        style={{
          width: 400,
          height: 200,
          border: "2px dashed #d1d5db",
          borderRadius: 8,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          background: isDragActive ? "#eff6ff" : "#fff",
          transition: "background 0.2s",
        }}
      >
        <input {...getInputProps()} />
        <p style={{ color: "#6b7280", textAlign: "center", padding: 16 }}>
          {uploading
            ? "Uploading..."
            : isDragActive
            ? "Drop PDF here"
            : "Drag & drop a PDF here, or click to select"}
        </p>
      </div>
    </div>
  );
}
