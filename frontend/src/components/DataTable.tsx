import { tokens } from "../theme";

interface DataTableProps {
  columns: string[];
  rows: unknown[][];
  maxRows?: number;
  totalRows?: number;
  caption?: string;
}

/** Reusable data table component used across Chat, Insights, and Notebook pages. */
export default function DataTable({ columns, rows, maxRows = 50, totalRows, caption }: DataTableProps) {
  const displayRows = rows.slice(0, maxRows);
  const count = totalRows ?? rows.length;

  return (
    <div style={{ marginTop: tokens.spacing.md }}>
      {(caption || count > 0) && (
        <div style={{ fontSize: tokens.fontSize.sm, color: tokens.color.text.tertiary, marginBottom: 6 }}>
          {caption || `Results (${displayRows.length} of ${count} rows)`}
        </div>
      )}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: tokens.fontSize.sm }}>
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col}
                  style={{
                    padding: `4px ${tokens.spacing.sm}px`,
                    borderBottom: `1px solid ${tokens.color.border.default}`,
                    textAlign: "left",
                    color: tokens.color.text.tertiary,
                    fontWeight: 500,
                  }}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, ri) => (
              <tr key={ri}>
                {row.map((val, ci) => (
                  <td
                    key={ci}
                    style={{
                      padding: `3px ${tokens.spacing.sm}px`,
                      borderBottom: `0.5px solid ${tokens.color.border.light}`,
                      color: tokens.color.text.secondary,
                    }}
                  >
                    {String(val)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
