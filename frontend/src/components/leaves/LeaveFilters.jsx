import React from 'react';

const LeaveFilters = ({ filters, onFilterChange }) => {
  return (
    <div className="card mb-6">
      <h3 className="text-lg font-semibold mb-4">Filters</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Status
          </label>
          <select
            value={filters.status || ''}
            onChange={(e) => onFilterChange('status', e.target.value)}
            className="input-field"
          >
            <option value="">All Status</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Leave Type
          </label>
          <select
            value={filters.leave_type || ''}
            onChange={(e) => onFilterChange('leave_type', e.target.value)}
            className="input-field"
          >
            <option value="">All Types</option>
            <option value="casual">Casual</option>
            <option value="sick">Sick</option>
            <option value="emergency">Emergency</option>
          </select>
        </div>

        <div className="flex items-end">
          <button
            onClick={() => onFilterChange('reset')}
            className="btn-secondary w-full"
          >
            Reset Filters
          </button>
        </div>
      </div>
    </div>
  );
};

export default LeaveFilters;
