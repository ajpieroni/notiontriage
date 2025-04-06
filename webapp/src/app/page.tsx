import Link from 'next/link'

async function getTasks() {
  try {
    const res = await fetch(`${process.env.VERCEL_URL || 'http://localhost:3000'}/api/tasks`, {
      cache: 'no-store'
    });
    if (!res.ok) throw new Error('Failed to fetch tasks');
    return res.json();
  } catch (error) {
    console.error('Error:', error);
    return [];
  }
}

export default async function Home() {
  const tasks = await getTasks();

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm">
        <h1 className="text-4xl font-bold mb-8 text-center">Notion Triage</h1>
        <p className="text-xl mb-8 text-center">
          Task management and scheduling system with Notion and Google Calendar integration
        </p>
        
        <div className="mb-12">
          <h2 className="text-2xl font-semibold mb-4">Recent Tasks</h2>
          <div className="bg-white shadow rounded-lg p-6">
            {tasks.length > 0 ? (
              <ul className="space-y-4">
                {tasks.slice(0, 5).map((task: any) => (
                  <li key={task.id} className="border-b pb-2">
                    <span className="font-medium">{task.properties.Name?.title[0]?.plain_text || 'Untitled'}</span>
                    {task.properties.Due?.date && (
                      <span className="text-gray-500 text-sm ml-2">
                        Due: {new Date(task.properties.Due.date.start).toLocaleDateString()}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500">No tasks found</p>
            )}
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8">
          <Link
            href="/focus"
            className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100"
          >
            <h2 className="mb-3 text-2xl font-semibold">
              Focus Mode{' '}
              <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
                →
              </span>
            </h2>
            <p className="m-0 max-w-[30ch] text-sm opacity-50">
              Enter distraction-free mode with Pomodoro timer
            </p>
          </Link>

          <Link
            href="/inbox"
            className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100"
          >
            <h2 className="mb-3 text-2xl font-semibold">
              Inbox{' '}
              <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
                →
              </span>
            </h2>
            <p className="m-0 max-w-[30ch] text-sm opacity-50">
              View and triage new tasks
            </p>
          </Link>

          <Link
            href="/tasks"
            className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100"
          >
            <h2 className="mb-3 text-2xl font-semibold">
              Tasks{' '}
              <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
                →
              </span>
            </h2>
            <p className="m-0 max-w-[30ch] text-sm opacity-50">
              View and manage your tasks from Notion
            </p>
          </Link>

          <Link
            href="/calendar"
            className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100"
          >
            <h2 className="mb-3 text-2xl font-semibold">
              Calendar{' '}
              <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
                →
              </span>
            </h2>
            <p className="m-0 max-w-[30ch] text-sm opacity-50">
              View and manage your Google Calendar events
            </p>
          </Link>

          <Link
            href="/schedule"
            className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100"
          >
            <h2 className="mb-3 text-2xl font-semibold">
              Schedule{' '}
              <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
                →
              </span>
            </h2>
            <p className="m-0 max-w-[30ch] text-sm opacity-50">
              Optimize your task schedule
            </p>
          </Link>

          <Link
            href="/settings"
            className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100"
          >
            <h2 className="mb-3 text-2xl font-semibold">
              Settings{' '}
              <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
                →
              </span>
            </h2>
            <p className="m-0 max-w-[30ch] text-sm opacity-50">
              Configure your Notion and Google Calendar integration
            </p>
          </Link>
        </div>
      </div>
    </div>
  )
} 