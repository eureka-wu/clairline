<template>
  <div class="app-root" :class="{ 'is-map-mode': currentTab === 'map' }">
    <!-- 顶部导航栏 -->
    <AppHeader 
      v-model:currentTab="currentTab"
      :patrol-count="patrolCount"
      @open-patrol="patrolModalVisible = true"
    />

    <!-- 主体容器 (限制 1280px 居中) -->
    <main class="app-container" :class="{ 'is-map-container': currentTab === 'map' }">


      <!-- TAB 1: 航线探索列表 -->
      <section v-show="currentTab === 'routes'">
        <!-- 筛选栏 -->
        <RouteFilterBar 
          v-model:origin="origin"
          v-model:destination="destination"
          v-model:onlyAvailable="onlyAvailable"
          v-model:sortBy="sortBy"
          :available-count="filteredAvailableCount"
          :total-count="filteredTotalCount"
          @swap-failed="showToast"
        />

        <!-- 航线卡片列表 -->
        <div class="routes-grid">
          <RouteCard 
            v-for="r in displayedRoutes"
            :key="`${r.from}-${r.to}`"
            :route="r"
            :seat-cache="seatCache"
            @click-date="handleDateClick"
            @hover-date="handleDateHover"
            @leave-date="handleDateLeave"
            @open-drawer="openDrawer"
            @refresh-calendar="handleRefreshCalendar"
          />

          <!-- 空状态 -->
          <div v-if="displayedRoutes.length === 0" style="text-align:center; padding:48px 20px; background:#fff; border-radius:12px; border:1px solid #e2e8f0;">
            <div style="font-size:1.1rem; font-weight:800; color:var(--text-primary); margin-bottom:6px;">未匹配到符合条件的直飞航线</div>
            <div style="font-size:0.85rem; color:var(--text-muted);">可尝试关闭“仅看有票航线”或切换出发城市</div>
          </div>
        </div>
      </section>

      <!-- TAB 2: 地图探索 -->
      <section v-show="currentTab === 'map'">
        <FlightMap 
          v-model:origin="origin"
          :available-routes="availableRoutes"
          @open-drawer="openDrawer"
        />
      </section>
    </main>

    <!-- 就地微气泡 Popover (触摸即显 · 移走即隐) -->
    <SeatPopover 
      :visible="popover.visible"
      :from-city="popover.fromCity"
      :to-city="popover.toCity"
      :flight-date="popover.flightDate"
      :target-el="popover.targetEl"
      :flights="popover.flights"
      :loading="popover.loading"
      :time-formatted="popover.timeFormatted"
      @close="popover.visible = false"
      @refresh="handlePopoverRefresh"
      @popover-enter="handlePopoverEnter"
      @popover-leave="handlePopoverLeave"
    />

    <!-- 航线详情与接驳规划抽屉 -->
    <RouteDetailDrawer 
      :visible="drawerVisible"
      :route="selectedRoute"
      :seat-cache="seatCache"
      @close="drawerVisible = false"
      @click-date="handleDateClick"
      @hover-date="handleDateHover"
      @leave-date="handleDateLeave"
      @refresh-calendar="handleRefreshCalendar"
    />

    <!-- 巡检航线配置模态框 -->
    <PatrolModal 
      :visible="patrolModalVisible"
      @close="patrolModalVisible = false"
      @saved="(cnt) => { patrolCount = cnt; showToast('巡检配置已成功保存并落库！'); }"
    />

    <!-- 悬浮 Toast 轻提示 -->
    <div v-if="toast.visible" class="app-toast-box">
      <span>{{ toast.message }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import AppHeader from './components/AppHeader.vue';
import RouteFilterBar from './components/RouteFilterBar.vue';
import RouteCard from './components/RouteCard.vue';
import SeatPopover from './components/SeatPopover.vue';
import RouteDetailDrawer from './components/RouteDetailDrawer.vue';
import PatrolModal from './components/PatrolModal.vue';
import FlightMap from './components/FlightMap.vue';

import { fetchAvailableRoutes, queryLiveFlights, refreshRouteCalendar } from './api/flights.js';
import { fetchPatrolHotRoutes } from './api/patrol.js';
import { DIRECT_MAP } from './data/routes-network.js';
import { CITY_METADATA } from './data/city-meta.js';

// 当前状态
const currentTab = ref('routes');

// 用户需求：仅在地图模式下锁定页面滚动，表格探索列表模式正常滚动浏览
watch(currentTab, (val) => {
  if (val === 'map') {
    document.body.classList.add('is-map-tab');
  } else {
    document.body.classList.remove('is-map-tab');
  }
}, { immediate: true });

onUnmounted(() => {
  document.body.classList.remove('is-map-tab');
});

const origin = ref('杭州');
const destination = ref('全部');
const onlyAvailable = ref(true);
const sortBy = ref('recent-first');

const availableRoutes = ref([]);
const seatCache = ref({});
const summary = ref({});
const patrolCount = ref(30);

// 模态框与抽屉
const drawerVisible = ref(false);
const selectedRoute = ref({});
const patrolModalVisible = ref(false);

// 就地微气泡状态与防抖定时器
const popover = ref({
  visible: false,
  fromCity: '',
  toCity: '',
  flightDate: '',
  targetEl: null,
  flights: [],
  loading: false,
  timeFormatted: ''
});
let popoverCloseTimer = null;

// Toast
const toast = ref({ visible: false, message: '' });
let toastTimer = null;

function showToast(msg) {
  toast.value.message = msg;
  toast.value.visible = true;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.value.visible = false;
  }, 3000);
}

