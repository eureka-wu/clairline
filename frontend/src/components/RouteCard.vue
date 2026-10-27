<template>
  <div class="route-card">
    <!-- 卡片上半部分：航线与排班信息 -->
    <div class="card-top">
      <div class="route-endpoints">
        <span class="city-name">{{ route.from }}</span>
        <span class="arrow-icon">➔</span>
        <span class="city-name">{{ route.to }}</span>
        <div class="airports-sub">
          {{ originMeta.airport || '国际机场' }} ➔ {{ destMeta.airport || '国际机场' }}
        </div>
      </div>

      <!-- 排班跨度与班次信息 (彻底修复首末班相同 Bug) -->
      <div class="flight-schedule-info">
        <template v-if="scheduleSpan.isSingle">
          <span class="badge-tag badge-direct">{{ scheduleSpan.stopoverTag }}</span>
          <span style="font-weight:800; font-size:0.92rem; font-variant-numeric:tabular-nums;">
            {{ scheduleSpan.firstFlight?.flightNo }}
          </span>
          <span style="font-size:0.75rem; color:var(--text-muted); background:#f1f5f9; padding:1px 5px; border-radius:4px;">
            {{ scheduleSpan.firstFlight?.aircraft || 'A320' }}
          </span>
          <div class="schedule-times">
            <span>{{ scheduleSpan.firstFlight?.depTime }}</span>
            <span style="color:#94a3b8; font-size:0.75rem;">➔</span>
            <span>{{ scheduleSpan.firstFlight?.arrTime }}</span>
            <span style="font-size:0.74rem; font-weight:500; color:#64748b;">
              ({{ scheduleSpan.firstFlight?.duration }})
            </span>
          </div>
          <span class="freq-tag">{{ scheduleSpan.frequencyText }}</span>
        </template>

        <template v-else-if="scheduleSpan.isMulti">
          <span class="badge-tag badge-span">全天共 {{ scheduleSpan.count }} 班</span>
          <span style="font-size:0.74rem; color:var(--text-secondary); background:#f1f5f9; padding:2px 6px; border-radius:4px;">
            {{ scheduleSpan.stopoverSummary }}
          </span>
          <div class="schedule-times">
            <template v-if="scheduleSpan.depTimesSame">
              <span class="time-prefix">每日</span>
              <span>{{ scheduleSpan.firstFlight?.depTime }}</span>
              <span class="time-prefix">起飞</span>
            </template>
            <template v-else>
              <span class="time-prefix">首班</span>
              <span>{{ scheduleSpan.firstFlight?.depTime }}</span>
              <span style="color:#94a3b8; margin:0 2px;">~</span>
              <span class="time-prefix">末班</span>
              <span>{{ scheduleSpan.lastFlight?.depTime }}</span>
            </template>
          </div>
          <span class="freq-tag">{{ scheduleSpan.frequencyText }}</span>
          <span style="font-size:0.72rem; color:var(--accent-cyan); font-weight:600;">(点日期查各班余票)</span>
        </template>
      </div>
    </div>

    <!-- 卡片下半部分：可兑换出行日胶囊流 -->
    <div class="dates-deck">
      <div class="dates-badge-btn">
        <span 
          class="avail-count-tag"
          :style="(route.availableDaysCount || 0) === 0 ? 'background:#f1f5f9; color:#64748b; border-color:#e2e8f0;' : ''"
        >
          {{ (route.availableDaysCount || 0) > 0 ? `可兑换 ${route.availableDaysCount} 天` : '暂无放票' }}
        </span>
        <button 
          type="button" 
          class="btn-refresh-route"
          :disabled="isRefreshing"
          @click="onRefreshCalendar"
          title="向官方刷新放票日历"
        >
          <span>{{ isRefreshing ? '刷新中...' : '刷新放票' }}</span>
        </button>
      </div>

      <div class="dates-chips-flow">
        <div v-if="visibleDates.length === 0" style="font-size:0.75rem; color:#94a3b8; padding:4px 0;">
          当前暂无可兑日期，可点击上方「刷新放票」查询最新票况
        </div>

        <div 
          v-for="d in visibleDates" 
          :key="d"
          class="date-pill"
          :class="{
            'is-weekend': isWeekend(d),
            'is-checked': Boolean(seatCache[`${route.from}-${route.to}-${d}`])
          }"
          :title="getPillTitle(d)"
          @click="onPillClick(d, $event)"
          @mouseenter="onPillMouseEnter(d, $event)"
          @mouseleave="onPillMouseLeave(d)"
        >
          <span>{{ formatDateLabel(d) }}</span>
          <!-- 数据库回显微标 -->
          <template v-if="seatCache[`${route.from}-${route.to}-${d}`]">
            <span 
              class="pill-check-tag"
              :class="seatCache[`${route.from}-${route.to}-${d}`].count > 0 ? 'tag-success' : 'tag-empty'"
            >
              {{ seatCache[`${route.from}-${route.to}-${d}`].count > 0 
                ? `余${seatCache[`${route.from}-${route.to}-${d}`].count} · ${seatCache[`${route.from}-${route.to}-${d}`].timeLabel}`
                : `兑完 · ${seatCache[`${route.from}-${route.to}-${d}`].timeLabel}` }}
            </span>
          </template>
        </div>

        <!-- 展开/收起全部日期 -->
        <button 
          v-if="(route.availableDates || []).length > 10"
          type="button" 
          class="btn-expand-dates"
          @click="expanded = !expanded"
        >
          {{ expanded ? '收起 ▴' : `展开全部 (${route.availableDates.length}天) ▾` }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { CITY_METADATA } from '../data/city-meta.js';
import { FLIGHTS_SCHEDULE } from '../data/flights-schedule.js';

const props = defineProps({
  route: {
    type: Object,
    required: true
  },
  seatCache: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['click-date', 'hover-date', 'leave-date', 'open-drawer', 'refresh-calendar']);

function hasCachedData(d) {
  const cacheKey = `${props.route.from}-${props.route.to}-${d}`;
  return Boolean(props.seatCache[cacheKey]);
}

function onPillClick(d, event) {
  emit('click-date', { from: props.route.from, to: props.route.to, date: d, targetEl: event.currentTarget });
}

function onPillMouseEnter(d, event) {
  if (hasCachedData(d)) {
    emit('hover-date', { from: props.route.from, to: props.route.to, date: d, targetEl: event.currentTarget });
  }
}

function onPillMouseLeave(d) {
  if (hasCachedData(d)) {
    emit('leave-date');
  }
}

const expanded = ref(false);
const isRefreshing = ref(false);

const originMeta = computed(() => CITY_METADATA[props.route.from] || {});
const destMeta = computed(() => CITY_METADATA[props.route.to] || {});

// 计算排班时刻跨度并去重（彻底解决首末班相同问题）
const scheduleSpan = computed(() => {
  const allFlights = FLIGHTS_SCHEDULE.filter(f => f.from === props.route.from && f.to === props.route.to);
  
  // 去除完全相同航班号与时刻的重复项
  const uniqueMap = new Map();
  allFlights.forEach(f => {
    const key = `${f.flightNo}-${f.depTime}-${f.arrTime}`;
    if (!uniqueMap.has(key)) uniqueMap.set(key, f);
  });
  const list = Array.from(uniqueMap.values()).sort((a, b) => (a.depTime || '').localeCompare(b.depTime || ''));

  if (list.length === 0) {
    return { isNone: true };
  }

  if (list.length === 1) {
    const f0 = list[0];
    return {
      isSingle: true,
      firstFlight: f0,
      stopoverTag: f0.stopover === '直飞' ? '首选单班' : (f0.stopover || '首选单班'),
      frequencyText: formatFrequency(f0.frequency)
    };
  }

  // 多班航线
  const first = list[0];
  const last = list[list.length - 1];
  const hasDirect = list.some(f => f.stopover === '直飞');
  const hasVia = list.some(f => f.stopover !== '直飞');

  // 计算全周合并频次
  const daySet = new Set();
  list.forEach(f => (f.frequency || '').split('').forEach(d => daySet.add(d)));
  const freqMap = { '1': '一', '2': '二', '3': '三', '4': '四', '5': '五', '6': '六', '7': '日' };
  const combinedFreq = daySet.size >= 7 ? '天天执飞' : `周${Array.from(daySet).sort().map(d => freqMap[d] || d).join('')}`;

  return {
    isMulti: true,
    count: list.length,
    firstFlight: first,
    lastFlight: last,
    depTimesSame: first.depTime === last.depTime,
    stopoverSummary: hasDirect && hasVia ? '含直飞/经停' : (hasDirect ? '直飞' : '经停'),
    frequencyText: combinedFreq
  };
});

function formatFrequency(freq) {
  if (!freq) return '班期以长龙发布为准';
  if (freq === '1234567') return '天天执飞';
  const map = { '1': '一', '2': '二', '3': '三', '4': '四', '5': '五', '6': '六', '7': '日' };
  return '周' + freq.split('').map(d => map[d] || d).join('');
}

const visibleDates = computed(() => {
  const dates = props.route.availableDates || [];
  if (expanded.value || dates.length <= 10) return dates;
  return dates.slice(0, 10);
});

function formatDateLabel(d) {
  const dt = new Date(d);
  const dayOfWeek = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][dt.getDay()];
  const shortDate = d.slice(5);
  return `${shortDate} ${dayOfWeek}`;
}

function isWeekend(d) {
  const day = new Date(d).getDay();
  return day === 0 || day === 6;
}

function getPillTitle(d) {
  const cached = props.seatCache[`${props.route.from}-${props.route.to}-${d}`];
  if (cached) {
    return `查询时间：${cached.timeFormatted}\n畅飞卡余 ${cached.count} 张 (点击可看各班详情)`;
  }
  return `点击实时查验 ${d} 官方航班余票`;
}

async function onRefreshCalendar() {
  if (isRefreshing.value) return;
  isRefreshing.value = true;
  emit('refresh-calendar', {
    from: props.route.from,
    to: props.route.to,
    done: () => { isRefreshing.value = false; }
  });
}
</script>
