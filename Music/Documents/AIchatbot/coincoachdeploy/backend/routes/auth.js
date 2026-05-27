const router  = require('express').Router()
const bcrypt  = require('bcryptjs')
const jwt     = require('jsonwebtoken')
const { body, validationResult } = require('express-validator')
const pool    = require('../db/pool')

const ROUNDS = parseInt(process.env.BCRYPT_ROUNDS) || 12

function generateToken(userId) {
  return jwt.sign({ userId }, process.env.JWT_SECRET, {
    expiresIn: process.env.JWT_EXPIRES_IN || '7d'
  })
}

function cookieOpts() {
  return {
    httpOnly: true,
    secure:   process.env.NODE_ENV === 'production',
    sameSite: process.env.NODE_ENV === 'production' ? 'none' : 'lax',
    maxAge:   7 * 24 * 60 * 60 * 1000,
  }
}

// ── REGISTER ─────────────────────────────────────────────
router.post('/register',
  [
    body('name').trim().isLength({ min:2, max:100 }).withMessage('Name must be 2–100 characters'),
    body('email').trim().isEmail().normalizeEmail().withMessage('Enter a valid email address'),
    body('password').isLength({ min:6 }).withMessage('Password must be at least 6 characters'),
  ],
  async (req, res) => {
    const errors = validationResult(req)
    if (!errors.isEmpty()) {
      return res.status(400).json({ error: errors.array()[0].msg })
    }

    const { name, email, password } = req.body

    try {
      // Check duplicate email
      const existing = await pool.query(
        'SELECT id FROM users WHERE email = $1', [email]
      )
      if (existing.rows.length) {
        return res.status(409).json({
          error: 'This email is already registered. Please login instead.'
        })
      }

      const hash = await bcrypt.hash(password, ROUNDS)
      const result = await pool.query(
        `INSERT INTO users (name, email, password)
         VALUES ($1, $2, $3)
         RETURNING id, name, email, created_at`,
        [name, email, hash]
      )

      const user  = result.rows[0]
      const token = generateToken(user.id)

      res.cookie('access_token', token, cookieOpts())
      res.status(201).json({
        message: `Welcome to CoinCoach, ${user.name}!`,
        token,
        user: { id: user.id, name: user.name, email: user.email }
      })
    } catch (err) {
      console.error('Register error:', err.message)
      // Return actual DB error in dev so user can debug
      const isDev = process.env.NODE_ENV !== 'production'
      res.status(500).json({
        error: isDev
          ? `Database error: ${err.message}`
          : 'Registration failed. Please try again.'
      })
    }
  }
)

// ── LOGIN ─────────────────────────────────────────────────
router.post('/login',
  [
    body('email').trim().isEmail().normalizeEmail().withMessage('Enter a valid email address'),
    body('password').notEmpty().withMessage('Password is required'),
  ],
  async (req, res) => {
    const errors = validationResult(req)
    if (!errors.isEmpty()) {
      return res.status(400).json({ error: errors.array()[0].msg })
    }

    const { email, password } = req.body

    try {
      const result = await pool.query(
        'SELECT id, name, email, password FROM users WHERE email = $1',
        [email]
      )

      if (!result.rows.length) {
        return res.status(401).json({
          error: 'No account found with this email. Please register first.'
        })
      }

      const user  = result.rows[0]
      const match = await bcrypt.compare(password, user.password)
      if (!match) {
        return res.status(401).json({ error: 'Incorrect password. Please try again.' })
      }

      const token = generateToken(user.id)
      res.cookie('access_token', token, cookieOpts())
      res.json({
        message: `Welcome back, ${user.name}!`,
        token,
        user: { id: user.id, name: user.name, email: user.email }
      })
    } catch (err) {
      console.error('Login error:', err.message)
      const isDev = process.env.NODE_ENV !== 'production'
      res.status(500).json({
        error: isDev
          ? `Database error: ${err.message}`
          : 'Login failed. Please try again.'
      })
    }
  }
)

// ── LOGOUT ───────────────────────────────────────────────
router.post('/logout', (req, res) => {
  res.clearCookie('access_token')
  res.json({ message: 'Logged out successfully' })
})

// ── ME ────────────────────────────────────────────────────
router.get('/me', require('../middleware/auth'), (req, res) => {
  res.json({ user: req.user })
})

module.exports = router
