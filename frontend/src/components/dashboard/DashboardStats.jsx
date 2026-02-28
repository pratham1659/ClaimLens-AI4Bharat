import React, { useEffect, useState } from 'react';
import { leavesAPI } from '../../api/leaves';
import { usersAPI } from '../../api/users';
import StatCard from './StatCard';
import LoadingSpinner from '../common/LoadingSpinner';
import { useAuth } from '../../hooks/useAuth';

const DashboardStats = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const { isAdmin } = useAuth();

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      if (isAdmin) {
        const leaveStats = await leavesAPI.getStatistics();
        setStats(leaveStats.statistics);
      } else {
        const myLeaves = await leavesAPI.getMyLeaves();
        const pending = myLeaves.filter(l => l.status === 'pending').length;
        const approved = myLeaves.filter(l => l.status === 'approved').length;
        const rejected = myLeaves.filter(l => l.status === 'rejected').length;
        
        setStats({
          total: myLeaves.length,
          by_status: { pending, approved, rejected }
        });
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!stats) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <StatCard
        title="Total Leaves"
        value={stats.total}
        icon="📊"
        color="primary"
      />
      <StatCard
        title="Pending"
        value={stats.by_status.pending}
        icon="⏳"
        color="warning"
      />
      <StatCard
        title="Approved"
        value={stats.by_status.approved}
        icon="✅"
        color="success"
      />
      <StatCard
        title="Rejected"
        value={stats.by_status.rejected}
        icon="❌"
        color="danger"
      />
    </div>
  );
};

export default DashboardStats;
