// frontend/src/components/charts/RiskDistributionChart.jsx
/**
 * Risk distribution bar chart.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const SEVERITY_COLORS = {
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#22c55e",
};

export function RiskDistributionChart({ risks }) {
  // Count risks by severity
  const data = [
    {
      severity: "High",
      count: risks.filter((r) => r.severity === "high").length,
      fill: SEVERITY_COLORS.high,
    },
    {
      severity: "Medium",
      count: risks.filter((r) => r.severity === "medium").length,
      fill: SEVERITY_COLORS.medium,
    },
    {
      severity: "Low",
      count: risks.filter((r) => r.severity === "low").length,
      fill: SEVERITY_COLORS.low,
    },
  ];

  return (
    <div className="w-full h-48">
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical">
          <XAxis type="number" allowDecimals={false} />
          <YAxis type="category" dataKey="severity" width={60} />
          <Tooltip />
          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
            {data.map((entry, index) => (
              <Cell key={index} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
