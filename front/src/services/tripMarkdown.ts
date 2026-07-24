import type {
  TransportDataQuality,
  TransportLeg,
  TransportMode,
  TransportOption,
  TripPlanResponse,
} from '@/types'

const modeLabels: Record<TransportMode, string> = {
  flight: '航班',
  rail: '铁路',
  drive: '自驾',
}

const qualityLabels: Record<TransportDataQuality, string> = {
  live: '实时查询',
  provider_live: '供应商实时',
  estimate: '规划估算',
}

function transportTime(value: string | null): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '时间待确认'
}

function transportPrice(option: TransportOption): string {
  if (option.total_price) return `${option.currency} ${option.total_price}`.trim()
  return option.estimated_price_range || (option.fare_details.length ? '按票种核算' : '费用待核算')
}

function appendTransportLeg(lines: string[], label: string, leg: TransportLeg): void {
  lines.push(`#### ${label}`, '')
  lines.push(`- 时间：${transportTime(leg.departure_at)} → ${transportTime(leg.arrival_at)}`)
  lines.push(`- 中转：${leg.transfer_count} 次中转`)
  if (leg.segments.length) {
    lines.push('- 班次：')
    for (const segment of leg.segments) {
      const service = [segment.carrier, segment.service_number].filter(Boolean).join(' ') || '班次待确认'
      const terminals = `${segment.from_terminal || '起点待确认'} → ${segment.to_terminal || '终点待确认'}`
      lines.push(`  - ${service} · ${transportTime(segment.departure_at)} → ${transportTime(segment.arrival_at)} · ${terminals}`)
    }
  } else {
    lines.push('- 班次：待确认')
  }
  lines.push('')
}

export function planToMarkdown(plan: TripPlanResponse): string {
  const lines = [`# ${plan.destination}行程`, '', plan.summary, '']

  const transport = plan.intercity_transport
  if (transport) {
    lines.push('## 往返交通建议', '')
    if (transport.recommendation_reason) lines.push(`推荐理由：${transport.recommendation_reason}`, '')

    const options = [...transport.options].sort((left, right) =>
      Number(right.id === transport.recommended_option_id) - Number(left.id === transport.recommended_option_id),
    )
    for (const option of options) {
      const recommended = option.id === transport.recommended_option_id ? ' · 推荐' : ''
      lines.push(`### ${modeLabels[option.mode]}${recommended}`, '')
      lines.push(`- 价格：${transportPrice(option)}`)
      if (option.fare_details.length) lines.push(`- 票价明细：${option.fare_details.join('；')}`)
      lines.push(`- 数据质量：${qualityLabels[option.data_quality]}`)
      lines.push(`- 来源：${option.provider}`)
      lines.push(`- 预订提示：${option.booking_hint || '预订前请核实供应商信息。'}`, '')
      appendTransportLeg(lines, '去程', option.outbound)
      appendTransportLeg(lines, '返程', option.return_leg)
    }

    lines.push(`查询时间：${transportTime(transport.searched_at)}`, '')
    if (transport.warnings.length) {
      lines.push('交通提示：')
      for (const warning of transport.warnings) lines.push(`- ${warning}`)
      lines.push('')
    }
  }

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
  const plan: TripPlanResponse = {
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
    intercity_transport: {
      origin: '上海',
      destination: '北京',
      recommended_option_id: 'rail-g25',
      recommendation_reason: '高铁时间稳定，市区到站更方便。',
      options: [
        {
          id: 'rail-g25',
          mode: 'rail',
          provider: '聚合数据',
          data_quality: 'provider_live',
          total_price: '',
          currency: 'CNY',
          estimated_price_range: '',
          fare_details: ['二等座 ¥662'],
          outbound: {
            direction: 'outbound',
            departure_at: '2026-10-01T07:00:00+08:00',
            arrival_at: '2026-10-01T11:38:00+08:00',
            duration_minutes: 278,
            transfer_count: 0,
            segments: [
              {
                service_number: 'G25',
                carrier: '中国铁路',
                departure_at: '2026-10-01T07:00:00+08:00',
                arrival_at: '2026-10-01T11:38:00+08:00',
                from_terminal: '上海虹桥站',
                to_terminal: '北京南站',
              },
            ],
          },
          return_leg: {
            direction: 'return',
            departure_at: '2026-10-01T18:00:00+08:00',
            arrival_at: '2026-10-01T22:43:00+08:00',
            duration_minutes: 283,
            transfer_count: 0,
            segments: [
              {
                service_number: 'G26',
                carrier: '中国铁路',
                departure_at: '2026-10-01T18:00:00+08:00',
                arrival_at: '2026-10-01T22:43:00+08:00',
                from_terminal: '北京南站',
                to_terminal: '上海虹桥站',
              },
            ],
          },
          booking_hint: '请在铁路官方渠道核实余票后预订。',
          source_url: '',
        },
      ],
      destination_ready_at: '2026-10-01T12:23:00+08:00',
      destination_depart_by: '2026-10-01T17:15:00+08:00',
      searched_at: '2026-07-23T10:00:00+08:00',
      warnings: ['余票与票价可能随时变化。'],
    },
  }

  const markdown = planToMarkdown(plan)
  const { intercity_transport: _, ...oldPlan } = plan
  const oldMarkdown = planToMarkdown(oldPlan)

  console.assert(markdown.includes('# 北京行程'))
  console.assert(markdown.includes('09:00 故宫'))
  console.assert(markdown.includes('## 往返交通建议'))
  console.assert(markdown.includes('G25'))
  console.assert(markdown.includes('G26'))
  console.assert(markdown.includes('上海虹桥站'))
  console.assert(markdown.includes('二等座 ¥662'))
  console.assert(markdown.includes('0 次中转'))
  console.assert(markdown.includes('供应商实时'))
  console.assert(markdown.includes('聚合数据'))
  console.assert(markdown.includes('查询时间'))
  console.assert(markdown.includes('铁路官方渠道'))
  console.assert(markdown.includes('余票与票价可能随时变化'))
  console.assert(!oldMarkdown.includes('## 往返交通建议'))
  console.assert(oldMarkdown.includes('09:00 故宫'))
}
