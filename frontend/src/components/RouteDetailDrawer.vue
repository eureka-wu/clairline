<template>
  <div v-if="visible" class="drawer-backdrop" @click.self="$emit('close')">
    <div class="drawer-panel">
      <!-- 头部 -->
      <div class="drawer-header">
        <div>
          <div style="font-size:1.2rem; font-weight:800; color:var(--text-primary);">
            {{ route.from }} ➔ {{ route.to }}
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">
            长龙航空执飞 · 航线总里程 {{ route.distance ? `${route.distance.toLocaleString()} km` : '直飞' }}
          </div>
        </div>
        <button 
          type="button" 
          class="btn-popover-close" 
          style="font-size:1.4rem;" 
          @click="$emit('close')"
        >
          &times;
        </button>
      </div>

      <!-- 主体内容 -->
      <div class="drawer-body">
        <!-- 60天可兑换出行日网格 -->
        <div style="margin-bottom:20px;">
          <div style="font-size:0.9rem; font-weight:800; color:#059669; margin-bottom:10px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
            <span>近 60 天可兑换出行日 ({{ (route.availableDates || []).length }} 天)</span>
            <div style="display:flex; align-items:center; gap:8px;">
              <button 
                type="button" 
                class="btn-refresh-route"
                :disabled="isRefreshing"
                @click="onRefreshCalendar"
                title="实时联网向长龙官方刷新本航线放票日历"
              >
                <span>{{ isRefreshing ? '刷新中...' : '刷新放票' }}</span>
              </button>
              <span style="font-size:0.72rem; color:var(--text-muted); font-weight:normal;">已查验触摸即显 · 未查验点击查询</span>
            </div>
          </div>

          <div style="display:flex; flex-wrap:wrap; gap:6px;">
            <div 
              v-for="d in (route.availableDates || [])" 
              :key="d"
              class="date-pill"
              :class="{
                'is-weekend': isWeekend(d),
                'is-checked': Boolean(seatCache[`${route.from}-${route.to}-${d}`])
              }"
              @click="onPillClick(d, $event)"
              @mouseenter="onPillMouseEnter(d, $event)"
              @mouseleave="onPillMouseLeave(d)"
            >
              <span>{{ formatDateLabel(d) }}</span>
              <template v-if="seatCache[`${route.from}-${route.to}-${d}`]">
                <span 
                  class="pill-check-tag"
                  :class="seatCache[`${route.from}-${route.to}-${d}`].count > 0 ? 'tag-success' : 'tag-empty'"
                >
                  {{ seatCache[`${route.from}-${route.to}-${d}`].count > 0 
                    ? `余${seatCache[`${route.from}-${route.to}-${d}`].count}`
                    : '兑完' }}
                </span>
              </template>
            </div>
          </div>
        </div>

        <!-- 落地延伸漫游建议 -->
        <div 
          v-if="onwardTip" 
          style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:var(--radius-md); padding:12px 14px; margin-bottom:18px;"
        >
          <div style="font-size:0.85rem; font-weight:800; color:#15803d; margin-bottom:4px;">
            落地【{{ route.to }}】周边延伸漫游建议
          </div>
          <div style="font-size:0.78rem; color:#166534; line-height:1.5;">
            {{ onwardTip }}
          </div>
        </div>

        <!-- 周边超级高铁枢纽接驳建议 -->
        <div v-if="railHubs.length > 0" style="margin-top:10px;">
          <div style="font-size:0.88rem; font-weight:800; color:var(--text-primary); margin-bottom:8px;">
            出发地周边超级枢纽高铁接驳
          </div>
          <div 
            v-for="(h, idx) in railHubs" 
            :key="idx"
            style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:var(--radius-md); padding:10px 12px; margin-bottom:8px;"
          >
            <div style="font-weight:700; font-size:0.82rem; color:var(--accent-cyan);">
              接驳枢纽：【{{ h.target }}】· 高铁约 {{ h.duration }} (参考 {{ h.priceRange }})
            </div>
            <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">
              {{ h.advantage }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { DEST_ONWARD_TIPS, HIGH_SPEED_RAIL_CONNECTIONS } from '../data/city-meta.js';

const props = defineProps({
  visible: Boolean,
  route: {
    type: Object,
    default: () => ({})
  },
  seatCache: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['close', 'click-date', 'hover-date', 'leave-date', 'refresh-calendar']);

const isRefreshing = ref(false);

function onRefreshCalendar() {
  if (isRefreshing.value) return;
  isRefreshing.value = true;
  emit('refresh-calendar', {
    from: props.route.from,
    to: props.route.to,
    done: () => {
      isRefreshing.value = false;
    }
  });
}

const onwardTip = computed(() => DEST_ONWARD_TIPS[props.route.to] || '');
const railHubs = computed(() => HIGH_SPEED_RAIL_CONNECTIONS[props.route.from] || []);

function formatDateLabel(d) {
  const dt = new Date(d);
  const week = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][dt.getDay()];
  return `${d.slice(5)} ${week}`;
}

function isWeekend(d) {
  const day = new Date(d).getDay();
  return day === 0 || day === 6;
}

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
</script>
