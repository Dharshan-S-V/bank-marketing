const { Pool } = require('pg')

// Strip channel_binding if present (pg driver doesn't support it)
const rawUrl = process.env.DATABASE_URL || ''
const cleanUrl = rawUrl
  .replace('&channel_binding=require', '')
  .replace('&channel_binding=disable', '')
  .replace('?channel_binding=require&', '?')
  .replace('?channel_binding=require', '')

const pool = new Pool({
  connectionString: cleanUrl,
  ssl: {
    rejectUnauthorized: false,
  },
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 10000,
})

pool.on('error', (err) => {
  console.error('⚠️  Unexpected DB client error:', err.message)
})

// Test on startup
async function testConnection() {
  try {
    const client = await pool.connect()
    await client.query('SELECT 1')
    client.release()
    console.log('✅ Neon PostgreSQL connected')
  } catch (err) {
    console.error('❌ DB connection failed:', err.message)
    console.error('   Check DATABASE_URL in .env')
  }
}
testConnection()

module.exports = pool
