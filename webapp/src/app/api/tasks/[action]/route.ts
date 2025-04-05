import { Client } from '@notionhq/client';
import { NextResponse } from 'next/server';

const notion = new Client({
  auth: process.env.NOTION_API_KEY,
});

export async function POST(
  request: Request,
  { params }: { params: { action: string } }
) {
  try {
    const { action } = params;
    const body = await request.json();

    switch (action) {
      case 'create':
        const response = await notion.pages.create({
          parent: { database_id: process.env.DATABASE_ID! },
          properties: {
            Name: {
              title: [
                {
                  text: {
                    content: body.title,
                  },
                },
              ],
            },
            Due: {
              date: {
                start: body.dueDate,
              },
            },
            Priority: {
              select: {
                name: body.priority || 'Medium',
              },
            },
            Status: {
              select: {
                name: 'To Do',
              },
            },
          },
        });
        return NextResponse.json(response);

      case 'update':
        const updateResponse = await notion.pages.update({
          page_id: body.pageId,
          properties: {
            Status: {
              select: {
                name: body.status,
              },
            },
            Priority: {
              select: {
                name: body.priority,
              },
            },
            Due: {
              date: {
                start: body.dueDate,
              },
            },
          },
        });
        return NextResponse.json(updateResponse);

      case 'delete':
        const deleteResponse = await notion.pages.update({
          page_id: body.pageId,
          archived: true,
        });
        return NextResponse.json(deleteResponse);

      default:
        return NextResponse.json(
          { error: 'Invalid action' },
          { status: 400 }
        );
    }
  } catch (error) {
    console.error('Error in task action:', error);
    return NextResponse.json(
      { error: 'Failed to process task action' },
      { status: 500 }
    );
  }
} 