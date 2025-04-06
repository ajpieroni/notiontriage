'use client';

import { useState, useEffect } from 'react';
import { getApiUrl } from '@/utils/api';

interface FocusTaskProps {
  currentTask: any;
  setCurrentTask: (task: any) => void;
}

export default function FocusTask({ currentTask, setCurrentTask }: FocusTaskProps) {
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await fetch(getApiUrl('/api/tasks?assigned_time_equals=false'));
      const data = await response.json();
      setTasks(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching tasks:', error);
      setLoading(false);
    }
  };

  const completeTask = async () => {
    if (!currentTask) return;

    try {
      const response = await fetch(getApiUrl(`/api/tasks/${currentTask.id}?action=complete`), {
        method: 'POST',
      });

      if (response.ok) {
        // Update the task in the local state
        setTasks(tasks.filter(task => task.id !== currentTask.id));
        setCurrentTask(null);
      }
    } catch (error) {
      console.error('Error completing task:', error);
    }
  };

  if (loading) {
    return <div className="text-center">Loading tasks...</div>;
  }

  return (
    <div>
      {currentTask ? (
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold">
            {currentTask.properties.Name?.title[0]?.plain_text || 'Untitled'}
          </h2>
          
          {currentTask.properties.Description?.rich_text?.[0]?.plain_text && (
            <p className="text-gray-600">
              {currentTask.properties.Description.rich_text[0].plain_text}
            </p>
          )}

          <div className="flex gap-2 text-sm text-gray-500">
            {currentTask.properties.Priority?.select?.name && (
              <span>Priority: {currentTask.properties.Priority.select.name}</span>
            )}
            {currentTask.properties.Due?.date?.start && (
              <span>
                Due: {new Date(currentTask.properties.Due.date.start).toLocaleDateString()}
              </span>
            )}
          </div>

          <div className="mt-6">
            <button
              onClick={completeTask}
              className="w-full px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
            >
              Mark as Complete
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Select a Task to Focus On</h2>
          <div className="space-y-2">
            {tasks.map((task) => (
              <button
                key={task.id}
                onClick={() => setCurrentTask(task)}
                className="w-full text-left p-4 bg-gray-50 rounded-lg hover:bg-gray-100"
              >
                <div className="font-medium">
                  {task.properties.Name?.title[0]?.plain_text || 'Untitled'}
                </div>
                {task.properties.Due?.date?.start && (
                  <div className="text-sm text-gray-500">
                    Due: {new Date(task.properties.Due.date.start).toLocaleDateString()}
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
} 