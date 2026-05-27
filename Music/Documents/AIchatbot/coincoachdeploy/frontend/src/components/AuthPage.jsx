import React, { useState } from 'react'
import styles from '../styles/AuthPage.module.css'

export default function AuthPage({ onLogin, onRegister }) {
  const [mode, setMode]     = useState('login')
  const [name, setName]     = useState('')
  const [email, setEmail]   = useState('')
  const [password, setPass] = useState('')
  const [error, setError]   = useState('')
  const [loading, setLoad]  = useState(false)
  const [success, setSucc]  = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError(''); setSucc('')
    setLoad(true)
    try {
      if (mode === 'register') {
        await onRegister(name, email, password)
        setSucc('Account created! Logging you in…')
      } else {
        await onLogin(email, password)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoad(false)
    }
  }

  function switchMode(m) {
    setMode(m); setError(''); setSucc(''); setName(''); setPass('')
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.card}>
        <div className={styles.logo}>◈ Coin<span>Coach</span></div>
        <div className={styles.subtitle}>Your personal money buddy 💚</div>

        {/* Mode tabs */}
        <div className={styles.tabs}>
          <button className={`${styles.tab} ${mode==='login'?styles.tabOn:''}`} onClick={()=>switchMode('login')}>Login</button>
          <button className={`${styles.tab} ${mode==='register'?styles.tabOn:''}`} onClick={()=>switchMode('register')}>Register</button>
        </div>

        {/* Context sentence */}
        <div className={styles.contextLine}>
          {mode === 'login'
            ? <>Already have an account? Login below. <button className={styles.switchLink} onClick={()=>switchMode('register')}>No account? Register →</button></>
            : <>New here? Create your account below. <button className={styles.switchLink} onClick={()=>switchMode('login')}>Have an account? Login →</button></>
          }
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          {mode === 'register' && (
            <div className={styles.field}>
              <label>Your name</label>
              <input type="text" placeholder="e.g. Arjun" value={name}
                onChange={e=>setName(e.target.value)} required minLength={2} autoFocus />
            </div>
          )}
          <div className={styles.field}>
            <label>Email</label>
            <input type="email" placeholder="you@example.com" value={email}
              onChange={e=>setEmail(e.target.value)} required
              autoFocus={mode==='login'} />
          </div>
          <div className={styles.field}>
            <label>
              Password
              {mode==='register' && <span className={styles.hint}> — at least 6 characters</span>}
            </label>
            <input type="password" placeholder="••••••••" value={password}
              onChange={e=>setPass(e.target.value)} required minLength={6} />
          </div>

          {error   && <div className={styles.errorBox}>{error}</div>}
          {success && <div className={styles.successBox}>{success}</div>}

          <button className={styles.submitBtn} type="submit" disabled={loading}>
            {loading ? 'Please wait…' : mode==='login' ? 'Login to CoinCoach →' : 'Create my account →'}
          </button>
        </form>

        <div className={styles.footer}>
          🔒 Data stored securely · Log in from any device
        </div>
      </div>
    </div>
  )
}
