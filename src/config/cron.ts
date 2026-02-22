import cron from 'node-cron'
import { logger } from '../utils/logger.js'

export function scheduleWeekly(handler: () => Promise<void>) {
  const expr = process.env.WEEKLY_CRON || '0 9 * * 3'
  cron.schedule(expr, async () => {
    try {
      logger.info('Weekly job started')
      await handler()
      logger.info('Weekly job finished')
    } catch (err) {
      logger.error({ err }, 'Weekly job failed')
    }
  })
}

