import { sendWeChatCard } from '../../services/wechat.js'
import { sendEmailHtml } from '../../services/email.js'
import { sendLarkCard } from '../../services/lark.js'
import { sendPushPlus } from '../../services/pushplus.js'

export async function distribute(item: { title: string; html: string }, target: { channel: 'wechat' | 'email' | 'lark' | 'pushplus'; address: string }) {
  if (target.channel === 'wechat') {
    return sendWeChatCard(target.address, item.title, item.html)
  }
  if (target.channel === 'lark') {
    return sendLarkCard(target.address, item.title, item.html)
  }
  if (target.channel === 'pushplus') {
    return sendPushPlus(target.address, item.title, item.html)
  }
  return sendEmailHtml(target.address, item.title, item.html)
}
