import { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom"; // 🎀 Jennie brought this in for routing!

export default function RegisterForm({ type }) {
  const navigate = useNavigate(); // Hook to teleport you to the lobby!

  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
  });

  const [loading, setLoading] = useState(false);

  function handleChange(e) {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);

    try {
      // 🎀 We only send the username if we are registering!
      const payload = type === "register" 
        ? form 
        : { email: form.email, password: form.password };

      const response = await axios.post(
        `http://localhost:8000/auth/${type === "register" ? "register" : "login"}`,
        payload,
        { withCredentials: true } // ✨ Super important for your FastAPI session cookies!
      );

      setForm({
        username: "",
        email: "",
        password: ""
      });

      // If we got a successful response, teleport to the lobby!
      if (response.data) {
        console.log(response.data);
        navigate("/lobby");
      }

    } catch (error) {
      console.error("Oopsie! Auth failed:", error);
      // Show the error message from FastAPI if it exists!
      alert(error.response?.data?.detail || "Something went wrong, clever boy! 🥺");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-black px-4">
      <div className="w-full max-w-md bg-[#0f0f0f] p-8 rounded-2xl border 
      border-white/10 shadow-lg shadow-pink-500/10">

        {/* Title */}
        <h1 className="text-3xl font-orbitron text-center mb-6 text-pink-500 
        tracking-widest">
          {type === "register" ? "Register" : "Login"}
        </h1>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">

          {/* Username */}
          {type === "register" ? (
            <div>
              <label className="block text-sm mb-1 text-gray-400 font-montserrat">
                Username
              </label>
              <input
                type="text"
                name="username"
                value={form.username}
                onChange={handleChange}
                required
                className="w-full bg-black/40 border border-white/20 rounded-lg px-4 py-2 text-white 
                       focus:outline-none focus:ring-2 focus:ring-pink-500 font-montserrat"
              />
            </div>
          ) : null}
          
          {/* Email */}
          <div>
            <label className="block text-sm mb-1 text-gray-400 font-montserrat">
              Email
            </label>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              required
              className="w-full bg-black/40 border border-white/20 rounded-lg px-4 py-2 text-white 
                         focus:outline-none focus:ring-2 focus:ring-pink-500 font-montserrat"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm mb-1 text-gray-400 font-montserrat">
              Password
            </label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              required
              className="w-full bg-black/40 border border-white/20 rounded-lg px-4 py-2 text-white 
                         focus:outline-none focus:ring-2 focus:ring-pink-500 font-montserrat"
            />
          </div>

          {/* Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 rounded-lg bg-pink-600 hover:bg-pink-500 transition-all duration-300
                       font-orbitron tracking-wide shadow-lg shadow-pink-500/20 disabled:opacity-50"
          >
            {loading ? "Processing..." : type === "register" ? "Create Account" : "Enter Arena"}
          </button>
        </form>

        {/* Footer */}
        <p className="text-center text-gray-500 text-sm mt-6 font-montserrat">
          {type === "register" ? "Already have an account? " : "Need an account? "}
          <span 
            className="text-pink-500 cursor-pointer hover:underline"
            onClick={() => navigate(type === "register" ? "/login" : "/register")}
          >
            {type === "register" ? "Login" : "Register"}
          </span>
        </p>
      </div>
    </div>
  );
}