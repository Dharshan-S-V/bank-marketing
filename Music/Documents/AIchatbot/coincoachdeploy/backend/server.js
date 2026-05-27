require('dotenv').config()
const app  = require('./server_vercel')
const PORT = process.env.PORT || 3001

// Auto-run migrations on startup
require('./db/migrate_inline')

app.listen(PORT, () => {
  console.log(`✅ CoinCoach API → http://localhost:${PORT}`)
  console.log(`🌱 Environment  → ${process.env.NODE_ENV || 'development'}`)
})
