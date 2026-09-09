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
import { Roadmap } from './pages/Roadmap'
import { Legal } from './pages/Legal'
import { LegalAgentDetail } from './pages/LegalAgentDetail'
import { LegalUpload } from './pages/LegalUpload'

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
        <Route path="roadmap" element={<Roadmap />} />
        <Route path="workspaces" element={<Workspaces />} />
        <Route path="workspaces/:slug" element={<Workspaces />} />
        <Route path="leads" element={<Leads />} />
        <Route path="agents" element={<Agents />} />
        <Route path="hukuk" element={<Legal />} />
        <Route path="hukuk/belge" element={<LegalUpload />} />
        <Route path="hukuk/:slug" element={<LegalAgentDetail />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
