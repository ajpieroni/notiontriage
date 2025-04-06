import { Client } from '@notionhq/client';
import { NextResponse } from 'next/server';

const notion = new Client({
  auth: process.env.NOTION_API_KEY,
});

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const assignedTimeEquals = url.searchParams.get('assigned_time_equals') === 'true';
    const targetDate = url.searchParams.get('target_date') || new Date().toISOString().split('T')[0];

    const response = await notion.databases.query({
      database_id: process.env.DATABASE_ID!,
      filter: {
        and: [
          {
            property: 'Due',
            date: {
              on_or_before: targetDate,
            },
          },
          {
            property: 'Assigned time',
            checkbox: {
              equals: assignedTimeEquals,
            },
          },
          {
            property: 'Done',
            checkbox: {
              equals: false,
            },
          },
          {
            property: 'Priority',
            status: {
              does_not_equal: 'Someday',
            },
          },
          {
            property: 'Priority',
            status: {
              does_not_equal: 'Unassigned',
            },
          },
        ],
      },
      sorts: [
        {
          timestamp: 'created_time',
          direction: 'ascending',
        },
      ],
    });

    return NextResponse.json(response.results);
  } catch (error) {
    console.error('Error fetching tasks:', error);
    return NextResponse.json({ error: 'Failed to fetch tasks' }, { status: 500 });
  }
} 