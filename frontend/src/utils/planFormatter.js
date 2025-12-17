// Lightweight Plan Markdown formatter extracted from PlannerPanel.
// Exports a function `renderPlanMarkdown(md)` that returns HTML string.
// Keeps table support: header row with `|` and a separator row (---) below.

const escapeHtml = (unsafe) => {
  return (unsafe || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
};

// Format inline markup: bold (**text**) and inline code (`code`)
const formatInline = (text) => {
  const escaped = escapeHtml(text || "");
  // bold first, then inline code
  return escaped
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, "<code style=\"background-color:#ccc;padding:2px 4px;border-radius:4px;\">$1</code>");
};

export function renderPlanMarkdown(md) {
  if (!md) return "";
  const raw = String(md || "");
  const inputLines = raw.split(/\r?\n/);
  const out = [];
  let inUl = false;
  let inOl = false;
  let inCode = false;
  let codeBuffer = [];

  for (let i = 0; i < inputLines.length; i++) {
    const rawLine = inputLines[i];

    if (rawLine.trim().startsWith("```")) {
      if (!inCode) {
        inCode = true;
        codeBuffer = [];
      } else {
        inCode = false;
        const codeHtml = escapeHtml(codeBuffer.join("\n"));
        out.push(`<pre><code>${codeHtml}</code></pre>`);
        codeBuffer = [];
      }
      continue;
    }

    if (inCode) {
      codeBuffer.push(rawLine);
      continue;
    }

    const line = rawLine.trim();
    const nextLine = inputLines[i + 1] || "";

    // table detection: header row contains '|' and next line is a separator with '---' or alignment markers
    const looksLikeTable = rawLine.includes("|") && /[-:\s|]+/.test(nextLine);
    if (looksLikeTable) {
      if (inUl) { out.push("</ul>"); inUl = false; }
      if (inOl) { out.push("</ol>"); inOl = false; }

      // split header and separator keeping positional indices so we can map alignments
      const rawHeaderParts = rawLine.split("|");
      const rawSepParts = (nextLine || "").split("|");

      const headerCells = [];
      const alignments = [];
      for (let k = 0; k < rawHeaderParts.length; k++) {
        const h = (rawHeaderParts[k] || "").trim();
        if (h === "") continue;
        headerCells.push(formatInline(h));
        const sep = (rawSepParts[k] || "").trim();
        // determine alignment from separator markers: :--- left, ---: right, :---: center
        let align = "left";
        const sepOnly = sep.replace(/\s/g, "");
        if (/^:?-{3,}:?$/.test(sepOnly)) {
          if (sepOnly.startsWith(":") && sepOnly.endsWith(":")) align = "center";
          else if (sepOnly.startsWith(":")) align = "left";
          else if (sepOnly.endsWith(":")) align = "right";
          else align = "left";
        }
        alignments.push(align);
      }

      const rows = [];
      let j = i + 2; // skip separator line
      while (j < inputLines.length && inputLines[j].includes("|")) {
        const rawRowParts = inputLines[j].split("|");
        const rowCells = [];
        // build row cells corresponding to headerCells positions
        let headerIndex = 0;
        for (let k = 0; k < rawRowParts.length && headerIndex < headerCells.length; k++) {
          const hpart = (rawHeaderParts[k] || "").trim();
          if (hpart === "") continue; // skip positions that were empty in header
          const cell = (rawRowParts[k] || "").trim();
          rowCells.push(formatInline(cell));
          headerIndex += 1;
        }
        rows.push(rowCells);
        j += 1;
      }

      out.push('<table class="md-table">');
      out.push('<thead><tr>' + headerCells.map((h, idx) => `<th style="text-align:${alignments[idx]}">${h}</th>`).join("") + '</tr></thead>');
      if (rows.length > 0) {
        out.push('<tbody>');
        rows.forEach((r) => {
          out.push('<tr>' + r.map((c, idx) => `<td style="text-align:${alignments[idx] || 'left'}">${c}</td>`).join("") + '</tr>');
        });
        out.push('</tbody>');
      }
      out.push('</table>');
      i = j - 1;
      continue;
    }

    if (!line) {
      if (inUl) { out.push("</ul>"); inUl = false; }
      if (inOl) { out.push("</ol>"); inOl = false; }
      continue;
    }

    let safeLine = formatInline(line);

    const ulMatch = line.match(/^[-+*]\s+(.*)$/);
    const olMatch = line.match(/^\d+\.\s+(.*)$/);
    const h3 = line.match(/^###\s+(.*)$/);
    const h2 = line.match(/^##\s+(.*)$/);
    const h1 = line.match(/^#\s+(.*)$/);
    const strongOnly = safeLine.match(/^<strong>(.+)<\/strong>$/);

    if (ulMatch) {
      if (!inUl) { out.push("<ul>"); inUl = true; }
      out.push(`<li>${formatInline(ulMatch[1])}</li>`);
      continue;
    } else if (olMatch) {
      if (!inOl) { out.push("<ol>"); inOl = true; }
      out.push(`<li>${formatInline(olMatch[1])}</li>`);
      continue;
    } else if (h3) {
      out.push(`<h3>${formatInline(h3[1])}</h3>`);
      continue;
    } else if (h2) {
      out.push(`<h2>${formatInline(h2[1])}</h2>`);
      continue;
    } else if (h1) {
      out.push(`<h1>${formatInline(h1[1])}</h1>`);
      continue;
    } else if (strongOnly) {
      out.push(`<h2>${formatInline(strongOnly[1])}</h2>`);
      continue;
    }

    out.push(`<p>${safeLine}</p>`);
  }

  if (inUl) out.push("</ul>");
  if (inOl) out.push("</ol>");

  return out.join("\n");
}

export default renderPlanMarkdown;
