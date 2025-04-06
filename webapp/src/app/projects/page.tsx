'use client';

import { useState, useEffect } from 'react';
import { getApiUrl } from '@/utils/api';
import { ChartBarIcon, ClockIcon, ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/react/24/outline';

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
      select: {
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
  stats: {
    total: number;
    highPriority: number;
    overdue: number;
    dueToday: number;
  };
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set());

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const response = await fetch(getApiUrl('/api/tasks'));
        if (!response.ok) {
          throw new Error(`Failed to fetch tasks: ${response.status} ${response.statusText}`);
        }
        
        const { tasks } = await response.json();
        
        // Group tasks by Zoom Out formula
        const projectGroups = new Map<string, Task[]>();
        
        tasks.forEach((task: Task) => {
          const projectName = task.properties['Zoom Out']?.formula?.string || 'Uncategorized';
          if (!projectGroups.has(projectName)) {
            projectGroups.set(projectName, []);
          }
          projectGroups.get(projectName)!.push(task);
        });
        
        // Convert to array and calculate stats
        const projectArray: ProjectGroup[] = Array.from(projectGroups.entries()).map(([name, tasks]) => {
          const now = new Date();
          const stats = {
            total: tasks.length,
            highPriority: tasks.filter(t => t.properties.Priority?.select?.name === 'High').length,
            overdue: tasks.filter(t => {
              const dueDate = t.properties.Due?.date?.start;
              return dueDate && new Date(dueDate) < now;
            }).length,
            dueToday: tasks.filter(t => {
              const dueDate = t.properties.Due?.date?.start;
              return dueDate && new Date(dueDate).toDateString() === now.toDateString();
            }).length,
          };
          
          return { name, tasks, stats };
        });
        
        // Sort projects by total tasks
        projectArray.sort((a, b) => b.stats.total - a.stats.total);
        
        setProjects(projectArray);
      } catch (err) {
        console.error('Error fetching tasks:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch tasks');
      } finally {
        setLoading(false);
      }
    };

    fetchTasks();
  }, []);

  const toggleProject = (projectName: string) => {
    const newExpanded = new Set(expandedProjects);
    if (newExpanded.has(projectName)) {
      newExpanded.delete(projectName);
    } else {
      newExpanded.add(projectName);
    }
    setExpandedProjects(newExpanded);
  };

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
      <h1 className="text-3xl font-bold mb-6">Projects</h1>
      
      <div className="space-y-4">
        {projects.map((project) => (
          <div key={project.name} className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <button
              onClick={() => toggleProject(project.name)}
              className="w-full p-4 flex justify-between items-center hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg"
            >
              <div className="flex items-center space-x-4">
                <h2 className="text-xl font-semibold">{project.name}</h2>
                <div className="flex space-x-2 text-sm text-gray-500 dark:text-gray-400">
                  <span className="flex items-center">
                    <ChartBarIcon className="h-4 w-4 mr-1" />
                    {project.stats.total} tasks
                  </span>
                  {project.stats.highPriority > 0 && (
                    <span className="flex items-center text-red-500">
                      <ExclamationTriangleIcon className="h-4 w-4 mr-1" />
                      {project.stats.highPriority} high priority
                    </span>
                  )}
                  {project.stats.overdue > 0 && (
                    <span className="flex items-center text-yellow-500">
                      <ClockIcon className="h-4 w-4 mr-1" />
                      {project.stats.overdue} overdue
                    </span>
                  )}
                  {project.stats.dueToday > 0 && (
                    <span className="flex items-center text-green-500">
                      <CheckCircleIcon className="h-4 w-4 mr-1" />
                      {project.stats.dueToday} due today
                    </span>
                  )}
                </div>
              </div>
              <svg
                className={`w-5 h-5 transform transition-transform ${
                  expandedProjects.has(project.name) ? 'rotate-180' : ''
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {expandedProjects.has(project.name) && (
              <div className="p-4 border-t border-gray-200 dark:border-gray-700">
                <div className="space-y-2">
                  {project.tasks.map((task) => (
                    <div
                      key={task.id}
                      className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                    >
                      <span className="font-medium">{task.properties.Name.title[0].plain_text}</span>
                      <div className="flex items-center space-x-2 text-sm">
                        {task.properties.Priority?.select?.name && (
                          <span className={`px-2 py-1 rounded ${
                            task.properties.Priority.select.name === 'High'
                              ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100'
                              : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100'
                          }`}>
                            {task.properties.Priority.select.name}
                          </span>
                        )}
                        {task.properties.Due?.date?.start && (
                          <span className="text-gray-500 dark:text-gray-400">
                            Due: {new Date(task.properties.Due.date.start).toLocaleDateString()}
                          </span>
                        )}
                      </div>
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