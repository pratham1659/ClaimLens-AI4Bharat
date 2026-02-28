import React from "react";
import { useNavigate } from "react-router-dom";

/**
 * QuickActionButton Component
 * Gradient action button with icon - ALMS-style design
 */
const QuickActionButton = ({
  title,
  description,
  icon: Icon,
  to,
  onClick,
  gradient = "blue",
}) => {
  const navigate = useNavigate();

  const gradientClasses = {
    blue: "bg-gradient-to-br from-blue-400 to-sky-500 hover:from-blue-500 hover:to-sky-600",
    teal: "bg-gradient-to-br from-teal-400 to-cyan-500 hover:from-teal-500 hover:to-cyan-600",
    purple:
      "bg-gradient-to-br from-indigo-400 to-purple-500 hover:from-indigo-500 hover:to-purple-600",
    orange:
      "bg-gradient-to-br from-orange-400 to-amber-500 hover:from-orange-500 hover:to-amber-600",
    green:
      "bg-gradient-to-br from-emerald-400 to-teal-500 hover:from-emerald-500 hover:to-teal-600",
    pink: "bg-gradient-to-br from-pink-400 to-rose-500 hover:from-pink-500 hover:to-rose-600",
  };

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else if (to) {
      navigate(to);
    }
  };

  return (
    <button
      onClick={handleClick}
      className={`group ${gradientClasses[gradient] || gradientClasses.blue} text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-200 transform hover:-translate-y-1 w-full text-left`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="p-3 bg-white bg-opacity-20 rounded-lg">{Icon}</div>
        <svg
          className="w-5 h-5 transform group-hover:translate-x-1 transition-transform"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 7l5 5m0 0l-5 5m5-5H6"
          />
        </svg>
      </div>
      <h3 className="text-lg font-semibold mb-1">{title}</h3>
      <p className="text-sm opacity-90">{description}</p>
    </button>
  );
};

export default QuickActionButton;
