'use client';

import { useState, useEffect } from 'react';
import { getApiUrl } from '@/utils/api';

interface TaskCount {
  count: number;
  tasks: any[];
}

export default function TaskCountPage() {
  const [taskCount, setTaskCount] = useState<TaskCount | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTaskCount = async () => {
      try {
        const response = await fetch(getApiUrl('/api/tasks'));
        if (!response.ok) {
          throw new Error(`Failed to fetch tasks: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        setTaskCount(data);
      } catch (err) {
        console.error('Error fetching task count:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch task count');
      } finally {
        setLoading(false);
      }
    };

    fetchTaskCount();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          <p>Error: {error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Task Count</h1>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <p className="text-2xl">
          You have <span className="font-bold">{taskCount?.count || 0}</span> incomplete tasks
        </p>
      </div>
    </div>
  );
} 