import React, { useEffect, useRef, useState } from 'react'
import styles from '../styles/LandingPage.module.css'

const DEMO_MESSAGES = [
  { role:'bot',  html:`Hey! 👋 I'm <strong>CoinCoach</strong>.<br/><br/><span class="ds">I'll help you</span><ul><li>Track daily income and spending</li><li>Build monthly and yearly totals automatically</li><li>Give smart, personalised saving tips</li></ul>` },
  { role:'user', html:`Today I received ₹500 and spent ₹200 on petrol and ₹150 on food` },
  { role:'bot',  html:`<span class="ds">Logged for today</span><ul><li>Income: <strong>+₹500</strong></li><li>Petrol: <strong>₹200</strong> → Travelling</li><li>Food: <strong>₹150</strong> → Eating outside</li><li>Balance: <strong>₹150 saved ✓</strong></li></ul><span class="ds">Tip</span><ul><li>Petrol is 40% of today's income — consider carpooling twice a week to save ₹800/month</li></ul><span class="ds">Motivation</span><ul><li>₹150 saved today = ₹4,500 by month end if you keep this up 🔥</li></ul>` },
  { role:'user', html:`Show my month so far` },
  { role:'bot',  html:`<span class="ds">May 2025</span><ul><li>Received: <strong>₹3,200</strong></li><li>Spent: <strong>₹2,100</strong></li><li>Saved: <strong>₹1,100 (34.4%)</strong> 🎉</li></ul><span class="ds">Motivation</span><ul><li>You're saving ₹1,100 more than the average person your age. That's real progress.</li></ul>` },
]

function useTicker(target, suffix='', duration=1500) {
  const [val, setVal] = useState(0)
  const started = useRef(false)
  function start() {
    if (started.current) return
    started.current = true
    const s = Date.now()
    const tick = () => {
      const p = Math.min(1, (Date.now()-s)/duration)
      setVal(Math.round(target*p))
      if (p < 1) requestAnimationFrame(tick)
    }
    tick()
  }
  return [val+suffix, start]
}

