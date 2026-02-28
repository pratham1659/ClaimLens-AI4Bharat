import React, { useState, useRef, useEffect } from "react";

const CustomLeaveTypeSelect = ({ balances, value, onChange, required }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const selectedBalance = balances.find(
    (b) => b.leave_type_id === parseInt(value)
  );

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleSelect = (leaveTypeId) => {
    onChange({
      target: {
        name: "leave_type_id",
        value: leaveTypeId.toString(),
      },
    });
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Leave Type {required && <span className="text-red-500">*</span>}
      </label>

      {/* Custom Select Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full input-field text-left flex items-center justify-between hover:border-blue-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
      >
        <span className={selectedBalance ? "text-gray-900" : "text-gray-400"}>
          {selectedBalance
            ? selectedBalance.leave_type_name
            : "Select leave type"}
        </span>
        <svg
          className={`w-5 h-5 text-gray-400 transition-transform ${
            isOpen ? "transform rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-auto">
          {balances.length === 0 ? (
            <div className="px-4 py-3 text-sm text-gray-500">
              No leave types available
            </div>
          ) : (
            balances.map((balance) => {
              const isWFH = balance.leave_type_name === "Work From Home";
              const isSelected = balance.leave_type_id === parseInt(value);

              return (
                <button
                  key={balance.leave_type_id}
                  type="button"
                  onClick={() => handleSelect(balance.leave_type_id)}
                  className={`w-full text-left px-4 py-3 hover:bg-blue-50 transition-colors border-b border-gray-100 last:border-b-0 ${
                    isSelected ? "bg-blue-50 border-l-4 border-l-blue-500" : ""
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="font-medium text-gray-900 text-sm">
                        {balance.leave_type_name}
                      </div>
                      {!isWFH && (
                        <div className="mt-1 flex items-center gap-3 text-xs text-gray-600">
                          <span className="flex items-center gap-1">
                            <span className="font-medium">Total:</span>
                            <span className="text-blue-600 font-semibold">
                              {Number(balance.total_days).toFixed(1)}
                            </span>
                          </span>
                          <span className="flex items-center gap-1">
                            <span className="font-medium">Used:</span>
                            <span className="text-orange-600 font-semibold">
                              {Number(balance.used_days).toFixed(1)}
                            </span>
                          </span>
                          <span className="flex items-center gap-1">
                            <span className="font-medium">Available:</span>
                            <span className="text-green-600 font-semibold">
                              {Number(balance.remaining_days).toFixed(1)}
                            </span>
                          </span>
                        </div>
                      )}
                      {isWFH && (
                        <div className="mt-1 text-xs text-green-600 font-medium">
                          No balance required
                        </div>
                      )}
                    </div>
                    {isSelected && (
                      <svg
                        className="w-5 h-5 text-blue-600"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                  </div>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};

export default CustomLeaveTypeSelect;
