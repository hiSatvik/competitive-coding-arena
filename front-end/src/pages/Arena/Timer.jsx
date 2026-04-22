import { useState, useEffect } from "react";

export default function Timer({ initialSeconds, onTimeUp }) {
  const [timeLeft, setTimeLeft] = useState(initialSeconds);

  useEffect(() => {
    if (timeLeft <= 0) {
      onTimeUp();
      return;
    }
    const timerId = setInterval(() => setTimeLeft((t) => t - 1), 1000);
    return () => clearInterval(timerId);
  }, [timeLeft, onTimeUp]);

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const isLowTime = timeLeft < 300; // Under 5 minutes

  return (
    <div className={`px-6 py-2 rounded-full backdrop-blur-md border font-orbitron text-2xl tracking-widest transition-colors duration-300 ${
      isLowTime 
        ? "bg-red-500/10 border-red-500/50 text-red-500 shadow-[0_0_15px_rgba(239,68,68,0.2)]" 
        : "bg-white/5 border-white/10 text-pink-500"
    }`}>
      {formatTime(timeLeft)}
    </div>
  );
}