import type { TripPlanResponse } from '@/types'

export function planToMarkdown(plan: TripPlanResponse): string {
  const lines = [`# ${plan.destination}行程`, '', plan.summary, '']

  for (const day of plan.days) {
    lines.push(`## 第 ${day.day} 天 · ${day.date} · ${day.title}`, '')
    lines.push(`- 天气：${day.weather}`)
    lines.push(`- 预算：${day.daily_budget}`)
    lines.push(`- 交通：${day.transport}`, '')

    for (const item of day.items) {
      lines.push(`### ${item.time} ${item.place}`)
      lines.push(item.activity)
      lines.push(`- 费用：${item.estimated_cost}`)
      lines.push(`- 预约：${item.booking_hint}`)
      lines.push(`- 来源：${item.source_hint}`, '')
    }

    if (day.notes.length > 0) {
      lines.push('注意事项：')
      for (const note of day.notes) lines.push(`- ${note}`)
      lines.push('')
    }
  }

  if (plan.tips.length > 0) {
    lines.push('## 出发前提醒', '')
    for (const tip of plan.tips) lines.push(`- ${tip}`)
    lines.push('')
  }

  lines.push('## 免责声明', '', plan.disclaimer)
  return lines.join('\n')
}

export function demo(): void {
  const markdown = planToMarkdown({
    trip_id: '1',
    destination: '北京',
    summary: '一天北京行程。',
    days: [
      {
        day: 1,
        date: '2026-10-01',
        title: '故宫周边',
        weather: '以实时天气为准',
        daily_budget: '约 ¥300',
        transport: '地铁和步行',
        notes: ['提前预约。'],
        items: [
          {
            time: '09:00',
            place: '故宫',
            activity: '参观中轴线。',
            estimated_cost: '需查询官方渠道',
            booking_hint: '提前预约',
            source_hint: '官方信息为准',
          },
        ],
      },
    ],
    tips: ['带身份证。'],
    disclaimer: '请以实际开放信息为准。',
  })

  console.assert(markdown.includes('# 北京行程'))
  console.assert(markdown.includes('09:00 故宫'))
}
