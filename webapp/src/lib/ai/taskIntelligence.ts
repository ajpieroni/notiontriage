import { Client } from '@notionhq/client';
import { pipeline, Pipeline } from 'transformers';
import * as tf from '@tensorflow/tfjs';

interface Task {
  id: string;
  properties: {
    Name: {
      title: [{ plain_text: string }];
    };
    Priority: {
      select: {
        name: string;
      };
    };
    Status: {
      status: {
        name: string;
      };
    };
    Due: {
      date: {
        start: string;
      };
    };
    'Time Estimate': {
      number: number;
    };
    Energy: {
      select: {
        name: string;
      };
    };
    Dependencies: {
      relation: Array<{ id: string }>;
    };
    Description?: {
      rich_text: Array<{ plain_text: string }>;
    };
  };
}

interface TaskScore {
  task: Task;
  score: number;
  reasons: string[];
  aiInsights: {
    category: string;
    confidence: number;
    similarity: number;
  };
}

export class TaskIntelligence {
  private notion: Client;
  private historicalData: Map<string, number> = new Map(); // taskId -> completionTime
  private textClassifier: Pipeline;
  private embeddingModel: Pipeline;
  private taskPatterns: Map<string, number[]> = new Map();
  private HUGGING_FACE_API_KEY: string;
  private HUGGING_FACE_API_URL = 'https://api-inference.huggingface.co/models';

  constructor(notionApiKey: string, huggingFaceApiKey: string) {
    this.notion = new Client({ auth: notionApiKey });
    this.HUGGING_FACE_API_KEY = huggingFaceApiKey;
    this.initializeModels();
  }

  private async initializeModels() {
    // Initialize text classification model for task categorization
    this.textClassifier = await pipeline('text-classification', 'distilbert-base-uncased');
    
    // Initialize sentence transformer for task embeddings
    this.embeddingModel = await pipeline('feature-extraction', 'sentence-transformers/all-MiniLM-L6-v2');
  }

  async calculateTaskScores(tasks: Task[], currentTime: Date): Promise<TaskScore[]> {
    return Promise.all(tasks.map(async (task) => {
      const [baseScore, aiInsights] = await Promise.all([
        this.calculateTaskScore(task, currentTime),
        this.getAIInsights(task)
      ]);
      
      return {
        task,
        score: baseScore + (aiInsights.confidence * 50) + (aiInsights.similarity * 50),
        reasons: this.getScoreReasons(task, baseScore),
        aiInsights
      };
    }));
  }

  private async calculateTaskScore(task: Task, currentTime: Date): Promise<number> {
    let score = 0;
    
    // Due date urgency (0-30 points)
    score += this.calculateDueDateScore(task, currentTime);
    
    // Dependency status (0-20 points)
    score += await this.calculateDependencyScore(task);
    
    // Historical completion patterns (0-20 points)
    score += this.calculateHistoricalScore(task);
    
    // Energy level matching (0-15 points)
    score += this.calculateEnergyScore(task, currentTime);
    
    // Time of day optimization (0-15 points)
    score += this.calculateTimeOfDayScore(task, currentTime);

    // Add AI-based scoring
    score += await this.calculateAIScore(task);

    return score;
  }

  private async calculateAIScore(task: Task): Promise<number> {
    const taskText = this.getTaskText(task);
    
    // Use Hugging Face model to analyze task text
    const classification = await this.textClassifier(taskText);
    const embeddings = await this.generateTaskEmbeddings(task);
    
    // Calculate similarity with historical successful tasks
    let similarityScore = 0;
    for (const [_, pattern] of this.taskPatterns) {
      const similarity = this.calculateCosineSimilarity(embeddings, pattern);
      similarityScore = Math.max(similarityScore, similarity);
    }
    
    // Combine classification confidence and similarity score
    return (classification[0].score * 50) + (similarityScore * 50);
  }

  private async generateTaskEmbeddings(task: Task): Promise<number[]> {
    const taskText = this.getTaskText(task);
    const result = await this.embeddingModel(taskText);
    return result[0];
  }

  private calculateCosineSimilarity(vec1: number[], vec2: number[]): number {
    const dotProduct = vec1.reduce((sum, val, i) => sum + val * vec2[i], 0);
    const norm1 = Math.sqrt(vec1.reduce((sum, val) => sum + val * val, 0));
    const norm2 = Math.sqrt(vec2.reduce((sum, val) => sum + val * val, 0));
    return dotProduct / (norm1 * norm2);
  }

  private getTaskText(task: Task): string {
    const name = task.properties.Name?.title[0]?.plain_text || '';
    const description = task.properties.Description?.rich_text[0]?.plain_text || '';
    return `${name} ${description}`.trim();
  }

  private calculateDueDateScore(task: Task, currentTime: Date): number {
    if (!task.properties.Due?.date?.start) return 0;
    
    const dueDate = new Date(task.properties.Due.date.start);
    const daysUntilDue = Math.ceil((dueDate.getTime() - currentTime.getTime()) / (1000 * 60 * 60 * 24));
    
    if (daysUntilDue < 0) return 30; // Overdue
    if (daysUntilDue === 0) return 25; // Due today
    if (daysUntilDue <= 1) return 20; // Due tomorrow
    if (daysUntilDue <= 3) return 15; // Due in 3 days
    if (daysUntilDue <= 7) return 10; // Due in a week
    return 5; // Due later
  }

