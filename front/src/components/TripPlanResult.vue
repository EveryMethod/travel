<script setup lang="ts">
import type { TripPlanResponse } from '@/types'

defineProps<{ plan: TripPlanResponse }>()
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
