import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";

import Timer from "./Timer";
import ProblemPanel from "./ProblemPanel";
import CodeEditor from "./CodeEditor";
import SubmissionConsole from "./SubmissionConsole";
import { executeCode } from "../../utils/codeExecution";


export default function Arena() {
    const { gameId } = useParams();
    const navigate = useNavigate();
    const socketRef = useRef(null);

    const [problems, setProblems] = useState([]);
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [code, setCode] = useState("");
    const [isEvaluating, setIsEvaluating] = useState(false);
    const [consoleOutput, setConsoleOutput] = useState(null);
    const [score, setScore] = useState(0);

    const problem = problems[currentQuestionIndex] ?? null;

    useEffect(() => {
        const socketUrl = `ws://localhost:8000/ws/game/${gameId}`;
        socketRef.current = new WebSocket(socketUrl);

        socketRef.current.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.status && data.type !== "connection") {
                setConsoleOutput({
                    status: data.status,
                    message:
                        data.execution_details?.results
                            ?.map((res) => `Test Case ${res.test_case}: ${res.status}`)
                            .join("\n") || data.message,
                });
                setScore(data.total_score ?? 0);
                setIsEvaluating(false);
            }
        };

        return () => {
            if (socketRef.current) socketRef.current.close();
        };
    }, [gameId]);

    useEffect(() => {
        async function getProblems() {
            try {
                const response = await axios("http://localhost:8000/game/problems");
                const fetchedProblems = response.data ?? [];
                const firstProblem = fetchedProblems[0];

                if (!firstProblem) {
                    setConsoleOutput({
                        status: "Error",
                        message: "No problems were returned by the backend.",
                    });
                    return;
                }

                setProblems(fetchedProblems);
                setCurrentQuestionIndex(0);
                setCode(firstProblem.starter_code ?? "");
            } catch (err) {
                console.error("Failed to fetch problems:", err);
                setConsoleOutput({ status: "Error", message: "Failed to load problems." });
            }
        }

        getProblems();
    }, [gameId]);

    const handleTimeUp = () => {
        alert("Session Expired!");
        navigate("/lobby");
    };

    const handleAcceptedSubmission = (result) => {
        const nextIndex = currentQuestionIndex + 1;
        const nextProblem = problems[nextIndex];

        if (nextProblem) {
            setCurrentQuestionIndex(nextIndex);
            setCode(nextProblem.starter_code ?? "");
            setConsoleOutput({
                status: result.status,
                message: [
                    result.execution_details?.results
                        ?.map((res) => `Test Case ${res.test_case}: ${res.status}`)
                        .join("\n"),
                    "",
                    "Accepted. Moving to the next question.",
                ]
                    .filter(Boolean)
                    .join("\n"),
            });
            return;
        }

        setConsoleOutput({
            status: "Completed",
            message: [
                result.execution_details?.results
                    ?.map((res) => `Test Case ${res.test_case}: ${res.status}`)
                    .join("\n"),
                "",
                `All dummy questions solved. Final score: ${result.total_score ?? score}`,
            ]
                .filter(Boolean)
                .join("\n"),
        });
    };

    const renderExecutionResult = (result, advanceOnAccept = false) => {
        setScore(result.total_score ?? 0);

        if (advanceOnAccept && result.status === "Accepted") {
            handleAcceptedSubmission(result);
            setIsEvaluating(false);
            return;
        }

        setConsoleOutput({
            status: result.status,
            message:
                result.execution_details?.results
                    ?.map((res) => `Test Case ${res.test_case}: ${res.status}`)
                    .join("\n") || result.message,
        });
        setIsEvaluating(false);
    };

    const handleSubmit = async () => {
        if (!problem) return;

        setIsEvaluating(true);
        setConsoleOutput({
            status: "Evaluating",
            message: "Submitting solution...",
        });

        try {
            const result = await executeCode(code, problem.id, gameId, "submit");
            renderExecutionResult(result, true);
        } catch (err) {
            console.error("Submission error:", err);
            setConsoleOutput({
                status: "Error",
                message: "Failed to reach the arena servers.",
            });
            setIsEvaluating(false);
        }
    };

    const handleRun = async (e) => {
        if (e) e.preventDefault();
        if (!problem) return;

        setConsoleOutput({
            status: "Evaluating",
            message: "Running test cases...",
        });
        setIsEvaluating(true);

        try {
            const result = await executeCode(code, problem.id, gameId, "run");
            renderExecutionResult(result, false);
        } catch (err) {
            console.error("Run failed:", err);
            setConsoleOutput({ status: "Error", message: "Run failed." });
            setIsEvaluating(false);
        }
    };

    return (
        <div className="h-screen w-screen bg-[#0a0a0a] flex flex-col overflow-hidden">
            <div className="h-16 border-b border-white/10 flex items-center justify-between px-6 bg-black/50">
                <div className="text-xl font-orbitron text-white tracking-widest">
                    ARENA <span className="text-pink-500">SOLO</span>
                </div>
                <div className="flex items-center gap-4">
                    <div className="px-4 py-2 rounded-full bg-white/5 border border-white/10 text-white font-orbitron text-sm tracking-wider">
                        SCORE: <span className="text-pink-500">{score}</span>
                    </div>
                    <div className="px-4 py-2 rounded-full bg-white/5 border border-white/10 text-white font-orbitron text-sm tracking-wider">
                        Q: <span className="text-pink-500">{problems.length ? currentQuestionIndex + 1 : 0}/{problems.length}</span>
                    </div>
                    <Timer initialSeconds={1800} onTimeUp={handleTimeUp} />
                </div>
                <button
                    onClick={() => navigate("/lobby")}
                    className="text-white/50 hover:text-white transition-colors text-sm font-fira"
                >
                    ABORT MISSION
                </button>
            </div>

            <div className="flex-1 flex overflow-hidden">
                <div className="w-1/2 h-full">
                    <ProblemPanel problem={problem} />
                </div>

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
