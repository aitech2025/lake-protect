import { lazy, Suspense, type ComponentType, type ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { homeFor, useAuth } from "./auth";
import { Layout } from "./components/Layout";
import { PageState } from "./components/PageState";
import { Login } from "./desk/Login";

/** Each page loads on first visit, so sign-in does not wait for the map library. */
function page<K extends string>(load: () => Promise<Record<K, ComponentType>>, name: K) {
  return lazy(() => load().then((m) => ({ default: m[name] })));
}

const AlertDetail = page(() => import("./desk/AlertDetail"), "AlertDetail");
const CitizenOperations = page(() => import("./desk/CitizenOperations"), "CitizenOperations");
const Assets = page(() => import("./desk/Assets"), "Assets");
const Asset360 = page(() => import("./desk/Asset360"), "Asset360");
const Audit = page(() => import("./desk/Audit"), "Audit");
const Dashboard = page(() => import("./desk/Dashboard"), "Dashboard");
const MapPage = page(() => import("./desk/MapPage"), "MapPage");
const Inbox = page(() => import("./desk/Inbox"), "Inbox");
const Officials = page(() => import("./desk/Officials"), "Officials");
const Queue = page(() => import("./desk/Queue"), "Queue");
const Records = page(() => import("./desk/Records"), "Records");
const Registry = page(() => import("./desk/Registry"), "Registry");
const Reports = page(() => import("./desk/Reports"), "Reports");
const ReportDetail = page(() => import("./desk/Reports"), "ReportDetail");
const Satellites = page(() => import("./desk/Satellites"), "Satellites");
const Sources = page(() => import("./desk/Sources"), "Sources");
const System = page(() => import("./desk/System"), "System");
const Monthly = page(() => import("./bulletin/Monthly"), "Monthly");
const WhatsAppTest = page(() => import("./desk/WhatsAppTest"), "WhatsAppTest");
const ReportPage = page(() => import("./portal/Portal"), "ReportPage");
const TrackPage = page(() => import("./portal/Portal"), "TrackPage");

const Loading = () => <div className="page"><PageState loading /></div>;

function RequireUser({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth();
  if (!ready && !user) return null;
  return user ? <>{children}</> : <Navigate to="/login" replace />;
}

function Home() {
  const { user } = useAuth();
  return <Navigate to={user ? homeFor(user.role) : "/login"} replace />;
}

const desk = (el: ReactNode) => <Suspense fallback={<Loading />}>{el}</Suspense>;

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      {/* The public portal for citizens (D-062): no sign-in. */}
      <Route path="/report" element={desk(<ReportPage />)} />
      <Route path="/report/track" element={desk(<TrackPage />)} />
      <Route path="/report/track/:ref" element={desk(<TrackPage />)} />
      <Route element={<RequireUser><Layout /></RequireUser>}>
        <Route path="/dashboard" element={desk(<Dashboard />)} />
        <Route path="/map" element={desk(<MapPage />)} />
        <Route path="/inbox" element={desk(<Inbox />)} />
        <Route path="/officials" element={desk(<Officials />)} />
        <Route path="/alerts" element={desk(<Queue />)} />
        <Route path="/alerts/:id" element={desk(<AlertDetail />)} />
        <Route path="/reports" element={desk(<Reports />)} />
        <Route path="/reports/:id" element={desk(<ReportDetail />)} />
        <Route path="/assets" element={desk(<Assets />)} />
        <Route path="/assets/:id" element={desk(<Asset360 />)} />
        <Route path="/records" element={desk(<Records />)} />
        <Route path="/registry" element={desk(<Registry />)} />
        <Route path="/system" element={desk(<System />)} />
        <Route path="/sources" element={desk(<Sources />)} />
        <Route path="/audit" element={desk(<Audit />)} />
        <Route path="/satellites" element={desk(<Satellites />)} />
        <Route path="/monthly" element={desk(<Monthly />)} />
        <Route path="/whatsapp-test" element={desk(<WhatsAppTest />)} />
        <Route path="/citizen-operations" element={desk(<CitizenOperations />)} />
      </Route>
      <Route path="*" element={<Home />} />
    </Routes>
  );
}