// 精确计算航线大圆物理航距 (Haversine 公式)
function getRouteDistance(r) {
  if (r.distance && r.distance > 0) return r.distance;
  const c1 = CITY_METADATA[r.from]?.coords;
  const c2 = CITY_METADATA[r.to]?.coords;
  if (!c1 || !c2) return 0;
  const rad = Math.PI / 180;
  const lat1 = c1[1] * rad, lat2 = c2[1] * rad;
  const dLat = (c2[1] - c1[1]) * rad;
  const dLon = (c2[0] - c1[0]) * rad;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return Math.round(6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
}

// 缓存统计
const cachedDaysCount = computed(() => Object.keys(seatCache.value).length);

// 筛选后的航线列表 (严谨落实 4 种排序)
const displayedRoutes = computed(() => {
  let list = availableRoutes.value;

  // 1. 出发城市过滤
  if (origin.value !== '全部') {
    list = list.filter(r => r.from === origin.value);
  }

  // 2. 目的城市过滤
  if (destination.value !== '全部') {
    list = list.filter(r => r.to === destination.value);
  }

  // 3. 仅看有票过滤
  if (onlyAvailable.value) {
    list = list.filter(r => (r.availableDaysCount || (r.availableDates || []).length) > 0);
  }

  // 4. 排序
  const sorted = [...list];
  const now = new Date();
  const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  const sevenDaysLater = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);

  if (sortBy.value === 'recent-first') {
    // 最近可兑：优先按照未来 7 天内放票天数（近期票量密度）降序！
    // 若 7 天内天数相同，按最早可兑日升序，再按总票数降序，再按航距降序
    sorted.sort((a, b) => {
      const datesA = a.availableDates || [];
      const datesB = b.availableDates || [];
      const recentA = datesA.filter(d => d >= todayStr && d <= sevenDaysLater).length;
      const recentB = datesB.filter(d => d >= todayStr && d <= sevenDaysLater).length;
      if (recentB !== recentA) return recentB - recentA;

      const firstA = datesA.find(d => d >= todayStr) || '9999-99-99';
      const firstB = datesB.find(d => d >= todayStr) || '9999-99-99';
      if (firstA !== firstB) return firstA.localeCompare(firstB);

      const cntDiff = (b.availableDaysCount || datesB.length) - (a.availableDaysCount || datesA.length);
      if (cntDiff !== 0) return cntDiff;
      return getRouteDistance(b) - getRouteDistance(a);
    });
  } else if (sortBy.value === 'time-asc') {
    // 起飞时间：按全天最早班次起飞时间升序（如 06:40 早班机排在前，18:00 晚班机排在后）
    sorted.sort((a, b) => {
      const timeA = (a.flights && a.flights[0]?.depTime) || '99:99';
      const timeB = (b.flights && b.flights[0]?.depTime) || '99:99';
      const diff = timeA.localeCompare(timeB);
      if (diff !== 0) return diff;
      return getRouteDistance(b) - getRouteDistance(a);
    });
  } else if (sortBy.value === 'dist-desc') {
    // 航距最长：长途大线排在前
    sorted.sort((a, b) => getRouteDistance(b) - getRouteDistance(a));
  }

  return sorted;
});

