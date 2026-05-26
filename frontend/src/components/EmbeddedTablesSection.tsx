import React from "react";

import { listSheetTables, type DrawingTableRecord, type TableKind } from "../api/tables";

const MAX_ROWS_BEFORE_TRUNCATE = 30;

const TABLE_KIND_LABELS: Record<TableKind, string> = {
  equipment: "设备表",
  material: "材料表",
  drawing_index: "图纸目录",
  legend: "图例",
  other: "其他"
};

const METHOD_LABELS: Record<string, string> = {
  acad_table: "ACAD 表格",
  text_cluster: "文字聚类"
};

type Props = {
  sheetId: number | null | undefined;
};

function buildCsv(header: string[], rows: string[][]): string {
  const lines: string[] = [];
  const escape = (cell: string): string => {
    if (cell.includes(",") || cell.includes("\"") || cell.includes("\n")) {
      return `"${cell.replace(/"/g, '""')}"`;
    }
    return cell;
  };
  lines.push(header.map(escape).join(","));
  for (const row of rows) {
    lines.push(row.map(escape).join(","));
  }
  return lines.join("\n");
}

function groupByKind(records: DrawingTableRecord[]): Map<TableKind, DrawingTableRecord[]> {
  const groups = new Map<TableKind, DrawingTableRecord[]>();
  for (const record of records) {
    const existing = groups.get(record.table_kind) ?? [];
    existing.push(record);
    groups.set(record.table_kind, existing);
  }
  return groups;
}

export function EmbeddedTablesSection({ sheetId }: Props): React.ReactElement | null {
  const [records, setRecords] = React.useState<DrawingTableRecord[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [copiedId, setCopiedId] = React.useState<number | null>(null);

  React.useEffect(() => {
    if (!sheetId) {
      setRecords([]);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    listSheetTables(sheetId)
      .then((items) => setRecords(items))
      .catch((exc: Error) => setError(exc.message || "加载失败"))
      .finally(() => setLoading(false));
  }, [sheetId]);

  if (!sheetId) {
    return null;
  }

  const handleCopyCsv = async (record: DrawingTableRecord): Promise<void> => {
    const csv = buildCsv(record.header, record.rows);
    try {
      await navigator.clipboard.writeText(csv);
      setCopiedId(record.id);
      window.setTimeout(() => setCopiedId(null), 1500);
    } catch {
      setError("复制失败：浏览器禁止剪贴板访问。");
    }
  };

  const groups = groupByKind(records);

  return (
    <div className="sheet-list embedded-tables-section">
      <div className="section-title">
        <h3>图纸内嵌表格</h3>
        <span>{loading ? "加载中…" : `${records.length} 张表`}</span>
      </div>
      {error ? <p className="error-message">{error}</p> : null}
      {!loading && records.length === 0 && !error ? (
        <p className="empty-state">未在该图纸抽取到表格。可先执行「抽取表格」。</p>
      ) : null}
      {[...groups.entries()].map(([kind, items]) => (
        <div className="embedded-table-kind-group" key={kind}>
          <h4>
            {TABLE_KIND_LABELS[kind] ?? kind}
            <span className="muted"> · {items.length} 张</span>
          </h4>
          {items.map((record) => {
            const visibleRows = record.rows.slice(0, MAX_ROWS_BEFORE_TRUNCATE);
            const remaining = Math.max(record.row_count - visibleRows.length, 0);
            return (
              <article className="embedded-table-card" key={record.id}>
                <header className="embedded-table-header">
                  <div>
                    <strong>表 #{record.table_index}</strong>
                    <span className="muted">
                      {METHOD_LABELS[record.extraction_method] ?? record.extraction_method}
                      {record.layer_name ? ` · ${record.layer_name}` : ""}
                      {` · ${record.row_count} 行 × ${record.col_count} 列`}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => handleCopyCsv(record)}
                  >
                    {copiedId === record.id ? "已复制 ✓" : "复制 CSV"}
                  </button>
                </header>
                <div className="embedded-table-scroll">
                  <table className="embedded-table">
                    <thead>
                      <tr>
                        {record.header.map((cell, idx) => (
                          <th key={idx}>{cell}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {visibleRows.map((row, rIdx) => (
                        <tr key={rIdx}>
                          {row.map((cell, cIdx) => (
                            <td key={cIdx}>{cell}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {remaining > 0 ? (
                  <p className="muted small">+ {remaining} 行（已截断）</p>
                ) : null}
                {record.warnings.length > 0 ? (
                  <p className="muted small">提示：{record.warnings.join(" / ")}</p>
                ) : null}
              </article>
            );
          })}
        </div>
      ))}
    </div>
  );
}
