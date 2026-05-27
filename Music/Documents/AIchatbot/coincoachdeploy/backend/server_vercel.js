/**
 * server_vercel.js — Express app exported for Vercel serverless
 * Used by /api/index.js (Vercel) and server.js (local dev)
 */
const express      = require('express')
const cors         = require('cors')
const helmet       = require('helmet')
const cookieParser = require('cookie-parser')
const rateLimit    = require('express-rate-limit')

const app = express()

app.use(helmet({ contentSecurityPolicy: false }))
app.use(express.json({ limit: '40kb' }))
app.use(cookieParser())

const allowedOrigins = [
  'http://localhost:5173',
  'http://localhost:4173',
  process.env.FRONTEND_URL,
  /\.vercel\.app$/,   // allow all vercel preview URLs
].filter(Boolean)

app.use(cors({
  origin: (origin, cb) => {
    if (!origin) return cb(null, true) // allow server-to-server
    const allowed = allowedOrigins.some(o =>
      o instanceof RegExp ? o.test(origin) : o === origin
    )
    if (allowed) return cb(null, true)
    // In dev allow everything
    if (process.env.NODE_ENV !== 'production') return cb(null, true)
    cb(new Error('Not allowed by CORS'))
  },
  credentials: true,
  methods: ['GET','POST','PUT','DELETE','OPTIONS'],
  allowedHeaders: ['Content-Type','Authorization'],
}))

app.use(rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 200,
  standardHeaders: true,
  legacyHeaders: false,
}))

app.use('/api/auth',    require('./routes/auth'))
app.use('/api/entries', require('./routes/entries'))
app.use('/api/chat',    require('./routes/chat'))

app.get('/api/health', (_, res) => res.json({
  status: 'ok',
  time: new Date().toISOString(),
  db: 'neon-postgresql',
  env: process.env.NODE_ENV,
}))

app.use((err, req, res, next) => {
  console.error('Unhandled error:', err.message)
  res.status(500).json({ error: 'Something went wrong on the server' })
})

module.exports = app