const filteredAvailableCount = computed(() => {
  return availableRoutes.value.filter(r => {
    if (origin.value !== '全部' && r.from !== origin.value) return false;
    if (destination.value !== '全部' && r.to !== destination.value) return false;
    return (r.availableDaysCount || (r.availableDates || []).length) > 0;
  }).length;
});

const filteredTotalCount = computed(() => {
  return availableRoutes.value.filter(r => {
    if (origin.value !== '全部' && r.from !== origin.value) return false;
    if (destination.value !== '全部' && r.to !== destination.value) return false;
    return true;
  }).length;
});

// 加载大盘数据与数据库在库查验缓存
async function initData() {
  try {
    const data = await fetchAvailableRoutes();
    if (data && data.routes) {
      availableRoutes.value = data.routes;
      summary.value = {
        totalAvailableRoutes: data.totalAvailableRoutes,
        totalDatePoints: data.totalDatePoints
      };
      // 核心：直接将 SQLite 数据库返回的全量查验缓存注入响应式状态
      if (data.seatCache) {
        seatCache.value = Object.assign({}, data.seatCache);
      }
    }
  } catch (err) {
    console.warn('获取大盘数据异常:', err);
  }

  // 加载巡检数量
  try {
    const pRes = await fetchPatrolHotRoutes();
    if (pRes?.routes) patrolCount.value = pRes.routes.length;
  } catch (e) {}
}

// 触摸已查验胶囊即显
function handleDateHover({ from, to, date, targetEl }) {
  if (popoverCloseTimer) {
    clearTimeout(popoverCloseTimer);
    popoverCloseTimer = null;
  }
  const cacheKey = `${from}-${to}-${date}`;
  const cached = seatCache.value[cacheKey];
  if (cached) {
    popover.value = {
      visible: true,
      fromCity: from,
      toCity: to,
      flightDate: date,
      targetEl: targetEl,
      flights: cached.flights || [],
      loading: false,
      timeFormatted: cached.timeFormatted || cached.timeLabel || ''
    };
  }
}

// 鼠标移出胶囊即延时优雅关闭
function handleDateLeave() {
  if (popoverCloseTimer) clearTimeout(popoverCloseTimer);
  popoverCloseTimer = setTimeout(() => {
    popover.value.visible = false;
  }, 160);
}

// 鼠标进入气泡主体内部保持显示
function handlePopoverEnter() {
  if (popoverCloseTimer) {
    clearTimeout(popoverCloseTimer);
    popoverCloseTimer = null;
  }
}

// 鼠标移出气泡主体关闭
function handlePopoverLeave() {
  if (popoverCloseTimer) clearTimeout(popoverCloseTimer);
  popoverCloseTimer = setTimeout(() => {
    popover.value.visible = false;
  }, 160);
}

