import React, { useState } from 'react';
import { format } from 'date-fns';
import Input from '../common/Input';
import Button from '../common/Button';
import Alert from '../common/Alert';

const LeaveForm = ({ onSubmit, loading }) => {
  const [formData, setFormData] = useState({
    leave_type: 'casual',
    start_date: '',
    end_date: '',
    reason: '',
  });
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError('');
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    // Validation
    if (new Date(formData.start_date) < new Date().setHours(0, 0, 0, 0)) {
      setError('Start date cannot be in the past');
      return;
    }

    if (new Date(formData.end_date) < new Date(formData.start_date)) {
      setError('End date must be after start date');
      return;
    }

    if (formData.reason.trim().length < 10) {
      setError('Reason must be at least 10 characters');
      return;
    }

    onSubmit(formData);
  };

  const today = format(new Date(), 'yyyy-MM-dd');

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && <Alert type="error" message={error} onClose={() => setError('')} />}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Leave Type <span className="text-red-500">*</span>
        </label>
        <select
          name="leave_type"
          value={formData.leave_type}
          onChange={handleChange}
          className="input-field"
          required
        >
          <option value="casual">Casual Leave</option>
          <option value="sick">Sick Leave</option>
          <option value="emergency">Emergency Leave</option>
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Input
          label="Start Date"
          type="date"
          name="start_date"
          value={formData.start_date}
          onChange={handleChange}
          required
          min={today}
        />

        <Input
          label="End Date"
          type="date"
          name="end_date"
          value={formData.end_date}
          onChange={handleChange}
          required
          min={formData.start_date || today}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Reason <span className="text-red-500">*</span>
        </label>
        <textarea
          name="reason"
          value={formData.reason}
          onChange={handleChange}
          rows="4"
          className="input-field"
          placeholder="Please provide a detailed reason for your leave request..."
          required
        />
        <p className="mt-1 text-sm text-gray-500">
          Minimum 10 characters
        </p>
      </div>

      <Button type="submit" fullWidth disabled={loading}>
        {loading ? 'Submitting...' : 'Submit Leave Request'}
      </Button>
    </form>
  );
};

export default LeaveForm;
