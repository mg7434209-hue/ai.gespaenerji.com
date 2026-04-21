import { Routes, Route, Navigate } from 'react-router-dom'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Layout } from './components/Layout'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { Workspaces } from './pages/Workspaces'
import { Leads } from './pages/Leads'
import { Agents } from './pages/Agents'
import { Settings } from './pages/Settings'
import { Inbox } from './pages/Inbox'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="inbox" element={<Inbox />} />
        <Route path="workspaces" element={<Workspaces />} />
        <Route path="workspaces/:slug" element={<Workspaces />} />
        <Route path="leads" element={<Leads />} />
        <Route path="agents" element={<Agents />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
