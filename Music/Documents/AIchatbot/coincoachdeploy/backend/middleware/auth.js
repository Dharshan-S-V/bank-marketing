const jwt  = require('jsonwebtoken')
const pool = require('../db/pool')

module.exports = async function authMiddleware(req, res, next) {
  try {
    // Accept token from Authorization header OR httpOnly cookie
    let token = null

    const authHeader = req.headers.authorization
    if (authHeader && authHeader.startsWith('Bearer ')) {
      token = authHeader.slice(7)
    } else if (req.cookies?.access_token) {
      token = req.cookies.access_token
    }

    if (!token) {
      return res.status(401).json({ error: 'Authentication required' })
    }

    const decoded = jwt.verify(token, process.env.JWT_SECRET)

    // Verify user still exists
    const result = await pool.query(
      'SELECT id, name, email FROM users WHERE id = $1',
      [decoded.userId]
    )

    if (!result.rows.length) {
      return res.status(401).json({ error: 'User not found' })
    }

    req.user = result.rows[0]
    next()
  } catch (err) {
    if (err.name === 'TokenExpiredError') {
      return res.status(401).json({ error: 'Token expired', code: 'TOKEN_EXPIRED' })
    }
    return res.status(401).json({ error: 'Invalid token' })
  }
}
