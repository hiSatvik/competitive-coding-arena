import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";

import ProblemPanel from "../Arena/ProblemPanel";
import CodeEditor from "../Arena/CodeEditor";
import SubmissionConsole from "../Arena/SubmissionConsole";
import Timer from "../Arena/Timer";
import Leaderboard from "../LeaderBoard/LeaderBoard";


export default function RoomArena() {
  const { roomCode } = useParams();
  const navigate = useNavigate();
  const socketRef = useRef(null);
  const questionsRef = useRef([]);
  const currentQuestionIndexRef = useRef(0);

  const [room, setRoom] = useState(null);
  const [code, setCode] = useState("");
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [consoleOutput, setConsoleOutput] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [username, setUsername] = useState("");

  const questions = room?.questions ?? [];
  const problem = questions[currentQuestionIndex] ?? null;
  const matchInitialSeconds = room?.start_time
    ? Math.max((room?.match_duration_seconds ?? 1800) - Math.floor(Date.now() / 1000 - room.start_time), 0)
    : room?.match_duration_seconds ?? 1800;
  const myScore = useMemo(
    () => leaderboard.find((entry) => entry.username === username)?.score ?? 0,
    [leaderboard, username]
  );

  const buildWinnerMessage = (winnerUsernames = [], reason) => {
    if (!winnerUsernames.length) {
      return "The match finished without a winner.";
    }

    const names = winnerUsernames.join(", ");
    if (reason === "completed_all_first") {
      return `${names} solved all 5 problems first and won the match.`;
    }
    return `${names} finished with the highest solved count. Ties are allowed.`;
  };

  useEffect(() => {
    questionsRef.current = questions;
  }, [questions]);

  useEffect(() => {
    currentQuestionIndexRef.current = currentQuestionIndex;
  }, [currentQuestionIndex]);

  useEffect(() => {
    async function loadRoom() {
      try {
        const response = await axios.get(`http://localhost:8000/game/room/${roomCode}`, {
          withCredentials: true,
        });

        if (response.data.status === "waiting") {
          navigate(`/waiting-room/${roomCode}`);
          return;
        }

        setRoom(response.data);
        setUsername(response.data.username);
        setCode(response.data.questions?.[0]?.starter_code ?? "");
        setLeaderboard(response.data.leaderboard ?? []);

        if (response.data.status === "completed") {
          setConsoleOutput({
            status: "Completed",
            message: buildWinnerMessage(
              response.data.winner_usernames,
              response.data.winner_reason
            ),
          });
        }
      } catch (err) {
        console.error("Failed to load room arena:", err);
      }
    }

    loadRoom();
  }, [navigate, roomCode]);

  useEffect(() => {
    const socketUrl = `ws://localhost:8000/ws/room/${roomCode}`;
    socketRef.current = new WebSocket(socketUrl);

    socketRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "SUBMISSION_UPDATE") {
        setLeaderboard(data.leaderboard ?? []);

        if (data.username === username) {
          setConsoleOutput({
            status: data.success ? "Accepted" : data.execution_details?.status ?? "Rejected",
            message:
              data.execution_details?.results
                ?.map((res) => `Test Case ${res.test_case}: ${res.status}`)
                .join("\n") || data.message,
          });

          if (data.success) {
            const nextIndex = currentQuestionIndexRef.current + 1;
            const nextProblem = questionsRef.current[nextIndex];
            if (nextProblem) {
              setCurrentQuestionIndex(nextIndex);
              setCode(nextProblem.starter_code ?? "");
            }
          }
          setIsEvaluating(false);
        }
      }

      if (data.type === "MATCH_COMPLETED") {
        setLeaderboard(data.leaderboard ?? []);
        setRoom((current) =>
          current
            ? {
                ...current,
                status: "completed",
                winner_usernames: data.winner_usernames ?? [],
                winner_reason: data.winner_reason,
                completed_at: data.completed_at,
              }
            : current
        );
        setConsoleOutput({
          status: "Completed",
          message: buildWinnerMessage(data.winner_usernames, data.winner_reason),
        });
        setIsEvaluating(false);
      }
    };

    return () => {
      if (socketRef.current) socketRef.current.close();
    };
  }, [roomCode, username]);

  const handleSubmit = async () => {
    if (!problem) return;

    if (room?.status === "completed") {
      setConsoleOutput({
        status: "Completed",
        message: buildWinnerMessage(room?.winner_usernames, room?.winner_reason),
      });
      return;
    }

    setIsEvaluating(true);
    setConsoleOutput({ status: "Evaluating", message: "Submitting to the room judge..." });

    try {
      await axios.post(
        "http://localhost:8000/game/room-submit",
        {
          room_code: roomCode,
          question_id: problem.id,
          code,
        },
        { withCredentials: true }
      );
    } catch (err) {
      console.error("Room submission failed:", err);
      setConsoleOutput({ status: "Error", message: "Room submission failed." });
      setIsEvaluating(false);
    }
  };

  const handleRun = async () => {
    setConsoleOutput({
      status: "Info",
      message: "Multiplayer mode scores only on submit. Use Submit to send code to the room judge.",
    });
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#17102a_0%,#090909_50%,#030303_100%)] text-white">
      <div className="h-16 border-b border-white/10 flex items-center justify-between px-6 bg-black/40">
        <div className="font-orbitron tracking-[0.2em]">
          ROOM <span className="text-pink-500">{roomCode}</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="px-4 py-2 rounded-full bg-white/5 border border-white/10 text-sm font-orbitron">
            YOU: <span className="text-pink-400">{username || "Guest"}</span>
          </div>
          <div className="px-4 py-2 rounded-full bg-white/5 border border-white/10 text-sm font-orbitron">
            SCORE: <span className="text-pink-400">{myScore}</span>
          </div>
          <Timer
            key={`${roomCode}-${room?.start_time ?? "pending"}`}
            initialSeconds={matchInitialSeconds}
            onTimeUp={async () => {
              try {
                const response = await axios.get(`http://localhost:8000/game/room/${roomCode}`, {
                  withCredentials: true,
                });
                setRoom(response.data);
                setLeaderboard(response.data.leaderboard ?? []);
                setConsoleOutput({
                  status: "Completed",
                  message: buildWinnerMessage(
                    response.data.winner_usernames,
                    response.data.winner_reason
                  ),
                });
              } catch (err) {
                navigate("/lobby");
              }
            }}
          />
        </div>
        <button
          onClick={() => navigate("/lobby")}
          className="text-white/50 hover:text-white transition-colors text-sm font-fira"
        >
          LEAVE ROOM
        </button>
      </div>

      <div className="grid min-h-[calc(100vh-4rem)] grid-cols-1 xl:grid-cols-[1fr_1fr_0.8fr]">
        <div className="border-r border-white/10">
          <ProblemPanel problem={problem} />
        </div>

        <div className="flex flex-col border-r border-white/10">
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

        <div className="p-6">
          <Leaderboard players={leaderboard} />
        </div>
      </div>
    </div>
  );
}
