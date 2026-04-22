import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";


function formatCountdown(seconds) {
  const safe = Math.max(seconds, 0);
  const minutes = Math.floor(safe / 60).toString().padStart(2, "0");
  const remainingSeconds = (safe % 60).toString().padStart(2, "0");
  return `${minutes}:${remainingSeconds}`;
}


export default function WaitingRoom() {
  const { roomCode } = useParams();
  const navigate = useNavigate();
  const socketRef = useRef(null);

  const [room, setRoom] = useState(null);
  const [timeLeft, setTimeLeft] = useState(0);

  const players = room?.players ?? [];
  const joinDeadline = room?.join_deadline ?? null;

  const inviteLink = useMemo(() => `${window.location.origin}/waiting-room/${roomCode}`, [roomCode]);

  const syncRoomState = async () => {
    try {
      const response = await axios.get(`http://localhost:8000/game/room/${roomCode}`, {
        withCredentials: true,
      });

      if (response.data.status === "in_progress") {
        navigate(`/arena/room/${roomCode}`);
        return;
      }

      setRoom(response.data);
    } catch (err) {
      console.error("Failed to sync room:", err);
    }
  };

  useEffect(() => {
    async function loadRoom() {
      try {
        const response = await axios.post(
          "http://localhost:8000/game/join-room",
          { room_code: roomCode },
          {
            withCredentials: true,
          }
        );

        if (response.data.status === "in_progress") {
          navigate(`/arena/room/${roomCode}`);
          return;
        }

        setRoom(response.data);
      } catch (joinError) {
        await syncRoomState();
      }
    }

    loadRoom();
  }, [navigate, roomCode]);

  useEffect(() => {
    if (!joinDeadline) return;

    const update = () => {
      const seconds = joinDeadline - Math.floor(Date.now() / 1000);
      setTimeLeft(seconds);

      if (seconds <= 0) {
        syncRoomState();
      }
    };

    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [joinDeadline]);

  useEffect(() => {
    const socketUrl = `ws://localhost:8000/ws/room/${roomCode}`;
    socketRef.current = new WebSocket(socketUrl);

    socketRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "PLAYER_JOINED") {
        setRoom((current) =>
          current
            ? {
                ...current,
                players: data.players,
                join_deadline: data.join_deadline ?? current.join_deadline,
              }
            : current
        );
      }

      if (data.type === "GAME_STARTED") {
        navigate(`/arena/room/${roomCode}`);
      }
    };

    return () => {
      if (socketRef.current) socketRef.current.close();
    };
  }, [navigate, roomCode]);

  const copyRoomCode = async () => {
    await navigator.clipboard.writeText(roomCode);
  };

  const copyInviteLink = async () => {
    await navigator.clipboard.writeText(inviteLink);
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#27103d_0%,#090909_45%,#030303_100%)] text-white px-6 py-10">
      <div className="mx-auto max-w-6xl grid gap-8 lg:grid-cols-[1.25fr_0.75fr]">
        <section className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-8 shadow-2xl">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="font-orbitron text-sm tracking-[0.35em] text-pink-400">ROOM STAGING</p>
              <h1 className="mt-3 text-5xl font-orbitron tracking-[0.18em]">{roomCode}</h1>
              <p className="mt-4 max-w-2xl text-white/60 font-fira">
                Everyone has two minutes to join. When the countdown ends, the room launches automatically and all connected players jump into the match together.
              </p>
            </div>
            <div className="rounded-2xl border border-pink-500/30 bg-pink-500/10 px-6 py-4 text-center">
              <div className="text-xs font-orbitron tracking-[0.3em] text-white/60">STARTS IN</div>
              <div className="mt-2 text-4xl font-orbitron text-pink-400">{formatCountdown(timeLeft)}</div>
            </div>
          </div>

          <div className="mt-10 grid gap-4 md:grid-cols-2">
            <button
              onClick={copyRoomCode}
              className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4 text-left transition hover:bg-white/10"
            >
              <div className="font-orbitron text-xs tracking-[0.25em] text-white/50">ROOM CODE</div>
              <div className="mt-2 text-2xl font-orbitron">{roomCode}</div>
              <div className="mt-1 text-sm text-white/50">Tap to copy the join code</div>
            </button>
            <button
              onClick={copyInviteLink}
              className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4 text-left transition hover:bg-white/10"
            >
              <div className="font-orbitron text-xs tracking-[0.25em] text-white/50">INVITE LINK</div>
              <div className="mt-2 truncate text-sm text-pink-300">{inviteLink}</div>
              <div className="mt-1 text-sm text-white/50">Tap to copy a direct waiting-room link</div>
            </button>
          </div>

          <div className="mt-10 rounded-3xl border border-white/10 bg-black/20 p-6">
            <div className="flex items-center justify-between">
              <h2 className="font-orbitron text-xl tracking-[0.18em] text-white">Joined Players</h2>
              <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/60">
                {players.length} joined
              </span>
            </div>

            <div className="mt-6 grid gap-3 md:grid-cols-2">
              {players.map((player, index) => (
                <div
                  key={`${player}-${index}`}
                  className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4"
                >
                  <div className="text-xs font-orbitron tracking-[0.25em] text-white/40">PLAYER {index + 1}</div>
                  <div className="mt-2 text-lg font-fira text-white">{player}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <aside className="rounded-3xl border border-white/10 bg-black/30 p-8 backdrop-blur-xl">
          <h2 className="font-orbitron text-2xl tracking-[0.18em] text-white">How It Works</h2>
          <div className="mt-6 space-y-4 text-sm text-white/65 font-fira">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              Create a room or join using the 4-character code.
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              Everyone gets the same 2-minute join window. No manual coordination needed.
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              When the timer hits zero, the room starts automatically and everyone in this screen gets redirected into the match.
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
