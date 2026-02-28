import React from 'react';
import LeaveCard from './LeaveCard';
import LoadingSpinner from '../common/LoadingSpinner';

const LeaveList = ({ leaves, loading, onUpdate, onDelete, emptyMessage = 'No leave requests found' }) => {
  if (loading) {
    return <LoadingSpinner message="Loading leaves..." />;
  }

  if (!leaves || leaves.length === 0) {
    return (
      <div className="card text-center py-12">
        <span className="text-6xl mb-4 block">📭</span>
        <p className="text-gray-600 text-lg">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {leaves.map((leave) => (
        <LeaveCard
          key={leave.id}
          leave={leave}
          onUpdate={onUpdate}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
};

export default LeaveList;
