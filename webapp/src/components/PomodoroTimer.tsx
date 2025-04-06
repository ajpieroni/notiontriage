'use client';

import { useState, useEffect } from 'react';

interface PomodoroTimerProps {
  isFocusMode: boolean;
  onComplete: () => void;
}

export default function PomodoroTimer({ isFocusMode, onComplete }: PomodoroTimerProps) {
  const [timeLeft, setTimeLeft] = useState(25 * 60); // 25 minutes in seconds
  const [isRunning, setIsRunning] = useState(false);
  const [isBreak, setIsBreak] = useState(false);
  const [workDuration, setWorkDuration] = useState(25); // minutes
  const [breakDuration, setBreakDuration] = useState(5); // minutes

  useEffect(() => {
    let timer: NodeJS.Timeout;
    
    if (isRunning && timeLeft > 0) {
      timer = setInterval(() => {
        setTimeLeft((prev) => prev - 1);
      }, 1000);
    } else if (timeLeft === 0) {
      onComplete();
      setIsBreak(!isBreak);
      setTimeLeft((isBreak ? workDuration : breakDuration) * 60);
      // Play completion sound
      new Audio('/sounds/complete.mp3').play().catch(() => {});
    }

    return () => clearInterval(timer);
  }, [isRunning, timeLeft, isBreak, workDuration, breakDuration, onComplete]);

  const toggleTimer = () => {
    setIsRunning(!isRunning);
  };

  const resetTimer = () => {
    setIsRunning(false);
    setTimeLeft((isBreak ? breakDuration : workDuration) * 60);
  };

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className="text-center">
      <div className="mb-4">
        <h2 className="text-2xl font-semibold">
          {isBreak ? 'Break Time' : 'Focus Time'}
        </h2>
        <div className="text-6xl font-bold my-4">{formatTime(timeLeft)}</div>
      </div>

      <div className="flex justify-center gap-4">
        <button
          onClick={toggleTimer}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          {isRunning ? 'Pause' : 'Start'}
        </button>
        <button
          onClick={resetTimer}
          className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
        >
          Reset
        </button>
      </div>

      {!isFocusMode && (
        <div className="mt-6 grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Work Duration (minutes)
            </label>
            <input
              type="number"
              value={workDuration}
              onChange={(e) => setWorkDuration(Number(e.target.value))}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              min="1"
              max="60"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Break Duration (minutes)
            </label>
            <input
              type="number"
              value={breakDuration}
              onChange={(e) => setBreakDuration(Number(e.target.value))}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              min="1"
              max="30"
            />
          </div>
        </div>
      )}
    </div>
  );
} 