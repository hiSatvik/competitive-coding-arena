import { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

export default function Lobby() {
  const navigate = useNavigate();
  const [roomCodeInput, setRoomCodeInput] = useState("");
  const [roomError, setRoomError] = useState("");

  const handleSoloPlay = async () => {
    try {
      const response = await axios.post(
        "http://localhost:8000/game/start-solo",
        {},
        { withCredentials: true }
      );
      navigate(`/arena/solo/${response.data.game_id}`);
    } catch (err) {
      alert("Failed to start solo game");
    }
  };

  const handleCreateRoom = async () => {
    try {
      const response = await axios.post(
        "http://localhost:8000/game/create-room",
        {},
        { withCredentials: true }
      );
      navigate(`/waiting-room/${response.data.room_code}`);
    } catch (err) {
      alert("Failed to create room");
    }
  };

  const handleJoinRoom = async () => {
    if (!roomCodeInput.trim()) {
      setRoomError("Enter a room code first.");
      return;
    }

    try {
      setRoomError("");
      await axios.post(
        "http://localhost:8000/game/join-room",
        { room_code: roomCodeInput },
        { withCredentials: true }
      );
      navigate(`/waiting-room/${roomCodeInput}`);
    } catch (err) {
      setRoomError(err.response?.data?.detail || "Could not join room");
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#32124a_0%,#0a0a0f_45%,#030303_100%)] px-4 py-10 text-white">
      <div className="mx-auto max-w-6xl">
        <div className="mb-10 text-center">
          <p className="font-orbitron text-sm tracking-[0.35em] text-pink-400">
            COMPETITIVE ARENA
          </p>
          <h1 className="mt-4 text-5xl font-orbitron tracking-[0.18em] text-white">
            Choose Your Match Flow
          </h1>
          <p className="mx-auto mt-4 max-w-2xl font-fira text-white/60">
            Practice solo when you want fast reps, or open a live room and let
            everyone race into the same coding match after a shared 2-minute
            join window.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
          <section className="rounded-3xl border border-white/10 bg-black/30 p-8 backdrop-blur-xl shadow-2xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-orbitron text-xs tracking-[0.3em] text-green-400">
                  SOLO MODE
                </p>
                <h2 className="mt-3 text-3xl font-orbitron">
                  Warm Up Your Reflexes
                </h2>
              </div>
              <div className="rounded-full border border-green-500/20 bg-green-500/10 px-4 py-2 font-orbitron text-xs tracking-[0.2em] text-green-300">
                INSTANT START
              </div>
            </div>

            <p className="mt-6 font-fira text-white/60">
              Jump straight into the editor, run dummy problems against the
              backend judge, and move through the set one accepted submission at
              a time.
            </p>

            <button
              onClick={handleSoloPlay}
              className="mt-8 btn-primary w-full py-4 text-lg"
            >
              PLAY SOLO
            </button>
          </section>

          <section className="rounded-3xl border border-white/10 bg-white/5 p-8 backdrop-blur-xl shadow-2xl">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-orbitron text-xs tracking-[0.3em] text-pink-400">
                  ROOM MODE
                </p>
                <h2 className="mt-3 text-3xl font-orbitron">
                  Launch A Live Coding Room
                </h2>
              </div>
              <div className="rounded-full border border-pink-500/20 bg-pink-500/10 px-4 py-2 font-orbitron text-xs tracking-[0.2em] text-pink-300">
                2 MIN JOIN TIMER
              </div>
            </div>

            <div className="mt-8 grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4 font-fira text-sm text-white/65">
                1. Create a room and share the code.
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4 font-fira text-sm text-white/65">
                2. Players join during the countdown.
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4 font-fira text-sm text-white/65">
                3. Everyone enters the same match together.
              </div>
            </div>

            <button
              onClick={handleCreateRoom}
              className="mt-8 w-full rounded-2xl border border-pink-500/40 bg-pink-500/10 px-6 py-4 font-orbitron tracking-[0.18em] text-pink-300 transition hover:bg-pink-500/20"
            >
              CREATE ROOM
            </button>

            <div className="mt-5 rounded-2xl border border-white/10 bg-black/20 p-4">
              <label className="font-orbitron text-xs tracking-[0.25em] text-white/45">
                JOIN WITH CODE
              </label>
              <div className="mt-3 flex gap-2">
                <input
                  type="text"
                  placeholder="AB12"
                  className="input-field w-full text-center font-orbitron tracking-[0.25em]"
                  value={roomCodeInput}
                  maxLength={4}
                  onChange={(e) => setRoomCodeInput(e.target.value.toUpperCase())}
                />
                <button onClick={handleJoinRoom} className="btn-primary px-6">
                  JOIN
                </button>
              </div>
              {roomError && (
                <p className="mt-3 text-sm font-fira text-red-400">{roomError}</p>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
