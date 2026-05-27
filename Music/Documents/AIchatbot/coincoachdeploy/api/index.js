// Vercel entry point — proxies all /api/* to the Express app
require('dotenv').config({ path: require('path').join(__dirname, '../backend/.env') })
module.exports = require('../backend/server_vercel')