export default function LandingPage({ onEnter }) {
  const bgRef    = useRef(null)
  const coinRef  = useRef(null)
  const demoRef  = useRef(null)
  const statsRef = useRef(null)
  const mousePos = useRef({ x: 0, y: 0 })
  const [demoMsgs, setDemoMsgs] = useState([])

  const [s1, startS1] = useTicker(2400, '', 1400)
  const [s2, startS2] = useTicker(34, '%', 1600)
  const [s3, startS3] = useTicker(1800, '', 1500)
  const [s4, startS4] = useTicker(9200, '', 1700)

  // Set landing scroll class
  useEffect(() => {
    document.documentElement.classList.add('landing')
    document.documentElement.classList.remove('app-view')
    return () => document.documentElement.classList.remove('landing')
  }, [])

  // Background particles
  useEffect(() => {
    const canvas = bgRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let raf
    function resize() {
      canvas.width  = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)
    const pts = Array.from({ length: 55 }, () => ({
      x: Math.random()*canvas.width, y: Math.random()*canvas.height,
      vx: (Math.random()-.5)*.3, vy: (Math.random()-.5)*.3,
      r: Math.random()*1.4+.3, o: Math.random()*.35+.08
    }))
    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      const mx = mousePos.current.x, my = mousePos.current.y
      pts.forEach(p => {
        p.x += p.vx; p.y += p.vy
        if (p.x < 0) p.x = canvas.width; if (p.x > canvas.width) p.x = 0
        if (p.y < 0) p.y = canvas.height; if (p.y > canvas.height) p.y = 0
        const d = Math.hypot(p.x-mx, p.y-my), g = Math.max(0, 1-d/200)
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r*(1+g), 0, Math.PI*2)
        ctx.fillStyle = `rgba(163,230,53,${p.o+g*.28})`; ctx.fill()
      })
      pts.forEach((a,i) => pts.slice(i+1).forEach(b => {
        const d = Math.hypot(a.x-b.x, a.y-b.y)
        if (d < 95) {
          ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y)
          ctx.strokeStyle = `rgba(163,230,53,${.1*(1-d/95)})`
          ctx.lineWidth = .5; ctx.stroke()
        }
      }))
      raf = requestAnimationFrame(draw)
    }
    draw()
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize) }
  }, [])

  useEffect(() => {
    const fn = e => { mousePos.current = { x: e.clientX, y: e.clientY } }
    window.addEventListener('mousemove', fn)
    return () => window.removeEventListener('mousemove', fn)
  }, [])

  // 3D coins
  useEffect(() => {
    const canvas = coinRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const W = 900, H = 340
    let raf, t = 0
    const coins = [
      {x:130,y:180,ry:0,dry:.022,rz:0,drz:.003,size:62,color:'#a3e635',label:'₹',phase:0,bv:.018},
      {x:270,y:160,ry:0,dry:.018,rz:0,drz:.005,size:48,color:'#fbbf24',label:'₹',phase:1,bv:.014},
      {x:420,y:188,ry:0,dry:.025,rz:0,drz:.004,size:78,color:'#a3e635',label:'₹',phase:.5,bv:.021},
      {x:568,y:158,ry:0,dry:.016,rz:0,drz:.006,size:54,color:'#4ade80',label:'₹',phase:1.5,bv:.016},
      {x:708,y:178,ry:0,dry:.020,rz:0,drz:.003,size:60,color:'#fbbf24',label:'₹',phase:2,bv:.019},
    ]
    let mLocal = {x:W/2,y:H/2}
    canvas.addEventListener('mousemove', e => {
      const r = canvas.getBoundingClientRect()
      mLocal = {x:e.clientX-r.left, y:e.clientY-r.top}
    })
    function lighten(hex,a){const n=parseInt(hex.slice(1),16);return`rgb(${Math.min(255,(n>>16)+Math.round(255*a))},${Math.min(255,((n>>8)&255)+Math.round(255*a))},${Math.min(255,(n&255)+Math.round(255*a))})`}
    function darken(hex,a){const n=parseInt(hex.slice(1),16);return`rgb(${Math.max(0,(n>>16)-Math.round(255*a))},${Math.max(0,((n>>8)&255)-Math.round(255*a))},${Math.max(0,(n&255)-Math.round(255*a))})`}
    function drawCoin(c) {
      const bOff = Math.sin(c.phase + t*c.bv)*14
      const mx=(mLocal.x-W/2)/W, my=(mLocal.y-H/2)/H
      const px=c.x+mx*24, py=c.y+bOff+my*10
      const rx3=c.size*Math.abs(Math.cos(c.ry)), ry3=c.size
      ctx.save(); ctx.translate(px, py+c.size*.5); ctx.scale(1,.2)
      ctx.beginPath(); ctx.ellipse(0,0,rx3*.8,ry3*.5,c.rz,0,Math.PI*2)
      ctx.fillStyle='rgba(0,0,0,.18)'; ctx.fill(); ctx.restore()
      ctx.save(); ctx.translate(px,py); ctx.rotate(c.rz)
      if(Math.cos(c.ry)>0){
        ctx.beginPath(); ctx.ellipse(3,0,rx3,ry3,0,0,Math.PI*2)
        ctx.fillStyle=darken(c.color,.28); ctx.fill()
      }
      ctx.beginPath(); ctx.ellipse(0,0,Math.max(rx3,2),ry3,0,0,Math.PI*2)
      const g=ctx.createRadialGradient(-rx3*.3,-ry3*.3,0,0,0,ry3)
      g.addColorStop(0,lighten(c.color,.28)); g.addColorStop(.6,c.color); g.addColorStop(1,darken(c.color,.22))
      ctx.fillStyle=g; ctx.fill()
      ctx.beginPath(); ctx.ellipse(0,0,rx3*.76,ry3*.76,0,0,Math.PI*2)
      ctx.strokeStyle=darken(c.color,.12); ctx.lineWidth=1.5; ctx.stroke()
      if(rx3>12){
        ctx.fillStyle=darken(c.color,.38); ctx.font=`600 ${Math.round(ry3*.48)}px DM Sans,sans-serif`
        ctx.textAlign='center'; ctx.textBaseline='middle'
        ctx.globalAlpha=Math.min(1,rx3/16)
        ctx.fillText(c.label,0,0); ctx.globalAlpha=1
      }
      ctx.beginPath(); ctx.ellipse(-rx3*.2,-ry3*.25,rx3*.28,ry3*.14,-.4,0,Math.PI*2)
      ctx.fillStyle='rgba(255,255,255,.15)'; ctx.fill()
      ctx.restore()
    }
    function loop() {
      ctx.clearRect(0,0,W,H); t+=.016
      coins.forEach(c => { c.ry+=c.dry; c.rz+=c.drz*.3; drawCoin(c) })
      raf = requestAnimationFrame(loop)
    }
    loop()
    return () => cancelAnimationFrame(raf)
  }, [])

  // Stats observer
  useEffect(() => {
    const el = statsRef.current; if(!el) return
    const obs = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) {
        startS1(); startS2(); startS3(); startS4(); obs.disconnect()
      }
    }, { threshold: .3 })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  // Demo chat auto-play
  useEffect(() => {
    const el = demoRef.current; if (!el) return
    let idx = 0
    function addMsg() {
      if (idx >= DEMO_MESSAGES.length) return
      const m = DEMO_MESSAGES[idx++]
      setDemoMsgs(prev => [...prev, m])
      setTimeout(addMsg, m.role==='user' ? 1000 : 1800)
    }
    const obs = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) { setTimeout(addMsg, 400); obs.disconnect() }
    }, { threshold: .2 })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  return (
    <div className={styles.root}>
      <canvas ref={bgRef} className={styles.bgCanvas} />

      {/* NAV — clean, no broken links */}
      <nav className={styles.nav}>
        <div className={styles.logo}>◈ Coin<em>Coach</em></div>
        <button className={styles.navCta} onClick={onEnter}>Start Free →</button>
      </nav>

      {/* HERO */}
      <section className={styles.hero}>
        <div className={styles.eyebrow}>
          <span className={styles.eyebrowDot}/>
          AI-Powered · Cloud Storage · Private
        </div>
        <h1 className={styles.heroTitle}>
          Your money,<br/><em>finally makes sense</em>
        </h1>
        <p className={styles.heroSub}>
          Just tell CoinCoach what you received and spent — in plain words.
          It tracks everything, builds your monthly picture automatically, and
          gives you real tips to save more.
        </p>
        <div className={styles.heroBtns}>
          <button className={styles.btnPrimary} onClick={onEnter}>
            Start Tracking Free
          </button>
          <button className={styles.btnGhost}
            onClick={() => demoRef.current?.scrollIntoView({behavior:'smooth'})}>
            See how it works ↓
          </button>
        </div>
        <button
          className={styles.scrollBtn}
          onClick={() => document.querySelector('.' + styles.coinSection)?.scrollIntoView({behavior:'smooth'})}
          aria-label="Scroll down"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 5v14M5 12l7 7 7-7"/></svg>
        </button>
      </section>

      {/* 3D COINS */}
      <section className={styles.coinSection}>
        <canvas ref={coinRef} width="900" height="340" className={styles.coinCanvas}/>
      </section>

      {/* STATS */}
      <div className={styles.stats} ref={statsRef}>
        {[
          [s1, 'Expenses tracked daily'],
          [s2, 'Average savings increase'],
          [s3, 'Story entries understood'],
          [s4, 'Motivational nudges sent'],
        ].map(([num, label]) => (
          <div key={label} className={styles.stat}>
            <div className={styles.statNum}>{num}</div>
            <div className={styles.statLbl}>{label}</div>
          </div>
        ))}
      </div>

      {/* FEATURES — universal, no student/employee split */}
      <section className={styles.features}>
        <div className={styles.sectionTag}>Everything you need</div>
        <h2 className={styles.sectionTitle}>Built for real life,<br/>not spreadsheets</h2>
        <p className={styles.sectionSub}>
          No forms. No manual entry. Just talk to CoinCoach like a friend
          and watch your financial picture build itself.
        </p>
        <div className={styles.featGrid}>
          {[
            {icon:'📖', title:'Story mode',           desc:'Say "Today I got ₹500 and spent ₹200 on petrol" — we extract every amount and category automatically.', tag:'Natural language'},
            {icon:'📅', title:'Day → Month → Year',   desc:'Every entry rolls up automatically. See today, this week, this month, this year — all in one place.', tag:'Auto tracking'},
            {icon:'🔧', title:'Instant corrections',   desc:'Made a mistake? Just say "petrol was ₹300 not ₹200" and it replaces — no double counting ever.', tag:'Smart corrections'},
            {icon:'📊', title:'Live breakdown chart',  desc:'Your spending breakdown appears as a donut chart in real time as you chat — no charting needed.', tag:'Visual insights'},
            {icon:'🎯', title:'Personalised saving plan', desc:'Get a 50/30/20 budget plan based on your actual income and spending, with a real deficit or surplus shown.', tag:'Your plan'},
            {icon:'✨', title:'Meaningful tips daily', desc:'Tips based on your real numbers — not generic advice. If petrol is 40% of income, we tell you exactly how to cut it.', tag:'Smart tips'},
          ].map((f,i) => (
            <div key={i} className={styles.featCard}
              onMouseMove={e=>{
                const r=e.currentTarget.getBoundingClientRect()
                const x=e.clientX-r.left, y=e.clientY-r.top
                e.currentTarget.style.transform=`translateY(-3px) rotateX(${(y/r.height-.5)*7}deg) rotateY(${-(x/r.width-.5)*7}deg)`
                e.currentTarget.style.setProperty('--mx',`${(x/r.width*100).toFixed(0)}%`)
                e.currentTarget.style.setProperty('--my',`${(y/r.height*100).toFixed(0)}%`)
              }}
              onMouseLeave={e=>{ e.currentTarget.style.transform='translateY(0)' }}
            >
              <div className={styles.featIcon}>{f.icon}</div>
              <div className={styles.featTitle}>{f.title}</div>
              <div className={styles.featDesc}>{f.desc}</div>
              <span className={styles.featTag}>{f.tag}</span>
            </div>
          ))}
        </div>
      </section>

      {/* HOW IT WORKS — replaces the student/employee section */}
      <section className={styles.how}>
        <div className={styles.howInner}>
          <div className={styles.sectionTag}>How it works</div>
          <h2 className={styles.sectionTitle}>Three steps to financial clarity</h2>
          <div className={styles.howSteps}>
            {[
              { num:'01', title:'Tell me your day', desc:'Type naturally — "Today I got ₹2,000 and spent ₹500 on groceries and ₹200 on petrol." No forms, no dropdowns.' },
              { num:'02', title:'Watch it add up',  desc:'Every entry flows into your daily, weekly, monthly and yearly totals automatically. Corrections replace — never double count.' },
              { num:'03', title:'Get real tips',    desc:'CoinCoach analyses your actual numbers and gives specific, actionable tips — not generic advice. Meaningful motivation every day.' },
            ].map(s => (
              <div key={s.num} className={styles.howStep}>
                <div className={styles.howNum}>{s.num}</div>
                <div className={styles.howTitle}>{s.title}</div>
                <div className={styles.howDesc}>{s.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* DEMO CHAT */}
      <section className={styles.demo} ref={demoRef}>
        <div className={styles.demoHeader}>
          <div className={styles.sectionTag}>See it in action</div>
          <h2 className={styles.sectionTitle}>Just talk. We do the rest.</h2>
        </div>
        <div className={styles.demoWindow}>
          <div className={styles.demoBar}>
            <div className={styles.dot} style={{background:'#f87171'}}/>
            <div className={styles.dot} style={{background:'#fbbf24'}}/>
            <div className={styles.dot} style={{background:'#4ade80'}}/>
            <span className={styles.demoTitle}>CoinCoach · AI Budget Advisor</span>
          </div>
          <div className={styles.demoBody}>
            {demoMsgs.map((m,i) => (
              <div key={i} className={`${styles.demoMsg} ${m.role==='user'?styles.demoUser:''}`}>
                {m.role==='bot' && <div className={`${styles.demoAv} ${styles.demoAvBot}`}>◈</div>}
                <div className={`${styles.demoBub} ${m.role==='user'?styles.demoBubUser:styles.demoBubBot}`}
                  dangerouslySetInnerHTML={{__html:m.html}}/>
                {m.role==='user' && <div className={`${styles.demoAv} ${styles.demoAvUser}`}>U</div>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className={styles.ctaSection}>
        <div className={styles.ctaGlow}/>
        <h2 className={styles.ctaTitle}>Start saving smarter<br/><em>today</em></h2>
        <p className={styles.ctaSub}>
          30 seconds to register. No credit card. Your data stored securely in the cloud.
        </p>
        <button className={styles.btnPrimary} style={{fontSize:'15px',padding:'14px 40px'}} onClick={onEnter}>
          Open CoinCoach →
        </button>
      </section>

      <footer className={styles.footer}>
        <div className={styles.logo} style={{fontSize:'16px'}}>◈ Coin<em>Coach</em></div>
        <div>Your money. Your data. Your future.</div>
        <div>🔒 Secured with JWT + Neon PostgreSQL</div>
      </footer>
    </div>
  )
}