// 点击具体出行日胶囊 (未查验的在此处发起联网查询)
async function handleDateClick({ from, to, date, targetEl }) {
  const cacheKey = `${from}-${to}-${date}`;
  const cached = seatCache.value[cacheKey];

  // 1. 如果 SQLite 数据库缓存已有完整各班航班详情，0ms 瞬间就地弹出微气泡！
  if (cached && cached.flights && cached.flights.length > 0) {
    popover.value = {
      visible: true,
      fromCity: from,
      toCity: to,
      flightDate: date,
      targetEl: targetEl,
      flights: cached.flights,
      loading: false,
      timeFormatted: cached.timeFormatted || cached.timeLabel
    };
    return;
  }

  // 2. 首次查验，就地弹出微气泡加载中
  popover.value = {
    visible: true,
    fromCity: from,
    toCity: to,
    flightDate: date,
    targetEl: targetEl,
    flights: [],
    loading: true,
    timeFormatted: ''
  };

  try {
    const res = await queryLiveFlights(from, to, date);
    if (res.ok && res.flights) {
      let totalLeft = 0;
      res.flights.forEach(f => { totalLeft += (Number(f.secCardLeft) || 0); });
      const now = new Date();
      const timeLabel = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}查`;
      const timeFormatted = `${now.getMonth() + 1}月${now.getDate()}日 ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

      // 写入前端响应式缓存 (后端已在数据库中完成落库)
      seatCache.value[cacheKey] = {
        count: totalLeft,
        timeLabel,
        timeFormatted: res.queryTime || timeFormatted,
        flights: res.flights
      };

      popover.value.loading = false;
      popover.value.flights = res.flights;
      popover.value.timeFormatted = res.queryTime || timeFormatted;
    } else {
      popover.value.loading = false;
      popover.value.flights = [];
    }
  } catch (e) {
    popover.value.loading = false;
    showToast('查询航班异常，请重试');
  }
}

// 微气泡内点击“刷新”
async function handlePopoverRefresh({ fromCity, toCity, flightDate, targetEl }) {
  popover.value.loading = true;
  try {
    const res = await queryLiveFlights(fromCity, toCity, flightDate, true);
    if (res.ok && res.flights) {
      let totalLeft = 0;
      res.flights.forEach(f => { totalLeft += (Number(f.secCardLeft) || 0); });
      const now = new Date();
      const timeLabel = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}查`;

      const cacheKey = `${fromCity}-${toCity}-${flightDate}`;
      seatCache.value[cacheKey] = {
        count: totalLeft,
        timeLabel,
        timeFormatted: res.queryTime,
        flights: res.flights
      };

      popover.value.loading = false;
      popover.value.flights = res.flights;
      popover.value.timeFormatted = res.queryTime;
      showToast('票况已重新联网刷新并落库！');
    } else {
      popover.value.loading = false;
    }
  } catch (e) {
    popover.value.loading = false;
    showToast('刷新超时');
  }
}

// 刷新单条航线放票日历
async function handleRefreshCalendar({ from, to, done }) {
  try {
    const res = await refreshRouteCalendar(from, to);
    if (res.ok && res.availableDates) {
      const match = availableRoutes.value.find(r => r.from === from && r.to === to);
      if (match) {
        match.availableDates = res.availableDates;
        match.availableDaysCount = res.availableDates.length;
      }
      if (selectedRoute.value && selectedRoute.value.from === from && selectedRoute.value.to === to) {
        selectedRoute.value.availableDates = res.availableDates;
        selectedRoute.value.availableDaysCount = res.availableDates.length;
      }
      showToast(`【${from} ➔ ${to}】日历已更新！共 ${res.availableDates.length} 天有票`);
    } else {
      showToast(`刷新提示: ${res.error || '暂无新增'}`);
    }
  } catch (e) {
    showToast(`刷新提示: ${e.message || '网络请求异常'}`);
  } finally {
    done();
  }
}

function openDrawer(route) {
  selectedRoute.value = route;
  drawerVisible.value = true;
}

onMounted(() => {
  initData();
});
</script>

<style>
.app-toast-box {
  position: fixed;
  bottom: 30px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(15, 23, 42, 0.92);
  color: #ffffff;
  padding: 8px 18px;
  border-radius: var(--radius-full);
  font-size: 0.82rem;
  font-weight: 600;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
  z-index: 2000;
  backdrop-filter: blur(6px);
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translate(-50%, 10px); }
  to { opacity: 1; transform: translate(-50%, 0); }
}
</style>
