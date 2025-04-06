import { Client } from '@notionhq/client';
import { NextResponse } from 'next/server';

const notion = new Client({
  auth: process.env.NOTION_API_KEY,
});

export async function POST(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const taskId = params.id;
    const url = new URL(request.url);
    const action = url.searchParams.get('action') || 'complete';

    switch (action) {
      case 'complete':
        await notion.pages.update({
          page_id: taskId,
          properties: {
            Done: {
              checkbox: true,
            },
          },
        });
        break;
      case 'assign':
        await notion.pages.update({
          page_id: taskId,
          properties: {
            'Assigned time': {
              checkbox: true,
            },
          },
        });
        break;
      default:
        return NextResponse.json(
          { error: 'Invalid action' },
          { status: 400 }
        );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error updating task:', error);
    return NextResponse.json(
      { error: 'Failed to update task' },
      { status: 500 }
    );
  }
} 