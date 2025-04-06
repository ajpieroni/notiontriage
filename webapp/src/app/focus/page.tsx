'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import PomodoroTimer from '@/components/PomodoroTimer';
import FocusTask from '@/components/FocusTask';
import FocusStats from '@/components/FocusStats';

export default function FocusPage() {
  const [currentTask, setCurrentTask] = useState(null);
  const [isFocusMode, setIsFocusMode] = useState(false);
  const [focusStats, setFocusStats] = useState({
    totalFocusTime: 0,
    completedPomodoros: 0,
    distractions: 0
  });
  const router = useRouter();

  const startFocusMode = () => {
    setIsFocusMode(true);
    // TODO: Implement website blocking
  };

  const stopFocusMode = () => {
    setIsFocusMode(false);
    // TODO: Stop website blocking
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Focus Mode</h1>
          <button
            onClick={() => router.push('/')}
            className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300"
          >
            Exit
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Main Focus Area */}
          <div className="md:col-span-2">
            <div className="bg-white rounded-lg shadow-lg p-6">
              <FocusTask 
                currentTask={currentTask}
                setCurrentTask={setCurrentTask}
              />
              
              <div className="mt-8">
                <PomodoroTimer 
                  isFocusMode={isFocusMode}
                  onComplete={() => {
                    setFocusStats(prev => ({
                      ...prev,
                      completedPomodoros: prev.completedPomodoros + 1
                    }));
                  }}
                />
              </div>

              <div className="mt-8 flex justify-center">
                {!isFocusMode ? (
                  <button
                    onClick={startFocusMode}
                    className="px-6 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600"
                  >
                    Start Focus Mode
                  </button>
                ) : (
                  <button
                    onClick={stopFocusMode}
                    className="px-6 py-3 bg-red-500 text-white rounded-lg hover:bg-red-600"
                  >
                    Stop Focus Mode
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Stats Sidebar */}
          <div className="md:col-span-1">
            <FocusStats stats={focusStats} />
          </div>
        </div>
      </div>
    </div>
  );
} 