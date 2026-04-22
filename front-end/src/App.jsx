import { RouterProvider, createBrowserRouter } from "react-router-dom";
import RegisterForm from "./pages/LoginPage/Login";
import Lobby from "./pages/Lobby/Lobby";
import Arena from "./pages/Arena/Arena";
import WaitingRoom from "./pages/Room/WaitingRoom";
import RoomArena from "./pages/Room/RoomArena";

export default function App() {
  const router = createBrowserRouter([
    {
      path: "/register",
      element: <RegisterForm type={"register"}/>
    },
    {
      path: "/login",
      element: <RegisterForm type={"login"} />
    },
    {
      path: "/lobby",
      element: <Lobby />
    },
    {
      path: "/arena/solo/:gameId", 
      element: <Arena />
    },
    {
      path: "/waiting-room/:roomCode",
      element: <WaitingRoom />
    },
    {
      path: "/arena/room/:roomCode",
      element: <RoomArena />
    }
  ])

  return (
    <RouterProvider router={router} />
  )
}
