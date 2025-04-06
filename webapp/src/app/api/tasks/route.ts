import { Client } from '@notionhq/client';
import { NextResponse } from 'next/server';

const notion = new Client({
  auth: process.env.NOTION_API_KEY,
});

export async function GET(request: Request) {
  try {
    let allResults: any[] = [];
    let hasMore = true;
    let startCursor: string | undefined;

    while (hasMore) {
      const response = await notion.databases.query({
        database_id: process.env.DATABASE_ID!,
        filter: {
          property: 'Done',
          checkbox: {
            equals: false,
          },
        },
        sorts: [
          {
            timestamp: 'created_time',
            direction: 'ascending',
          },
        ],
        page_size: 100,
        start_cursor: startCursor,
      });

      allResults = [...allResults, ...response.results];
      hasMore = response.has_more;
      startCursor = response.next_cursor || undefined;
    }

    return NextResponse.json({
      count: allResults.length,
      tasks: allResults
    });
  } catch (error) {
    console.error('Error fetching tasks:', error);
    return NextResponse.json({ error: 'Failed to fetch tasks' }, { status: 500 });
  }
} 