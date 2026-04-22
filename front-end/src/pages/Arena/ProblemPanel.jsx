export default function ProblemPanel({ problem }) {
    if (!problem) return <div className="text-white/50 p-6 font-fira">Loading transmission...</div>;
  
    return (
      <div className="h-full overflow-y-auto custom-scrollbar bg-black/40 backdrop-blur-sm border-r border-white/10 p-6 space-y-6 text-gray-300 font-fira">
        <h2 className="text-3xl font-orbitron text-white">{problem.title}</h2>
        
        <div className="flex gap-4 text-sm font-orbitron">
          <span className="px-3 py-1 bg-green-500/10 text-green-400 rounded border border-green-500/20">
            {problem.difficulty}
          </span>
          <span className="px-3 py-1 bg-white/5 rounded border border-white/10">
            Time Limit: {problem.timeLimit}s
          </span>
        </div>
  
        <div className="prose prose-invert max-w-none">
          <p className="text-lg leading-relaxed">{problem.description}</p>
          
          <h3 className="text-xl text-pink-500 mt-8 mb-4 font-orbitron">Constraints</h3>
          <ul className="list-disc pl-5 space-y-2 text-white/80">
            {problem.constraints?.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
  
          <h3 className="text-xl text-pink-500 mt-8 mb-4 font-orbitron">Examples</h3>
          {problem.examples?.map((ex, i) => (
            <div key={i} className="mb-4 p-4 bg-white/5 rounded-lg border border-white/10 font-mono text-sm">
              <div className="text-white/50 mb-1">Input:</div>
              <div className="mb-3 text-white">{ex.input}</div>
              <div className="text-white/50 mb-1">Output:</div>
              <div className="text-white">{ex.output}</div>
            </div>
          ))}
        </div>
      </div>
    );
  }