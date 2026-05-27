require('dotenv').config()
const pool = require('./pool')

async function migrate() {
  const client = await pool.connect()
  try {
    console.log('🔄 Running migrations...')
    await client.query('BEGIN')

    // Users table
    await client.query(`
      CREATE TABLE IF NOT EXISTS users (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name        VARCHAR(100) NOT NULL,
        email       VARCHAR(255) UNIQUE NOT NULL,
        password    VARCHAR(255) NOT NULL,
        created_at  TIMESTAMPTZ DEFAULT NOW(),
        updated_at  TIMESTAMPTZ DEFAULT NOW()
      )
    `)

    // Entries table — one row per user per date
    await client.query(`
      CREATE TABLE IF NOT EXISTS entries (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        entry_date  DATE NOT NULL,
        income      NUMERIC(12,2) DEFAULT 0,
        expenses    JSONB DEFAULT '{}',
        note        TEXT DEFAULT '',
        corrected   BOOLEAN DEFAULT false,
        created_at  TIMESTAMPTZ DEFAULT NOW(),
        updated_at  TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(user_id, entry_date)
      )
    `)

    // Index for fast per-user queries
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_entries_user_date
      ON entries(user_id, entry_date DESC)
    `)

    // Index for monthly range queries
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_entries_user_month
      ON entries(user_id, DATE_TRUNC('month', entry_date))
    `)

    // Refresh token table
    await client.query(`
      CREATE TABLE IF NOT EXISTS refresh_tokens (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token       VARCHAR(512) UNIQUE NOT NULL,
        expires_at  TIMESTAMPTZ NOT NULL,
        created_at  TIMESTAMPTZ DEFAULT NOW()
      )
    `)

    await client.query('COMMIT')
    console.log('✅ Migrations complete')
  } catch (err) {
    await client.query('ROLLBACK')
    console.error('❌ Migration failed:', err.message)
    throw err
  } finally {
    client.release()
    await pool.end()
  }
}

migrate().catch(err => {
  console.error(err)
  process.exit(1)
})
