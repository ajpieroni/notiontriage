'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { getApiUrl } from '@/utils/api';
import { getCachedData, setCachedData, CACHE_KEYS } from '@/utils/cache';
import { ChartBarIcon, ClockIcon, ExclamationTriangleIcon, CheckCircleIcon, ArrowTrendingUpIcon, ArrowTrendingDownIcon, FireIcon } from '@heroicons/react/24/outline';

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
    Created?: {
      created_time: string;
    };
  };
}

interface ProjectGroup {
  name: string;
  tasks: Task[];
}

interface ProjectMetrics {
  totalTasks: number;
  highPriorityTasks: number;
  mediumPriorityTasks: number;
  lowPriorityTasks: number;
  overdueTasks: number;
  averageTaskAge: number;
  taskChurnRate: number;
  priorityScore: number;
  urgencyScore: number;
}

export default function ZoomPage() {
  const [projects, setProjects] = useState<ProjectGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set());

  // Memoize the fetch function
  const fetchTasks = useCallback(async () => {
    try {
      // Try to get cached data first
      const cachedData = getCachedData<Task[]>(CACHE_KEYS.ZOOM);
      if (cachedData) {
        processTasks(cachedData);
        return;
      }

      // If no cache, fetch from API
      const response = await fetch(getApiUrl('/api/tasks'));
      const tasks: Task[] = await response.json();
      
      // Cache the results
      setCachedData(CACHE_KEYS.ZOOM, tasks);
      
      // Process the tasks
      processTasks(tasks);
    } catch (error) {
      console.error('Error fetching tasks:', error);
      setLoading(false);
    }
  }, []);

  // Separate task processing logic
  const processTasks = useCallback((tasks: Task[]) => {
    // Filter and group tasks in a single pass
    const projectGroups = tasks.reduce((groups: { [key: string]: Task[] }, task) => {
      if (task.properties.Status?.status?.name === 'Done') return groups;
      
      const projectName = task.properties['Zoom Out']?.formula?.string || 'No Project';
      if (!groups[projectName]) {
        groups[projectName] = [];
      }
      groups[projectName].push(task);
      return groups;
    }, {});

    // Convert to array and sort
    const sortedProjects = Object.entries(projectGroups)
      .map(([name, tasks]) => ({
        name,
        tasks: tasks.sort((a, b) => {
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
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  // Memoize the toggle function
  const toggleProject = useCallback((projectName: string) => {
    setExpandedProjects(prev => {
      const newSet = new Set(prev);
      if (newSet.has(projectName)) {
        newSet.delete(projectName);
      } else {
        newSet.add(projectName);
      }
      return newSet;
    });
  }, []);

  // Memoize metrics calculation
  const calculateProjectMetrics = useCallback((tasks: Task[]): ProjectMetrics => {
    const now = new Date();
    
    // Single pass through tasks for all metrics
    const metrics = tasks.reduce((acc, task) => {
      // Priority counts
      if (task.properties.Priority?.status?.name === 'High') acc.highPriorityTasks++;
      else if (task.properties.Priority?.status?.name === 'Medium') acc.mediumPriorityTasks++;
      else if (task.properties.Priority?.status?.name === 'Low') acc.lowPriorityTasks++;

      // Overdue tasks
      const dueDate = task.properties.Due?.date?.start;
      if (dueDate && new Date(dueDate) < now) acc.overdueTasks++;

      // Task age
      const createdTime = new Date(task.properties.Created?.created_time || now);
      acc.totalAge += now.getTime() - createdTime.getTime();

      // Recent tasks (7 days)
      if (now.getTime() - createdTime.getTime() <= 7 * 24 * 60 * 60 * 1000) {
        acc.recentTasks++;
      }

      return acc;
    }, {
      highPriorityTasks: 0,
      mediumPriorityTasks: 0,
      lowPriorityTasks: 0,
      overdueTasks: 0,
      totalAge: 0,
      recentTasks: 0
    });

    const totalTasks = tasks.length;
    const averageTaskAge = totalTasks > 0 ? metrics.totalAge / totalTasks : 0;
    const taskChurnRate = totalTasks > 0 ? (metrics.recentTasks / totalTasks) * 100 : 0;

    const priorityScore = Math.max(0, Math.min(100,
      (metrics.highPriorityTasks * 50 + metrics.mediumPriorityTasks * 30 + metrics.lowPriorityTasks * 10) / totalTasks
    ));

    const urgencyScore = Math.max(0, Math.min(100,
      100 - (averageTaskAge > 7 * 24 * 60 * 60 * 1000 ? 30 : 0) - (metrics.overdueTasks * 20)
    ));

    return {
      totalTasks,
      highPriorityTasks: metrics.highPriorityTasks,
      mediumPriorityTasks: metrics.mediumPriorityTasks,
      lowPriorityTasks: metrics.lowPriorityTasks,
      overdueTasks: metrics.overdueTasks,
      averageTaskAge,
      taskChurnRate,
      priorityScore,
      urgencyScore
    };
  }, []);

  // Memoize color getters
  const getPriorityColor = useCallback((score: number): string => {
    if (score >= 70) return 'text-red-500';
    if (score >= 40) return 'text-yellow-500';
    return 'text-green-500';
  }, []);

  const getUrgencyColor = useCallback((score: number): string => {
    if (score >= 80) return 'text-red-500';
    if (score >= 60) return 'text-yellow-500';
    return 'text-green-500';
  }, []);

  // Memoize duration formatter
  const formatDuration = useCallback((ms: number): string => {
    const days = Math.floor(ms / (1000 * 60 * 60 * 24));
    return `${days} day${days !== 1 ? 's' : ''}`;
  }, []);

  // Memoize project metrics
  const projectMetrics = useMemo(() => 
    projects.reduce((acc, project) => {
      acc[project.name] = calculateProjectMetrics(project.tasks);
      return acc;
    }, {} as Record<string, ProjectMetrics>),
    [projects, calculateProjectMetrics]
  );

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
        {projects.map((project) => {
          const metrics = projectMetrics[project.name];
          
          return (
            <div key={project.name} className="bg-white dark:bg-gray-800 rounded-lg shadow">
              <button
                onClick={() => toggleProject(project.name)}
                className="w-full px-6 py-4 flex justify-between items-center hover:bg-gray-50 dark:hover:bg-gray-700 rounded-t-lg"
              >
                <div className="flex items-center space-x-4">
                  <h2 className="text-xl font-semibold">{project.name}</h2>
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded">
                      {metrics.totalTasks} tasks
                    </span>
                    <span className={`px-2 py-1 text-sm rounded ${getPriorityColor(metrics.priorityScore)}`}>
                      Priority: {Math.round(metrics.priorityScore)}%
                    </span>
                    <span className={`px-2 py-1 text-sm rounded ${getUrgencyColor(metrics.urgencyScore)}`}>
                      Urgency: {Math.round(metrics.urgencyScore)}%
                    </span>
                  </div>
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
                  {/* Project Health Dashboard */}
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <FireIcon className="h-5 w-5 text-red-500" />
                        <span className="font-medium">High Priority</span>
                      </div>
                      <div className="mt-2 text-2xl font-bold">
                        {metrics.highPriorityTasks}
                      </div>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <ArrowTrendingUpIcon className="h-5 w-5 text-yellow-500" />
                        <span className="font-medium">Task Churn</span>
                      </div>
                      <div className="mt-2 text-2xl font-bold">
                        {Math.round(metrics.taskChurnRate)}%
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        New tasks (7 days)
                      </div>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
                        <span className="font-medium">Overdue</span>
                      </div>
                      <div className="mt-2 text-2xl font-bold">
                        {metrics.overdueTasks}
                      </div>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <ClockIcon className="h-5 w-5 text-yellow-500" />
                        <span className="font-medium">Avg. Age</span>
                      </div>
                      <div className="mt-2 text-2xl font-bold">
                        {formatDuration(metrics.averageTaskAge)}
                      </div>
                    </div>
                  </div>

                  {/* Priority Distribution */}
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold mb-3">Priority Distribution</h3>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
                        <div className="text-red-500 font-medium">High</div>
                        <div className="text-2xl font-bold">{metrics.highPriorityTasks}</div>
                      </div>
                      <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg">
                        <div className="text-yellow-500 font-medium">Medium</div>
                        <div className="text-2xl font-bold">{metrics.mediumPriorityTasks}</div>
                      </div>
                      <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
                        <div className="text-green-500 font-medium">Low</div>
                        <div className="text-2xl font-bold">{metrics.lowPriorityTasks}</div>
                      </div>
                    </div>
                  </div>

                  {/* Tasks List */}
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
          );
        })}
      </div>
    </div>
  );
} 