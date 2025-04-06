import Link from 'next/link'
import { getApiUrl } from '@/utils/api'

async function getTasks() {
  try {
    const res = await fetch(getApiUrl('/api/tasks'), {
      cache: 'no-store'
    });
    if (!res.ok) throw new Error('Failed to fetch tasks');
    return res.json();
  } catch (error) {
    console.error('Error:', error);
    return [];
  }
}

export default function Home() {
  const features = [
    {
      name: 'Tasks',
      description: 'View and manage your tasks from Notion',
      href: '/tasks',
    },
    {
      name: 'Inbox',
      description: 'Process your incoming tasks and ideas',
      href: '/inbox',
    },
    {
      name: 'Focus',
      description: 'Focus on your most important tasks',
      href: '/focus',
    },
    {
      name: 'Zoom',
      description: 'Schedule and manage Zoom meetings',
      href: '/zoom',
    },
  ];

  return (
    <div className="bg-white dark:bg-gray-900">
      <div className="mx-auto max-w-7xl px-6 py-24 sm:py-32 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-4xl">
            Welcome to Notion Triage
          </h2>
          <p className="mt-6 text-lg leading-8 text-gray-600 dark:text-gray-300">
            A task management and scheduling system that integrates with Notion and Google Calendar
          </p>
        </div>
        <div className="mx-auto mt-16 max-w-2xl sm:mt-20 lg:mt-24 lg:max-w-none">
          <dl className="grid max-w-xl grid-cols-1 gap-x-8 gap-y-16 lg:max-w-none lg:grid-cols-4">
            {features.map((feature) => (
              <div key={feature.name} className="flex flex-col">
                <Link
                  href={feature.href}
                  className="relative flex flex-col rounded-2xl bg-gray-50 dark:bg-gray-800 p-8 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <dt className="text-base font-semibold leading-7 text-gray-900 dark:text-white">
                    {feature.name}
                  </dt>
                  <dd className="mt-1 flex flex-auto flex-col text-base leading-7 text-gray-600 dark:text-gray-300">
                    <p className="flex-auto">{feature.description}</p>
                  </dd>
                </Link>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </div>
  )
} 