  private async calculateDependencyScore(task: Task): Promise<number> {
    const dependencies = task.properties.Dependencies?.relation || [];
    if (dependencies.length === 0) return 20; // No dependencies = high score
    
    // Check if all dependencies are complete
    const dependencyTasks = await Promise.all(
      dependencies.map(dep => this.notion.pages.retrieve({ page_id: dep.id }))
    );
    
    const incompleteDependencies = dependencyTasks.filter(
      task => task.properties.Status?.status?.name !== 'Done'
    );
    
    if (incompleteDependencies.length === 0) return 20; // All dependencies complete
    return 5; // Some dependencies incomplete
  }

  private calculateHistoricalScore(task: Task): number {
    const historicalTime = this.historicalData.get(task.id);
    if (!historicalTime) return 10; // No historical data
    
    // If task typically takes longer than estimated, prioritize it
    const estimatedTime = task.properties['Time Estimate']?.number || 0;
    return historicalTime > estimatedTime ? 20 : 10;
  }

  private calculateEnergyScore(task: Task, currentTime: Date): number {
    const taskEnergy = task.properties.Energy?.select?.name;
    if (!taskEnergy) return 7; // No energy level specified
    
    // This would be replaced with actual energy level tracking
    const currentEnergy = this.getCurrentEnergyLevel(currentTime);
    
    return taskEnergy === currentEnergy ? 15 : 7;
  }

  private calculateTimeOfDayScore(task: Task, currentTime: Date): number {
    const hour = currentTime.getHours();
    
    // Example time-based scoring
    if (hour >= 9 && hour <= 11) {
      return task.properties.Priority?.select?.name === 'High' ? 15 : 7;
    } else if (hour >= 14 && hour <= 16) {
      return task.properties.Priority?.select?.name === 'Medium' ? 15 : 7;
    }
    return 7;
  }

  private getCurrentEnergyLevel(currentTime: Date): string {
    const hour = currentTime.getHours();
    
    if (hour >= 9 && hour <= 11) return 'High';
    if (hour >= 14 && hour <= 16) return 'Medium';
    return 'Low';
  }

  private getScoreReasons(task: Task, score: number): string[] {
    const reasons: string[] = [];
    
    if (task.properties.Due?.date?.start) {
      const dueDate = new Date(task.properties.Due.date.start);
      const daysUntilDue = Math.ceil((dueDate.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24));
      
      if (daysUntilDue < 0) reasons.push('Overdue');
      else if (daysUntilDue === 0) reasons.push('Due today');
      else if (daysUntilDue <= 1) reasons.push('Due tomorrow');
    }
    
    if (task.properties.Priority?.select?.name === 'High') {
      reasons.push('High priority');
    }
    
    if (task.properties.Dependencies?.relation?.length === 0) {
      reasons.push('No dependencies');
    }
    
    return reasons;
  }

  // Update historical data when a task is completed
  updateHistoricalData(taskId: string, completionTime: number): void {
    this.historicalData.set(taskId, completionTime);
  }

  // Update task patterns when a task is completed successfully
  updateTaskPatterns(taskId: string, completionTime: number, embeddings: number[]): void {
    this.historicalData.set(taskId, completionTime);
    if (completionTime < (task.properties['Time Estimate']?.number || 0)) {
      this.taskPatterns.set(taskId, embeddings);
    }
  }

  private async getAIInsights(task: Task) {
    const taskText = this.getTaskText(task);
    
    try {
      // Get task category using text classification
      const categoryResponse = await fetch(
        `${this.HUGGING_FACE_API_URL}/distilbert-base-uncased-finetuned-sst-2-english`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.HUGGING_FACE_API_KEY}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ inputs: taskText }),
        }
      );
      
      const categoryData = await categoryResponse.json();
      
      // Get task embeddings for similarity comparison
      const embeddingResponse = await fetch(
        `${this.HUGGING_FACE_API_URL}/sentence-transformers/all-MiniLM-L6-v2`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.HUGGING_FACE_API_KEY}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ inputs: taskText }),
        }
      );
      
      const embeddingData = await embeddingResponse.json();
      
      return {
        category: categoryData[0][0].label,
        confidence: categoryData[0][0].score,
        similarity: this.calculateSimilarity(embeddingData[0], this.getHistoricalEmbeddings())
      };
    } catch (error) {
      console.error('Error getting AI insights:', error);
      return {
        category: 'unknown',
        confidence: 0.5,
        similarity: 0.5
      };
    }
  }

  private calculateSimilarity(embedding: number[], historicalEmbeddings: number[][]): number {
    if (historicalEmbeddings.length === 0) return 0.5;
    
    let maxSimilarity = 0;
    for (const historical of historicalEmbeddings) {
      const similarity = this.cosineSimilarity(embedding, historical);
      maxSimilarity = Math.max(maxSimilarity, similarity);
    }
    return maxSimilarity;
  }

  private getHistoricalEmbeddings(): number[][] {
    // This would be replaced with actual historical embeddings storage
    return [];
  }
} 