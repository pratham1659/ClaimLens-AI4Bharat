import React from "react";
import { useNavigate } from "react-router-dom";

/**
 * StatsCard Component
 * Minimal design - just icon and stats, no colors
 */
const StatsCard = ({
  icon: Icon,
  label,
  value,
  subtitle = null,
  link = null,
}) => {
  const navigate = useNavigate();

  // Ensure value is always a valid display value
  const displayValue = value !== undefined && value !== null ? value : 0;

  const handleClick = () => {
    if (link) {
      navigate(link);
    }
  };

  return (
    <div
      className={`bg-white border border-gray-200 rounded-lg p-5 ${
        link ? "cursor-pointer hover:bg-gray-50" : ""
      } transition-colors`}
      onClick={link ? handleClick : undefined}
    >
      <div className="flex items-center space-x-4">
        {Icon && (
          <div className="p-2 bg-gray-100 rounded-lg">
            <Icon className="w-6 h-6 text-gray-600" />
          </div>
        )}
        <div className="flex-1">
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-semibold text-gray-900 mt-1">
            {displayValue}
          </p>
          {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
        </div>
      </div>
    </div>
  );
};

export default StatsCard;
