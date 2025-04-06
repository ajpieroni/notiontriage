'use client';

import { useState, useEffect } from 'react';
import { getApiUrl } from '@/utils/api';

interface Task {
  id: string;
  properties: {
    Name: {
      title: [{ plain_text: string }];
    };
    'Zoom Out': {
      formula: {
        string: string;
      };
    };
    Status: {
      status: {
        name: string;
      };
    };
    Priority: {
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

interface ProjectGroup {
  name: string;
  tasks: Task[];
}

export default function ZoomPage() {
  const [projects, setProjects] = useState<ProjectGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await fetch(getApiUrl('/api/tasks'));
      const tasks: Task[] = await response.json();
      
      // Filter out completed tasks and group by Zoom Out formula
      const projectGroups = tasks
        .filter(task => task.properties.Status?.status?.name !== 'Done')
        .reduce((groups: { [key: string]: Task[] }, task) => {
          const projectName = task.properties['Zoom Out']?.formula?.string || 'No Project';
          if (!groups[projectName]) {
            groups[projectName] = [];
          }
          groups[projectName].push(task);
          return groups;
        }, {});

      // Convert to array and sort by project name
      const sortedProjects = Object.entries(projectGroups)
        .map(([name, tasks]) => ({
          name,
          tasks: tasks.sort((a, b) => {
            // Sort by due date, then by priority
            const dateA = a.properties.Due?.date?.start;
            const dateB = b.properties.Due?.date?.start;
            if (dateA && dateB) {
              return new Date(dateA).getTime() - new Date(dateB).getTime();
            }
            return 0;
          }),
        }))
        .sort((a, b) => a.name.localeCompare(b.name));

      setProjects(sortedProjects);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching tasks:', error);
      setLoading(false);
    }
  };

  const toggleProject = (projectName: string) => {
    setExpandedProjects(prev => {
      const newSet = new Set(prev);
      if (newSet.has(projectName)) {
        newSet.delete(projectName);
      } else {
        newSet.add(projectName);
      }
      return newSet;
    });
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Project Overview</h1>
      
      <div className="space-y-6">
        {projects.map((project) => (
          <div key={project.name} className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <button
              onClick={() => toggleProject(project.name)}
              className="w-full px-6 py-4 flex justify-between items-center hover:bg-gray-50 dark:hover:bg-gray-700 rounded-t-lg"
            >
              <div className="flex items-center space-x-4">
                <h2 className="text-xl font-semibold">{project.name}</h2>
                <span className="px-2 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded">
                  {project.tasks.length} tasks
                </span>
              </div>
              <svg
                className={`w-5 h-5 transform transition-transform ${
                  expandedProjects.has(project.name) ? 'rotate-180' : ''
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

            {expandedProjects.has(project.name) && (
              <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
                <div className="space-y-4">
                  {project.tasks.map((task) => (
                    <div
                      key={task.id}
                      className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
                    >
                      <div>
                        <h3 className="font-medium">
                          {task.properties.Name.title[0].plain_text}
                        </h3>
                        <div className="flex items-center space-x-4 mt-1 text-sm text-gray-500 dark:text-gray-400">
                          {task.properties.Status?.status?.name && (
                            <span>Status: {task.properties.Status.status.name}</span>
                          )}
                          {task.properties.Priority?.status?.name && (
                            <span>Priority: {task.properties.Priority.status.name}</span>
                          )}
                          {task.properties.Due?.date?.start && (
                            <span>
                              Due: {new Date(task.properties.Due.date.start).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => window.location.href = `/focus?task=${task.id}`}
                        className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                      >
                        Focus
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
} 