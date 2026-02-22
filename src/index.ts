import dotenv from 'dotenv'
dotenv.config()
import { logger } from './utils/logger.js'
import { scheduleWeekly } from './config/cron.js'
import { runWeeklyNewsletter } from './jobs/weeklyNewsletter.js'

async function main() {
  logger.info('AutoNewsletter booting')
  scheduleWeekly(async () => {
    await runWeeklyNewsletter()
  })
  const enableImmediate = process.env.IMMEDIATE_RUN === '1'
  if (enableImmediate) {
    await runWeeklyNewsletter()
  }
  logger.info('Scheduler ready')
}

main().catch((err) => {
  logger.error({ err }, 'Fatal error')
  process.exit(1)
})

