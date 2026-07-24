<script setup lang="ts">
import { computed } from 'vue'

import type { TransportDataQuality, TransportMode, TransportOption, TripPlanResponse } from '@/types'

const props = defineProps<{ plan: TripPlanResponse }>()

const transportPlan = computed(() => props.plan.intercity_transport ?? null)
const transportOptions = computed(() => {
  const recommendedId = transportPlan.value?.recommended_option_id
  return [...(transportPlan.value?.options ?? [])].sort((left, right) =>
    Number(right.id === recommendedId) - Number(left.id === recommendedId),
  )
})

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

function formatProviderDateTime(value: string | null): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '时间待确认'
}

function formatSearchedAt(value: string): string {
  const date = new Date(value)
  if (!value || Number.isNaN(date.getTime())) return '查询时间未知'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).format(date)
}

function priceText(option: TransportOption): string {
  if (option.total_price) return `${option.currency} ${option.total_price}`
  return option.estimated_price_range || (option.fare_details.length ? '按票种与旅客人数核算' : '费用待核算')
}
</script>

<template>
  <div class="space-y-4">
    <div class="grid gap-4 rounded-xl bg-[#f9e79f] p-4 md:grid-cols-[220px_minmax(0,1fr)] md:items-center">
      <div>
        <p class="text-xs font-semibold text-[#523410]">{{ plan.trip_id }}</p>
        <h2 class="mt-2 text-3xl font-semibold">{{ plan.destination }}</h2>
      </div>
      <p class="text-sm leading-6 text-[#37352f]">{{ plan.summary }}</p>
    </div>

    <section v-if="transportPlan" class="overflow-hidden rounded-lg border border-[#d8c7a4] bg-[#f8f5e8]">
      <header class="border-b border-[#d8c7a4] px-4 py-3">
        <div class="flex flex-wrap items-start justify-between gap-2">
          <div class="min-w-0">
            <p class="text-xs font-semibold text-[#9a5b13]">往返交通</p>
            <h3 class="mt-1 break-words text-lg font-semibold">{{ transportPlan.origin }} → {{ transportPlan.destination }}</h3>
          </div>
          <p class="text-xs font-medium text-[#787671]">查询于 {{ formatSearchedAt(transportPlan.searched_at) }}</p>
        </div>
        <p v-if="transportPlan.recommendation_reason" class="mt-2 text-sm leading-6 text-[#5d5b54]">{{ transportPlan.recommendation_reason }}</p>
        <ul v-if="transportPlan.warnings.length" class="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-[#793400]">
          <li v-for="warning in transportPlan.warnings" :key="warning">{{ warning }}</li>
        </ul>
      </header>

      <div v-if="transportOptions.length" class="divide-y divide-[#d8c7a4]">
        <article v-for="option in transportOptions" :key="option.id" class="min-w-0 bg-white/70 px-4 py-4">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="flex flex-wrap items-center gap-2">
              <h4 class="font-semibold">{{ modeLabels[option.mode] }}</h4>
              <span v-if="option.id === transportPlan.recommended_option_id" class="rounded bg-[#d9f3e1] px-2 py-1 text-xs font-semibold text-[#11752b]">推荐</span>
              <span class="rounded bg-[#e6e0f5] px-2 py-1 text-xs font-semibold text-[#391c57]">{{ qualityLabels[option.data_quality] }}</span>
            </div>
            <p class="break-words text-sm font-semibold text-[#793400]">{{ priceText(option) }}</p>
          </div>

          <div class="mt-4 grid gap-4 lg:grid-cols-2">
            <div v-for="leg in [{ label: '去程', value: option.outbound }, { label: '返程', value: option.return_leg }]" :key="leg.label" class="min-w-0 border-l-2 border-[#dd5b00] pl-3">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <p class="text-sm font-semibold">{{ leg.label }}</p>
                <p class="text-xs font-medium text-[#787671]">{{ leg.value.transfer_count }} 次中转</p>
              </div>
              <p class="mt-1 break-words text-sm leading-6 text-[#37352f]">{{ formatProviderDateTime(leg.value.departure_at) }} → {{ formatProviderDateTime(leg.value.arrival_at) }}</p>
              <ol v-if="leg.value.segments.length" class="mt-2 space-y-2">
                <li v-for="(segment, segmentIndex) in leg.value.segments" :key="`${segment.service_number}-${segmentIndex}`" class="min-w-0 text-xs leading-5 text-[#5d5b54]">
                  <p class="break-words font-semibold text-[#37352f]">{{ [segment.carrier, segment.service_number].filter(Boolean).join(' ') || '班次待确认' }}</p>
                  <p class="break-words">{{ segment.from_terminal || '起点待确认' }} → {{ segment.to_terminal || '终点待确认' }}</p>
                  <p>{{ formatProviderDateTime(segment.departure_at) }} → {{ formatProviderDateTime(segment.arrival_at) }}</p>
                </li>
              </ol>
              <p v-else class="mt-2 text-xs text-[#787671]">班次与站点待确认</p>
            </div>
          </div>

          <ul v-if="option.fare_details.length" class="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs leading-5 text-[#5d5b54]">
            <li v-for="fare in option.fare_details" :key="fare" class="break-words">{{ fare }}</li>
          </ul>
          <div class="mt-3 flex flex-col gap-1 border-t border-[#e5e3df] pt-3 text-xs leading-5 text-[#5d5b54] sm:flex-row sm:justify-between sm:gap-4">
            <p class="break-words">{{ option.booking_hint || '预订前请核实供应商信息。' }}</p>
            <p class="shrink-0 font-semibold">来源：{{ option.provider }}</p>
          </div>
        </article>
      </div>
      <p v-else class="px-4 py-5 text-sm text-[#5d5b54]">暂未找到可用的往返交通方案。</p>
    </section>

    <article v-for="day in plan.days" :key="`${day.day}-${day.date}`" class="rounded-xl border border-[#e5e3df] p-4">
      <div class="grid gap-3 lg:grid-cols-[180px_minmax(0,1fr)]">
        <div>
          <p class="text-xs font-semibold text-[#5645d4]">第 {{ day.day }} 天 · {{ day.date }}</p>
          <h3 class="mt-1 text-lg font-semibold leading-snug">{{ day.title }}</h3>
          <div class="mt-3 grid gap-2 text-xs font-medium text-[#5d5b54]">
            <p class="rounded-md bg-[#dcecfa] px-3 py-2">{{ day.weather }}</p>
            <p class="rounded-md bg-[#f9e79f] px-3 py-2">{{ day.daily_budget }}</p>
            <p class="rounded-md bg-[#d9f3e1] px-3 py-2">{{ day.transport }}</p>
          </div>
        </div>

        <ol class="grid gap-3">
          <li v-for="item in day.items" :key="`${day.date}-${item.time}-${item.place}`" class="grid gap-3 rounded-lg bg-[#fafaf9] p-3 sm:grid-cols-[72px_minmax(0,1fr)]">
            <p class="text-sm font-semibold text-[#5645d4]">{{ item.time }}</p>
            <div>
              <div class="flex flex-wrap items-center gap-2">
                <h4 class="font-semibold">{{ item.place }}</h4>
                <span class="rounded bg-white px-2 py-1 text-xs font-semibold text-[#793400]">{{ item.estimated_cost }}</span>
              </div>
              <p class="mt-2 text-sm leading-6 text-[#37352f]">{{ item.activity }}</p>
              <div class="mt-2 grid gap-2 text-xs font-medium text-[#5d5b54] md:grid-cols-2">
                <p class="rounded-md bg-white px-2 py-1.5">{{ item.booking_hint }}</p>
                <p class="rounded-md bg-white px-2 py-1.5">{{ item.source_hint }}</p>
              </div>
            </div>
          </li>
        </ol>
      </div>

      <ul v-if="day.notes.length > 0" class="mt-3 list-disc space-y-1 pl-5 text-sm leading-6 text-[#5d5b54]">
        <li v-for="note in day.notes" :key="note">{{ note }}</li>
      </ul>
    </article>

    <div class="rounded-xl bg-[#d9f3e1] p-4">
      <h3 class="font-semibold">出发前提醒</h3>
      <ul class="mt-3 grid gap-2 text-sm leading-6 text-[#37352f] md:grid-cols-2">
        <li v-for="tip in plan.tips" :key="tip">{{ tip }}</li>
      </ul>
      <p class="mt-4 border-t border-[#1aae39]/20 pt-4 text-xs font-semibold text-[#5d5b54]">{{ plan.disclaimer }}</p>
    </div>
  </div>
</template>
