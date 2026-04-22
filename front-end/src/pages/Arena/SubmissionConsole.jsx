export default function SubmissionConsole({ onRun, onSubmit, isEvaluating, output }) {
    
    return (
      <div className="h-64 bg-black/60 backdrop-blur-md flex flex-col font-fira">
        {/* Console Toolbar */}
        <div className="flex justify-between items-center px-4 py-3 border-b border-white/10 bg-white/5">
          <div className="text-white/70 font-orbitron text-sm">EXECUTION CONSOLE</div>
          <div className="flex gap-3">
            <button 
              onClick={onRun} 
              disabled={isEvaluating}
              className="px-6 py-2 bg-white/10 hover:bg-white/20 text-white rounded transition-colors disabled:opacity-50"
            >
              Run Tests
            </button>
            <button 
              onClick={onSubmit} 
              disabled={isEvaluating}
              className="px-6 py-2 bg-pink-600 hover:bg-pink-500 text-white font-bold rounded shadow-[0_0_15px_rgba(219,39,119,0.4)] transition-all disabled:opacity-50"
            >
              {isEvaluating ? "EVALUATING..." : "SUBMIT"}
            </button>
          </div>
        </div>
  
        {/* Output Area */}
        <div className="flex-1 p-4 overflow-y-auto text-sm">
          {output ? (
            <div className={`p-4 rounded border ${
              output.status === 'Accepted' ? 'bg-green-500/10 border-green-500/30 text-green-400' :
              output.status === 'Evaluating' ? 'text-pink-500 animate-pulse' :
              'bg-red-500/10 border-red-500/30 text-red-400'
            }`}>
              <div className="font-bold mb-2">{output.status}</div>
              {output.message && <pre className="whitespace-pre-wrap font-mono">{output.message}</pre>}
            </div>
          ) : (
            <div className="text-white/30 italic">Awaiting execution...</div>
          )}
        </div>
      </div>
    );
  }