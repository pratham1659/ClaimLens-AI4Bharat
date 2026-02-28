// frontend/src/components/common/Tooltip.jsx
/**
 * Tooltip component.
 */

import { useState } from "react";
import { clsx } from "clsx";

export function Tooltip({ children, content, position = "top" }) {
  const [isVisible, setIsVisible] = useState(false);

  const positionClasses = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
  };

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
    >
      {children}
      {isVisible && (
        <div
          className={clsx(
            "absolute z-50 px-3 py-2 text-sm text-white bg-gray-900 rounded-lg whitespace-nowrap",
            positionClasses[position],
          )}
        >
          {content}
          <div
            className={clsx(
              "absolute w-2 h-2 bg-gray-900 transform rotate-45",
              position === "top" && "top-full left-1/2 -translate-x-1/2 -mt-1",
              position === "bottom" &&
                "bottom-full left-1/2 -translate-x-1/2 -mb-1",
              position === "left" && "left-full top-1/2 -translate-y-1/2 -ml-1",
              position === "right" &&
                "right-full top-1/2 -translate-y-1/2 -mr-1",
            )}
          />
        </div>
      )}
    </div>
  );
}
