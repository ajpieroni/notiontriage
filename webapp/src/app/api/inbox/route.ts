import { Client } from '@notionhq/client';
import { NextResponse } from 'next/server';

const notion = new Client({
  auth: process.env.NOTION_API_KEY,
});

export async function GET() {
  try {
    // Get tasks that need triage (no priority or status set)
    const response = await notion.databases.query({
      database_id: process.env.DATABASE_ID!,
      filter: {
        or: [
          {
            property: 'Priority',
            select: {
              is_empty: true,
            },
          },
          {
            property: 'Status',
            status: {
              is_empty: true,
            },
          },
          {
            property: 'Due',
            date: {
              is_empty: true,
            },
          },
        ],
      },
      sorts: [
        {
          timestamp: 'created_time',
          direction: 'descending',
        },
      ],
    });

    // Get tasks with high priority that need scheduling
    const highPriorityTasks = await notion.databases.query({
      database_id: process.env.DATABASE_ID!,
      filter: {
        and: [
          {
            property: 'Priority',
            select: {
              equals: 'High',
            },
          },
          {
            property: 'Status',
            status: {
              equals: 'To Do',
            },
          },
        ],
      },
      sorts: [
        {
          property: 'Due',
          direction: 'ascending',
        },
      ],
    });

    return NextResponse.json({
      needsTriage: response.results,
      highPriority: highPriorityTasks.results,
    });
  } catch (error) {
    console.error('Error fetching inbox tasks:', error);
    return NextResponse.json(
      { error: 'Failed to fetch inbox tasks' },
      { status: 500 }
    );
  }
} 