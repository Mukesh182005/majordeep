import React, { lazy } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './index.css'
import Layout from './components/Layout'
import LoadingRoute from './components/ui/LoadingRoute'
import { AuthProvider, useAuth } from './lib/useAuth'
import { ThemeProvider } from './lib/theme'
import { ROUTER_FUTURE } from './lib/router'

// Each page is its own chunk, loaded when first visited (Layout shows a loader
// meanwhile), so no single bundle has to carry every page.
const Landing = lazy(() => import('./pages/Landing'))
const UploadPage = lazy(() => import('./pages/Upload'))
const Result = lazy(() => import('./pages/Result'))
const Report = lazy(() => import('./pages/Report'))
const History = lazy(() => import('./pages/History'))
const HowItWorks = lazy(() => import('./pages/HowItWorks'))
const Login = lazy(() => import('./pages/Login'))
const Privacy = lazy(() => import('./pages/Privacy'))
const ReferencesPage = lazy(() => import('./pages/ReferencesPage'))

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingRoute />
  return user ? children : <Navigate to="/login" replace />
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter future={ROUTER_FUTURE}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Landing />} />
            <Route path="analyse" element={<UploadPage />} />
            <Route path="jobs/:jobId" element={<Result />} />
            <Route path="jobs/:jobId/report" element={<Report />} />
            <Route path="how-it-works" element={<HowItWorks />} />
            <Route path="privacy" element={<Privacy />} />
            <Route path="references" element={<ReferencesPage />} />
            <Route path="login" element={<Login />} />
            <Route
              path="history"
              element={
                <RequireAuth>
                  <History />
                </RequireAuth>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  </React.StrictMode>,
)
