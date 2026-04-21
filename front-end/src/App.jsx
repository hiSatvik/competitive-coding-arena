import { RouterProvider, createBrowserRouter } from "react-router-dom";
import RegisterForm from "./pages/Login";

export default function App() {
  const router = createBrowserRouter([
    {
      path: "/register",
      element: <RegisterForm type={"register"}/>
    },
    {
      path: "/login",
      element: <RegisterForm type={"login"} />
    }
  ])

  return (
    <RouterProvider router={router} />
  )
}