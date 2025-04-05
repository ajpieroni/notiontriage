import { Suspense } from 'react';
import Link from 'next/link';

async function getInboxTasks() {
  const res = await fetch(`${process.env.VERCEL_URL || 'http://localhost:3002'}/api/inbox`, {
    cache: 'no-store'
  });
  if (!res.ok) throw new Error('Failed to fetch inbox tasks');
  return res.json();
}

function TaskCard({ task }: { task: any }) {
  const title = task.properties.Name?.title[0]?.plain_text || 'Untitled';
  const priority = task.properties.Priority?.select?.name || 'Not Set';
  const status = task.properties.Status?.select?.name || 'Not Set';
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

function InboxContent() {
  const { needsTriage, highPriority } = getInboxTasks();

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8">Inbox</h1>
      
      <div className="mb-12">
        <h2 className="text-2xl font-semibold mb-4">Needs Triage</h2>
        <div className="space-y-4">
          {needsTriage.length > 0 ? (
            needsTriage.map((task: any) => (
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
            highPriority.map((task: any) => (
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

export default function InboxPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <InboxContent />
    </Suspense>
  );
} 