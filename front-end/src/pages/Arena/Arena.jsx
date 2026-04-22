import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Timer from "./Timer";
import ProblemPanel from "./ProblemPanel";
import CodeEditor from "./CodeEditor";
import SubmissionConsole from "./SubmissionConsole";
import { executeCode } from "../../utils/codeExecution";
import axios from "axios";

export default function Arena() {
    const { gameId } = useParams();
    const navigate = useNavigate();

    // State management
    const [problem, setProblem] = useState(null);
    const [code, setCode] = useState(null);
    const [isEvaluating, setIsEvaluating] = useState(false);
    const [consoleOutput, setConsoleOutput] = useState(null);
    const [score, setScore] = useState(0);

    // Mock fetch on load (Replace with your actual FastAPI call)
    useEffect(() => {
        // This will eventually be: axios.get(`/game/status/${gameId}`)
        setTimeout(() => {
            async function getProblems() {
                const response = await axios("http://localhost:8000/game/problems")
                const problems = response.data;

                console.log(problems[0])

                setProblem(problems[0])
                setCode(problems[0].starter_code)
            }

            getProblems()
        }, 1000);
    }, [gameId]);

    const handleTimeUp = () => {
        alert("Session Expired!");
        navigate("/lobby");
    };

    const handleRun = () => {
        setConsoleOutput({ status: "Evaluating", message: "Running local test cases..." });

        try {
            const data = executeCode(code, problem.id, gameId, score)
            console.log(data);
        } catch(err) {
            console.err(err)
        }
    };

    const handleSubmit = () => {
        setIsEvaluating(true);
        setConsoleOutput({ status: "Evaluating", message: "Sending to Docker Sandbox..." });
        // TODO: Send to FastAPI submission endpoint
        setTimeout(() => {
            setIsEvaluating(false);
            setConsoleOutput({ status: "Accepted", message: "All test cases passed!\nTime: 12ms\nMemory: 4.2MB" });
        }, 2000);
    };

    return (
        <div className="h-screen w-screen bg-[#0a0a0a] flex flex-col overflow-hidden">
            {/* Top Navbar */}
            <div className="h-16 border-b border-white/10 flex items-center justify-between px-6 bg-black/50">
                <div className="text-xl font-orbitron text-white tracking-widest">
                    ARENA <span className="text-pink-500">SOLO</span>
                </div>
                <Timer initialSeconds={1800} onTimeUp={handleTimeUp} />
                <button onClick={() => navigate("/lobby")} className="text-white/50 hover:text-white transition-colors text-sm font-fira">
                    ABORT MISSION
                </button>
            </div>

            {/* Main Workspace */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left Column: Problem */}
                <div className="w-1/2 h-full">
                    <ProblemPanel problem={problem} />
                </div>

                {/* Right Column: Editor & Console */}
                <div className="w-1/2 h-full flex flex-col">
                    <div className="flex-1">
                        <CodeEditor code={code} setCode={setCode} />
                    </div>
                    <SubmissionConsole
                        onRun={handleRun}
                        onSubmit={handleSubmit}
                        isEvaluating={isEvaluating}
                        output={consoleOutput}
                    />
                </div>
            </div>
        </div>
    );
}