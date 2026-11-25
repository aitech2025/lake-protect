import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { homeFor, useAuth } from "./auth";
import { Layout } from "./components/Layout";
import { AlertDetail } from "./desk/AlertDetail";
import { Assets } from "./desk/Assets";
import { Audit } from "./desk/Audit";
import { Dashboard } from "./desk/Dashboard";
import { Inbox } from "./desk/Inbox";
import { Login } from "./desk/Login";
import { Officials } from "./desk/Officials";
import { Queue } from "./desk/Queue";
import { Records } from "./desk/Records";
import { ReportDetail, Reports } from "./desk/Reports";
import { Satellites } from "./desk/Satellites";
import { Sources } from "./desk/Sources";
import { Monthly } from "./bulletin/Monthly";
import { ReportPage, TrackPage } from "./portal/Portal";

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
      {/* The public portal for citizens (D-062): no sign-in. */}
      <Route path="/report" element={<ReportPage />} />
      <Route path="/report/track" element={<TrackPage />} />
      <Route path="/report/track/:ref" element={<TrackPage />} />
      <Route element={<RequireUser><Layout /></RequireUser>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/inbox" element={<Inbox />} />
        <Route path="/officials" element={<Officials />} />
        <Route path="/alerts" element={<Queue />} />
        <Route path="/alerts/:id" element={<AlertDetail />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/reports/:id" element={<ReportDetail />} />
        <Route path="/assets" element={<Assets />} />
        <Route path="/records" element={<Records />} />
        <Route path="/sources" element={<Sources />} />
        <Route path="/audit" element={<Audit />} />
        <Route path="/satellites" element={<Satellites />} />
        <Route path="/monthly" element={<Monthly />} />
      </Route>
      <Route path="*" element={<Home />} />
    </Routes>
  );
}
