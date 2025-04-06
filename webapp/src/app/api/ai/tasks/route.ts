import { NextResponse } from 'next/server';
import { TaskIntelligence } from '@/lib/ai/taskIntelligence';

const taskIntelligence = new TaskIntelligence(
  process.env.NOTION_API_KEY!,
  process.env.HUGGING_FACE_API_KEY!
);

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') || '10');
    
    // Fetch all incomplete tasks
    const response = await fetch(`${process.env.NEXT_PUBLIC_APP_URL}/api/tasks`);
    if (!response.ok) {
      throw new Error('Failed to fetch tasks');
    }
    
    const { tasks } = await response.json();
    
    // Calculate scores for all tasks
    const scoredTasks = await taskIntelligence.calculateTaskScores(tasks, new Date());
    
    // Sort by score and limit results
    const sortedTasks = scoredTasks
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);
    
    return NextResponse.json({
      tasks: sortedTasks.map(task => ({
        ...task,
        aiInsights: {
          category: task.aiInsights.category,
          confidence: Math.round(task.aiInsights.confidence * 100),
          similarity: Math.round(task.aiInsights.similarity * 100)
        }
      })),
      totalTasks: tasks.length
    });
  } catch (error) {
    console.error('Error in AI task intelligence:', error);
    return NextResponse.json(
      { error: 'Failed to process tasks' },
      { status: 500 }
    );
  }
} 