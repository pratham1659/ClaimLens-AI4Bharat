// frontend/src/components/charts/ApprovalScoreChart.jsx
/**
 * Approval score visualization chart.
 */

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";

const COLORS = {
  high: "#22c55e",
  medium: "#f59e0b",
  low: "#ef4444",
  very_low: "#991b1b",
};

export function ApprovalScoreChart({ score, likelihood }) {
  const data = [
    { name: "Score", value: score },
    { name: "Remaining", value: 100 - score },
  ];

  const color = COLORS[likelihood] || COLORS.medium;

  return (
    <div className="w-full h-48">
      <ResponsiveContainer>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={70}
            startAngle={90}
            endAngle={-270}
            dataKey="value"
          >
            <Cell fill={color} />
            <Cell fill="#e5e7eb" />
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="text-center -mt-24">
        <span className="text-3xl font-bold" style={{ color }}>
          {Math.round(score)}%
        </span>
        <p className="text-sm text-gray-500 mt-1">Approval Score</p>
      </div>
    </div>
  );
}
