import React, { useState, useEffect, useCallback } from 'react'
import LandingPage from './components/LandingPage'
import AuthPage    from './components/AuthPage'
import Header      from './components/Header'
import Sidebar     from './components/Sidebar'
import ChatArea    from './components/ChatArea'
import { useAuth } from './hooks/useAuth'
import { useChat } from './hooks/useChat'
import { api }     from './utils/api'
import styles      from './styles/App.module.css'

export default function App() {
  const { user, loading, register, login, logout } = useAuth()
  const [view, setView]           = useState('landing')
  const [showAuth, setShowAuth]   = useState(false)
  const [activeTab, setActiveTab] = useState('overview')
  const [summary, setSummary]     = useState(null)

  // Manage html class for scroll behaviour
  useEffect(() => {
    const html = document.documentElement
    if (view === 'app' && user) {
      html.classList.remove('landing')
      html.classList.add('app-view')
    } else {
      html.classList.remove('app-view')
      html.classList.add('landing')
    }
    return () => {
      html.classList.remove('app-view')
      html.classList.remove('landing')
    }
  }, [view, user])

  // If user is already logged in, go straight to app
  useEffect(() => {
    if (user && !loading) {
      setView('app')
      setShowAuth(false)
      refreshSummary()
    }
  }, [user, loading])

  const refreshSummary = useCallback(async () => {
    try {
      const s = await api.getSummary()
      setSummary(s)
    } catch {}
  }, [])

  const chat = useChat(user, summary, refreshSummary)

  function handleEnterApp() {
    if (user) { setView('app'); refreshSummary() }
    else setShowAuth(true)
  }

  async function handleLogout() {
    await logout()
    setView('landing')
    setSummary(null)
    chat.resetChat()
  }

  async function handleLogin(email, password) {
    await login(email, password)
    // useEffect above handles the rest
  }

  async function handleRegister(name, email, password) {
    await register(name, email, password)
  }

  if (loading) {
    return (
      <div style={{
        height:'100vh', display:'flex', alignItems:'center',
        justifyContent:'center', background:'#09090b',
        fontFamily:'DM Serif Display,serif', fontSize:'22px',
        color:'#a3e635', gap:'10px'
      }}>
        ◈ <em style={{color:'#fafafa',fontStyle:'italic'}}>CoinCoach</em>
      </div>
    )
  }

  return (
    <>
      {/* Auth modal — shown on top of landing */}
      {showAuth && !user && (
        <AuthPage onLogin={handleLogin} onRegister={handleRegister} />
      )}

      {/* Landing page */}
      {view === 'landing' && !user && (
        <LandingPage onEnter={handleEnterApp} />
      )}

      {/* Main app */}
      {view === 'app' && user && (
        <div className={styles.root}>
          <Header
            callCount={chat.callCount}
            user={user}
            onReset={chat.resetChat}
            onLogout={handleLogout}
          />
          <div className={styles.app}>
            <Sidebar
              latestBudget={chat.latestBudget}
              summary={summary}
              activeTab={activeTab}
              onTabChange={setActiveTab}
            />
            <ChatArea
              messages={chat.messages}
              isLoading={chat.isLoading}
              callCount={chat.callCount}
              onSend={chat.sendMessage}
              user={user}
            />
          </div>
        </div>
      )}
    </>
  )
}
