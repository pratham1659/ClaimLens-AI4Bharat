import React from "react";
import Spinner from "./Spinner";

const Table = ({
  columns,
  data,
  loading = false,
  emptyMessage = "No data available",
}) => {
  if (loading) {
    return (
      <div className="py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 table-fixed">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((column, index) => (
              <th
                key={index}
                className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${
                  column.width || ""
                }`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {data.map((row, rowIndex) => (
            <tr key={rowIndex} className="hover:bg-gray-50">
              {columns.map((column, colIndex) => (
                <td
                  key={colIndex}
                  className={`px-4 py-4 text-sm text-gray-900 align-top ${
                    column.width || ""
                  }`}
                >
                  {column.render ? column.render(row) : row[column.accessor]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default Table;
