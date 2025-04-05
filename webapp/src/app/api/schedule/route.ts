import { Client } from '@notionhq/client';
import { google } from 'googleapis';
import { NextResponse } from 'next/server';
import { addHours, isWithinInterval } from 'date-fns';

const notion = new Client({
  auth: process.env.NOTION_API_KEY,
});

const auth = new google.auth.GoogleAuth({
  credentials: JSON.parse(process.env.GOOGLE_CREDENTIALS || '{}'),
  scopes: ['https://www.googleapis.com/auth/calendar.readonly'],
});

const calendar = google.calendar({ version: 'v3', auth });

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { taskId, duration, priority } = body;

    // Get task details
    const task = await notion.pages.retrieve({ page_id: taskId });
    const taskName = task.properties.Name?.title[0]?.plain_text || 'Untitled';
    const dueDate = task.properties.Due?.date?.start;

    if (!dueDate) {
      return NextResponse.json(
        { error: 'Task must have a due date' },
        { status: 400 }
      );
    }

    // Get calendar events
    const timeMin = new Date().toISOString();
    const timeMax = new Date(dueDate).toISOString();
    const events = await calendar.events.list({
      calendarId: 'primary',
      timeMin,
      timeMax,
      singleEvents: true,
      orderBy: 'startTime',
    });

    // Find available time slots
    const availableSlots = [];
    let currentTime = new Date();

    while (currentTime < new Date(dueDate)) {
      const slotEnd = addHours(currentTime, duration);
      const isAvailable = !events.data.items?.some(event => {
        const eventStart = new Date(event.start?.dateTime || event.start?.date || '');
        const eventEnd = new Date(event.end?.dateTime || event.end?.date || '');
        return isWithinInterval(currentTime, { start: eventStart, end: eventEnd }) ||
               isWithinInterval(slotEnd, { start: eventStart, end: eventEnd });
      });

      if (isAvailable) {
        availableSlots.push({
          start: currentTime.toISOString(),
          end: slotEnd.toISOString(),
        });
      }

      currentTime = addHours(currentTime, 1);
    }

    // Sort slots by priority (closer to due date for higher priority)
    availableSlots.sort((a, b) => {
      const timeToDueA = new Date(dueDate).getTime() - new Date(a.start).getTime();
      const timeToDueB = new Date(dueDate).getTime() - new Date(b.start).getTime();
      return priority === 'High' ? timeToDueA - timeToDueB : timeToDueB - timeToDueA;
    });

    return NextResponse.json({
      task: {
        id: taskId,
        name: taskName,
        dueDate,
      },
      availableSlots,
    });
  } catch (error) {
    console.error('Error scheduling task:', error);
    return NextResponse.json(
      { error: 'Failed to schedule task' },
      { status: 500 }
    );
  }
} 