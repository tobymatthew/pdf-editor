import React from "react";
import { Edit, FontInfo } from "../types/edit";

interface EditPanelProps {
  selectedEdit: Edit | null;
  fonts: FontInfo[];
  onUpdateText: (value: string) => void;
  onUpdateFontSize: (size: number) => void;
  onUpdateColor: (color: string) => void;
  onUpdateFont: (font: FontInfo | null) => void;
  onUpdateCoverMethod: (method: "white" | "sampled_background" | "inpaint") => void;
  onDeleteEdit: () => void;
}

export default function EditPanel({
  selectedEdit,
  fonts,
  onUpdateText,
  onUpdateFontSize,
  onUpdateColor,
  onUpdateFont,
  onUpdateCoverMethod,
  onDeleteEdit,
}: EditPanelProps) {
  if (!selectedEdit) {
    return (
      <div style={styles.panel}>
        <p style={{ color: "#6b7280", fontSize: 14 }}>
          Select a text block or an existing edit to modify it.
        </p>
      </div>
    );
  }

  const matchesFamily = (font: FontInfo, family: string) => {
    const normalize = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, "");
    const requested = normalize(family);
    return new Set([
      normalize(font.family),
      normalize(`${font.family} ${font.style}`),
      normalize(`${font.family}-${font.style}`),
    ]).has(requested);
  };

  const selectedFontId =
    selectedEdit.text.font_id ||
    fonts.find((font) => matchesFamily(font, selectedEdit.text.font_family))?.id ||
    "";

  return (
    <div style={styles.panel}>
      <h3 style={styles.title}>Edit Properties</h3>

      <label style={styles.label}>Replacement Text</label>
      <input
        style={styles.input}
        value={selectedEdit.text.value}
        onChange={(e) => onUpdateText(e.target.value)}
        placeholder="Enter new text..."
      />

      <label style={styles.label}>Font Size</label>
      <input
        style={styles.input}
        type="number"
        value={selectedEdit.text.font_size}
        onChange={(e) => onUpdateFontSize(Number(e.target.value))}
        min={6}
        max={200}
      />

      <label style={styles.label}>Font</label>
      <select
        style={styles.input}
        value={selectedFontId}
        onChange={(e) => {
          const font = fonts.find((item) => item.id === e.target.value) || null;
          onUpdateFont(font);
        }}
      >
        <option value="">Auto / family fallback</option>
        {fonts.map((font) => (
          <option key={font.id} value={font.id}>
            {font.family} {font.style !== "Regular" ? `(${font.style})` : ""}
            {font.weight ? ` · ${font.weight}` : ""}
          </option>
        ))}
      </select>

      <label style={styles.label}>Text Color</label>
      <input
        style={{ ...styles.input, padding: 2 }}
        type="color"
        value={selectedEdit.text.color}
        onChange={(e) => onUpdateColor(e.target.value)}
      />

      <label style={styles.label}>Cover Method</label>
      <select
        style={styles.input}
        value={selectedEdit.cover.method}
        onChange={(e) =>
          onUpdateCoverMethod(
            e.target.value as "white" | "sampled_background" | "inpaint"
          )
        }
      >
        <option value="white">White</option>
        <option value="sampled_background">Sampled Background</option>
        <option value="inpaint">Inpaint (advanced)</option>
      </select>

      <button style={styles.deleteBtn} onClick={onDeleteEdit}>
        Delete Edit
      </button>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    width: 260,
    padding: 16,
    background: "#fff",
    borderLeft: "1px solid #e5e7eb",
    overflowY: "auto",
  },
  title: {
    margin: "0 0 16px 0",
    fontSize: 16,
    fontWeight: 600,
  },
  label: {
    display: "block",
    fontSize: 12,
    fontWeight: 500,
    color: "#374151",
    marginBottom: 4,
    marginTop: 12,
  },
  input: {
    width: "100%",
    padding: "6px 8px",
    fontSize: 14,
    border: "1px solid #d1d5db",
    borderRadius: 4,
    boxSizing: "border-box",
  },
  deleteBtn: {
    marginTop: 24,
    width: "100%",
    padding: "8px 16px",
    background: "#ef4444",
    color: "#fff",
    border: "none",
    borderRadius: 4,
    cursor: "pointer",
    fontSize: 14,
  },
};
