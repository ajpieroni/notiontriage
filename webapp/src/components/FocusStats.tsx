'use client';

interface FocusStatsProps {
  stats: {
    totalFocusTime: number;
    completedPomodoros: number;
    distractions: number;
  };
}

export default function FocusStats({ stats }: FocusStatsProps) {
  const formatTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return `${hours}h ${remainingMinutes}m`;
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold mb-4">Focus Stats</h2>
      
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <span className="text-gray-600">Total Focus Time</span>
          <span className="font-medium">{formatTime(stats.totalFocusTime)}</span>
        </div>
        
        <div className="flex justify-between items-center">
          <span className="text-gray-600">Completed Pomodoros</span>
          <span className="font-medium">{stats.completedPomodoros}</span>
        </div>
        
        <div className="flex justify-between items-center">
          <span className="text-gray-600">Distractions</span>
          <span className="font-medium">{stats.distractions}</span>
        </div>
      </div>

      <div className="mt-6 pt-4 border-t">
        <h3 className="text-lg font-semibold mb-2">Productivity Score</h3>
        <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-green-500"
            style={{
              width: `${Math.min(100, (stats.completedPomodoros * 25) / (stats.distractions + 1))}%`,
            }}
          />
        </div>
        <p className="text-sm text-gray-500 mt-2">
          Based on completed pomodoros and distractions
        </p>
      </div>
    </div>
  );
} 