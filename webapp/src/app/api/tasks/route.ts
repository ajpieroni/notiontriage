import { Client } from '@notionhq/client';
import { NextResponse } from 'next/server';

const notion = new Client({
  auth: process.env.NOTION_API_KEY,
});

export async function GET() {
  try {
    const response = await notion.databases.query({
      database_id: process.env.DATABASE_ID!,
      sorts: [
        {
          property: 'Due',
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