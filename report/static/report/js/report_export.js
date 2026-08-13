/**
 * Shared report export helpers for PivotTable explorer pages.
 * Templates can replace duplicated exportTableToExcel / CSV / PDF logic
 * by loading this script and calling HorillaReportExport.exportTable(...).
 *
 * Usage (theme report templates):
 *   <script src="{% static 'report/js/report_export.js' %}"></script>
 *   HorillaReportExport.exportTable(tableEl, { format: 'xlsx', filename: 'report.xlsx' });
 */
(function (global) {
  "use strict";

  function downloadBlob(blob, filename) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 1000);
  }

  function tableToMatrix(table) {
    var rows = [];
    table.querySelectorAll("tr").forEach(function (tr) {
      var row = [];
      tr.querySelectorAll("th,td").forEach(function (cell) {
        row.push((cell.innerText || "").trim());
      });
      if (row.length) rows.push(row);
    });
    return rows;
  }

  function exportCsv(table, filename) {
    var matrix = tableToMatrix(table);
    var csv = matrix
      .map(function (row) {
        return row
          .map(function (v) {
            var s = String(v).replace(/"/g, '""');
            return '"' + s + '"';
          })
          .join(",");
      })
      .join("\n");
    downloadBlob(new Blob([csv], { type: "text/csv;charset=utf-8;" }), filename || "report.csv");
  }

  function exportXlsx(table, filename) {
    // Prefer SheetJS / ExcelJS if already loaded by the page.
    var matrix = tableToMatrix(table);
    if (global.ExcelJS && global.ExcelJS.Workbook) {
      var wb = new global.ExcelJS.Workbook();
      var ws = wb.addWorksheet("Report");
      matrix.forEach(function (row) {
        ws.addRow(row);
      });
      wb.xlsx.writeBuffer().then(function (buffer) {
        downloadBlob(
          new Blob([buffer], {
            type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          }),
          filename || "report.xlsx"
        );
      });
      return;
    }
    if (global.XLSX) {
      var sheet = global.XLSX.utils.aoa_to_sheet(matrix);
      var book = global.XLSX.utils.book_new();
      global.XLSX.utils.book_append_sheet(book, sheet, "Report");
      global.XLSX.writeFile(book, filename || "report.xlsx");
      return;
    }
    // Fallback to CSV when no spreadsheet library is present.
    exportCsv(table, (filename || "report.xlsx").replace(/\.xlsx$/i, ".csv"));
  }

  function exportTable(table, options) {
    options = options || {};
    var format = (options.format || "xlsx").toLowerCase();
    if (format === "csv") {
      exportCsv(table, options.filename || "report.csv");
    } else {
      exportXlsx(table, options.filename || "report.xlsx");
    }
  }

  global.HorillaReportExport = {
    exportTable: exportTable,
    exportCsv: exportCsv,
    exportXlsx: exportXlsx,
    tableToMatrix: tableToMatrix,
  };
})(window);
