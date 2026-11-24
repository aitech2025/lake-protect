import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { homeFor, useAuth } from "./auth";
import { Layout } from "./components/Layout";
import { AlertDetail } from "./desk/AlertDetail";
import { Assets } from "./desk/Assets";
import { Audit } from "./desk/Audit";
import { Login } from "./desk/Login";
import { Queue } from "./desk/Queue";
import { Records } from "./desk/Records";
import { Sources } from "./desk/Sources";
import { Monthly } from "./bulletin/Monthly";

function RequireUser({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth();
  if (!ready && !user) return null;
  return user ? <>{children}</> : <Navigate to="/login" replace />;
}

function Home() {
  const { user } = useAuth();
  return <Navigate to={user ? homeFor(user.role) : "/login"} replace />;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<RequireUser><Layout /></RequireUser>}>
        <Route path="/alerts" element={<Queue />} />
        <Route path="/alerts/:id" element={<AlertDetail />} />
        <Route path="/assets" element={<Assets />} />
        <Route path="/records" element={<Records />} />
        <Route path="/sources" element={<Sources />} />
        <Route path="/audit" element={<Audit />} />
        <Route path="/monthly" element={<Monthly />} />
      </Route>
      <Route path="*" element={<Home />} />
    </Routes>
  );
}
