import React from 'react';
import { Trophy, Clock, CheckCircle, User } from 'lucide-react';

const Leaderboard = ({ players = [] }) => {
  // Supports both the older solved/time shape and the newer score-based room shape.
  const sortedPlayers = [...players].sort((a, b) => {
    const scoreA = a.score ?? a.solved ?? 0;
    const scoreB = b.score ?? b.solved ?? 0;
    if (scoreB !== scoreA) return scoreB - scoreA;
    return (a.time ?? 0) - (b.time ?? 0);
  });

  return (
    <div className="w-full max-w-4xl mx-auto p-6 bg-black/40 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-3xl font-orbitron text-white tracking-wider flex items-center gap-3">
            <Trophy className="text-yellow-500 w-8 h-8" />
            HALL OF <span className="text-pink-500">FAME</span>
          </h2>
          <p className="text-white/50 font-fira text-sm mt-1">Real-time performance rankings</p>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-hidden rounded-xl border border-white/5 bg-white/5">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-white/10 text-white/70 font-orbitron text-xs uppercase tracking-widest">
              <th className="px-6 py-4">Rank</th>
              <th className="px-6 py-4">Architect</th>
              <th className="px-6 py-4 text-center">Score</th>
              <th className="px-6 py-4 text-center">Total Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 font-fira">
            {sortedPlayers.map((player, index) => (
              <tr 
                key={player.username} 
                className={`group transition-all duration-300 hover:bg-white/10 ${
                  index === 0 ? 'bg-pink-500/5' : ''
                }`}
              >
                {/* Rank Digit */}
                <td className="px-6 py-4">
                  <span className={`text-lg font-bold ${
                    index === 0 ? 'text-yellow-400' : 
                    index === 1 ? 'text-gray-300' : 
                    index === 2 ? 'text-orange-400' : 'text-white/30'
                  }`}>
                    #{index + 1}
                  </span>
                </td>

                {/* User Info */}
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white/5 rounded-full border border-white/10 group-hover:border-pink-500/50 transition-colors">
                      <User className="w-4 h-4 text-white/70" />
                    </div>
                    <span className="text-white font-medium group-hover:text-pink-400 transition-colors">
                      {player.username}
                    </span>
                  </div>
                </td>

                {/* Questions Solved */}
                <td className="px-6 py-4">
                  <div className="flex items-center justify-center gap-2 text-green-400">
                    <CheckCircle className="w-4 h-4" />
                    <span className="font-bold">{player.score ?? player.solved ?? 0}</span>
                  </div>
                </td>

                {/* Time Taken */}
                <td className="px-6 py-4">
                  <div className="flex items-center justify-center gap-2 text-blue-400">
                    <Clock className="w-4 h-4" />
                    <span>{player.time ?? 0}s</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {players.length === 0 && (
        <div className="text-center py-12 text-white/20 italic font-fira">
          Waiting for results to materialize...
        </div>
      )}
    </div>
  );
};

export default Leaderboard;
