'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { getApiUrl } from '@/utils/api';
import { getCachedData, setCachedData, CACHE_KEYS } from '@/utils/cache';

interface Task {
  id: string;
  properties: {
    Name: {
      title: [{ plain_text: string }];
    };
    Priority: {
      select: {
        name: string;
      };
    };
    Status: {
      status: {
        name: string;
      };
    };
    Due: {
      date: {
        start: string;
      };
    };
  };
}

function TaskCard({ task }: { task: Task }) {
  const title = task.properties.Name?.title[0]?.plain_text || 'Untitled';
  const priority = task.properties.Priority?.select?.name || 'Not Set';
  const status = task.properties.Status?.status?.name || 'Not Set';
  const dueDate = task.properties.Due?.date?.start;

  return (
    <div className="bg-white shadow rounded-lg p-4 mb-4">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-semibold">{title}</h3>
          <div className="flex gap-4 mt-2 text-sm text-gray-600">
            <span>Priority: {priority}</span>
            <span>Status: {status}</span>
            {dueDate && (
              <span>Due: {new Date(dueDate).toLocaleDateString()}</span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <Link
            href={`/tasks/${task.id}/edit`}
            className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Edit
          </Link>
          <Link
            href={`/schedule/${task.id}`}
            className="px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600"
          >
            Schedule
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function InboxPage() {
  const [needsTriage, setNeedsTriage] = useState<Task[]>([]);
  const [highPriority, setHighPriority] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchInboxTasks = async () => {
      try {
        // Try to get cached data first
        const cachedData = getCachedData<{ needsTriage: Task[]; highPriority: Task[] }>(CACHE_KEYS.INBOX);
        if (cachedData) {
          setNeedsTriage(cachedData.needsTriage);
          setHighPriority(cachedData.highPriority);
          setLoading(false);
          return;
        }

        // If no cache, fetch from API
        const response = await fetch(getApiUrl('/api/inbox'));
        if (!response.ok) {
          throw new Error(`Failed to fetch inbox tasks: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        
        // Cache the results
        setCachedData(CACHE_KEYS.INBOX, data);
        
        setNeedsTriage(data.needsTriage || []);
        setHighPriority(data.highPriority || []);
      } catch (err) {
        console.error('Error fetching inbox tasks:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch inbox tasks');
      } finally {
        setLoading(false);
      }
    };

    fetchInboxTasks();
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
      <h1 className="text-3xl font-bold mb-8">Inbox</h1>
      
      <div className="mb-12">
        <h2 className="text-2xl font-semibold mb-4">Needs Triage</h2>
        <div className="space-y-4">
          {needsTriage.length > 0 ? (
            needsTriage.map((task) => (
              <TaskCard key={task.id} task={task} />
            ))
          ) : (
            <p className="text-gray-500">No tasks need triage</p>
          )}
        </div>
      </div>

      <div>
        <h2 className="text-2xl font-semibold mb-4">High Priority Tasks</h2>
        <div className="space-y-4">
          {highPriority.length > 0 ? (
            highPriority.map((task) => (
              <TaskCard key={task.id} task={task} />
            ))
          ) : (
            <p className="text-gray-500">No high priority tasks</p>
          )}
        </div>
      </div>
    </div>
  );
} 