import { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

export default function Lobby() {
  const navigate = useNavigate();
  const [roomCodeInput, setRoomCodeInput] = useState("");

  const handleSoloPlay = async () => {
    try {
      const response = await axios.post("http://localhost:8000/game/start-solo", {}, { withCredentials: true });
      // Navigate to the arena with the new game_id
      navigate(`/arena/solo/${response.data.game_id}`);
    } catch (err) {
      alert("Failed to start solo game");
    }
  };

  const handleCreateRoom = async () => {
    try {
      const response = await axios.post("http://localhost:8000/game/create-room", {}, { withCredentials: true });
      // Navigate to waiting room with room_code
      navigate(`/waiting-room/${response.data.room_code}`);
    } catch (err) {
      alert("Failed to create room");
    }
  };

  const handleJoinRoom = async () => {
    try {
      await axios.post("http://localhost:8000/game/join-room", { room_code: roomCodeInput }, { withCredentials: true });
      navigate(`/waiting-room/${roomCodeInput}`);
    } catch (err) {
      alert(err.response?.data?.detail || "Could not join room");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black px-4">
      <div className="w-full max-w-2xl space-y-8">
        <h1 className="text-4xl font-orbitron text-center text-pink-500 tracking-widest">THE LOBBY</h1>
        
        <div className="grid md:grid-cols-2 gap-6">
          {/* Solo Play Section */}
          <div className="card flex flex-col items-center justify-center space-y-4 p-8">
            <h2 className="text-xl font-orbitron">SOLO ARENA</h2>
            <button onClick={handleSoloPlay} className="btn-primary w-full py-4 text-lg">PLAY SOLO</button>
          </div>

          {/* Multiplayer Section */}
          <div className="card space-y-4 p-8">
            <h2 className="text-xl font-orbitron text-center">MULTIPLAYER</h2>
            <button onClick={handleCreateRoom} className="w-full py-2 border border-pink-500 text-pink-500 rounded-lg hover:bg-pink-500/10 transition-all font-orbitron">
              CREATE ROOM
            </button>
            <div className="flex gap-2">
              <input 
                type="text" 
                placeholder="ENTER CODE" 
                className="input-field w-full text-center font-fira"
                value={roomCodeInput}
                onChange={(e) => setRoomCodeInput(e.target.value.toUpperCase())}
              />
              <button onClick={handleJoinRoom} className="btn-primary">JOIN</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}