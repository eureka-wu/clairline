<template>
  <div class="app-root" :class="{ 'is-map-mode': currentTab === 'map' }">
    <!-- 顶部导航栏 -->
    <AppHeader 
      v-model:currentTab="currentTab"
      :patrol-state="patrolState"
      :auth-status="authStatus"
      :update-info="updateInfo"
      @open-patrol="handleOpenPatrol"
      @open-auth="openAuthModal(false)"
      @open-update="openUpdateModal"
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

          <!-- 首屏加载中状态 (防闪烁骨架卡片) -->
          <div v-if="isInitialLoading && displayedRoutes.length === 0" class="routes-loading-card">
            <div class="loading-spin-circle"></div>
            <div class="loading-main-title">正在同步全国直飞拓扑与最新放票大盘...</div>
            <div class="loading-sub-desc">毫秒级秒开本地数据库，请稍候</div>
          </div>

          <!-- 真实空状态 (仅在数据加载完成且筛选确实无结果时显示) -->
          <div v-else-if="!isInitialLoading && displayedRoutes.length === 0" style="text-align:center; padding:48px 20px; background:#fff; border-radius:12px; border:1px solid #e2e8f0;">
            <div style="font-size:1.1rem; font-weight:800; color:var(--text-primary); margin-bottom:6px;">未匹配到符合条件的直飞航线</div>
            <div style="font-size:0.85rem; color:var(--text-muted); margin-bottom:12px;">可尝试关闭“仅看有票航线”或切换出发城市</div>
            <button 
              v-if="!authStatus.is_logged_in" 
              type="button" 
              class="btn-primary" 
              style="padding:6px 16px; display:inline-flex; align-items:center; gap:5px;" 
              @click="openAuthModal(true)"
            >
              <span v-html="ICONS.phone" style="display:inline-flex;"></span>
              <span>手机验证码登录长龙会员</span>
            </button>
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

    <!-- 航线监控与全网普查模态框 -->
    <PatrolModal 
      :visible="patrolModalVisible"
      :patrol-state="patrolState"
      @close="patrolModalVisible = false"
      @triggered="handlePatrolTriggered"
      @expand-full="handleExpandFull"
      @saved="() => { showToast('监控配置已成功保存！'); }"
    />

    <!-- 会员登录同步向导模态框 (网页内嵌入抓包与证书指引) -->
    <AuthModal 
      :visible="authModalVisible"
      :auth-status="authStatus"
      :auto-start="autoStartCaptureOnOpen"
      @close="authModalVisible = false"
      @synced="handleAuthSynced"
      @refresh-auth="refreshAuthStatus"
    />

    <!-- 软件检查更新与版本发布模态框 (方案 A) -->
    <UpdateModal 
      :visible="updateModalVisible"
      :update-info="updateInfo"
      @close="updateModalVisible = false"
      @ignore-version="handleIgnoreVersion"
    />

    <!-- 全网探测普查全屏进度条模态框 -->
    <FullPatrolProgress 
      :visible="fullPatrolVisible"
      :patrol-state="patrolState"
      :auth-status="authStatus"
      :available-routes-count="availableRoutes.length"
      @minimize="handleMinimizePatrol"
      @close="fullPatrolVisible = false"
      @cancel="fullPatrolVisible = false"
      @completed="handleFullPatrolCompleted"
    />

    <!-- 转入后台时的常驻高质感悬浮进度微卡片 (Mini Floating Radar Widget) -->
    <transition name="mini-pop">
      <div 
        v-if="patrolState.running && !fullPatrolVisible" 
        class="mini-patrol-widget"
        @click="fullPatrolVisible = true"
        title="点击重新展开全屏高质感普查大雷达"
      >
        <div class="mini-widget-inner">
          <div class="mini-radar-avatar">
            <span v-html="ICONS.radar" class="mini-spin-radar"></span>
          </div>
          <div class="mini-widget-body">
            <div class="mini-widget-top">
              <span class="mini-badge-mode">{{ patrolState.mode === 'all' ? '全网普查中' : '重点巡检中' }}</span>
              <span class="mini-percent">{{ patrolState.percent || 0 }}%</span>
            </div>
            <div class="mini-route-info">
              <span class="mini-route-text">{{ formatMiniCurrentRoute }}</span>
              <span class="mini-counter">({{ patrolState.completed }}/{{ patrolState.total || 397 }})</span>
            </div>
            <div class="mini-progress-track">
              <div class="mini-progress-fill" :style="{ width: `${patrolState.percent || 2}%` }"></div>
            </div>
          </div>
          <div class="mini-expand-btn">
            <span v-html="ICONS.arrowRight"></span>
          </div>
        </div>
      </div>
    </transition>

    <!-- 全局现代高质感 EXE 模态对话框 (替换丑陋的浏览器原生 alert / confirm) -->
    <AppDialog 
      :visible="appDialog.visible"
      :title="appDialog.title"
      :message="appDialog.message"
      :type="appDialog.type"
      :confirm-text="appDialog.confirmText"
      :cancel-text="appDialog.cancelText"
      :show-cancel="appDialog.showCancel"
      @confirm="handleDialogConfirm"
      @cancel="handleDialogCancel"
      @close="handleDialogClose"
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
import AuthModal from './components/AuthModal.vue';
import UpdateModal from './components/UpdateModal.vue';
import FlightMap from './components/FlightMap.vue';
import AppDialog from './components/AppDialog.vue';
import FullPatrolProgress from './components/FullPatrolProgress.vue';

import { fetchAvailableRoutes, queryLiveFlights, refreshRouteCalendar } from './api/flights.js';
import { fetchPatrolHotRoutes, fetchPatrolStatus, triggerPatrol } from './api/patrol.js';
import { fetchAuthStatus } from './api/auth.js';
import { checkSystemUpdate } from './api/system.js';
import { DIRECT_MAP } from './data/routes-network.js';
import { CITY_METADATA } from './data/city-meta.js';
import { ICONS } from './data/icons.js';


// 当前状态
const currentTab = ref('routes');

// 用户需求：仅在地图模式下锁定页面滚动，表格探索列表模式正常滚动浏览
watch(currentTab, (val) => {
  if (val === 'map') {
    document.body.classList.add('is-map-tab');
  } else {
    document.body.classList.remove('is-map-tab');
    document.body.classList.remove('is-map-fullscreen');
    if (document.fullscreenElement && document.exitFullscreen) {
      document.exitFullscreen().catch(() => {});
    }
  }
}, { immediate: true });

onUnmounted(() => {
  document.body.classList.remove('is-map-tab');
  document.body.classList.remove('is-map-fullscreen');
  if (patrolPollTimer) {
    clearInterval(patrolPollTimer);
    patrolPollTimer = null;
  }
});

const origin = ref('杭州');
const destination = ref('全部');
const onlyAvailable = ref(true);
const sortBy = ref('recent-first');

// 本地瞬时首屏缓存 (实现 F5 刷新 0 毫秒秒开，彻底杜绝闪烁“未登录”与“有票(0)”)
function getInitialRoutes() {
  try {
    const c = localStorage.getItem('clairline_routes_cache');
    if (c) {
      const parsed = JSON.parse(c);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch (e) {}
  return [];
}

const availableRoutes = ref(getInitialRoutes());
const isInitialLoading = ref(availableRoutes.value.length === 0);
const seatCache = ref({});
const summary = ref({});
const patrolCount = ref(30);

// 航线监控实时状态
const patrolState = ref({
  running: false,
  mode: 'idle',
  completed: 0,
  total: 0,
  percent: 0,
  current_route: ''
});
// 全网普查动态全屏进度条模态框
const fullPatrolVisible = ref(false);

// 全局现代高质感 EXE 模态对话框 (支持普通提示与双选确认)
const appDialog = ref({
  visible: false,
  title: '系统提示',
  message: '',
  type: 'info',
  confirmText: '确定',
  cancelText: '取消',
  showCancel: false,
  onConfirm: null,
  onCancel: null
});

function showAppDialog(title, message, type = 'info', confirmText = '知道了') {
  appDialog.value = {
    visible: true,
    title,
    message,
    type,
    confirmText,
    cancelText: '',
    showCancel: false,
    onConfirm: null,
    onCancel: null
  };
}

function showAppConfirm({ title, message, type = 'warning', confirmText = '确定', cancelText = '取消' }) {
  return new Promise((resolve) => {
    appDialog.value = {
      visible: true,
      title: title || '请确认操作',
      message: message || '',
      type,
      confirmText,
      cancelText,
      showCancel: true,
      onConfirm: () => resolve(true),
      onCancel: () => resolve(false)
    };
  });
}

function handleDialogConfirm() {
  if (appDialog.value.onConfirm) {
    appDialog.value.onConfirm();
  }
  appDialog.value.visible = false;
}

function handleDialogCancel() {
  if (appDialog.value.onCancel) {
    appDialog.value.onCancel();
  }
  appDialog.value.visible = false;
}

function handleDialogClose() {
  if (appDialog.value.showCancel && appDialog.value.onCancel) {
    appDialog.value.onCancel();
  }
  appDialog.value.visible = false;
}

// 挂载到全局 window，供 AuthModal / PatrolModal 随时调起原生质感弹窗与确认框
if (typeof window !== 'undefined') {
  window.$dialog = showAppDialog;
  window.$confirm = showAppConfirm;
}

let patrolPollTimer = null;
let incrementalTick = 0;

const formatMiniCurrentRoute = computed(() => {
  const r = patrolState.value?.current_route;
  if (Array.isArray(r) && r.length >= 2) {
    return `${r[0]} ➔ ${r[1]}`;
  }
  if (typeof r === 'string' && r) return r;
  return '连接长龙航网数据中...';
});

async function checkPatrolStatus() {
  try {
    const res = await fetchPatrolStatus();
    if (res?.state) {
      const wasRunning = patrolState.value.running;
      patrolState.value = res.state;
      if (res.state.running) {
        if (!patrolPollTimer) {
          patrolPollTimer = setInterval(checkPatrolStatus, 1000);
        }
        // 后台普查期间每 4 秒静默增量刷新一次大盘航线，让用户看到新查出来的航线
        incrementalTick++;
        if (incrementalTick % 4 === 0) {
          initData();
        }
      } else {
        incrementalTick = 0;
        if (patrolPollTimer) {
          clearInterval(patrolPollTimer);
          patrolPollTimer = null;
        }
        if (wasRunning) {
          if (fullPatrolVisible.value) {
            fullPatrolVisible.value = false;
            showAppDialog('全网普查完成', '已完成全网航线机位探测普查，放票大盘已全面就绪！', 'success');
          } else {
            showToast('全网普查完成，放票日历已全面更新！');
          }
          initData();
        }
      }
    }
  } catch (e) {
    if (patrolPollTimer) {
      clearInterval(patrolPollTimer);
      patrolPollTimer = null;
    }
  }
}

function startPatrolPolling() {
  checkPatrolStatus();
  if (!patrolPollTimer) {
    patrolPollTimer = setInterval(checkPatrolStatus, 1000);
  }
}

// 模态框与抽屉
const drawerVisible = ref(false);
const selectedRoute = ref({});
const patrolModalVisible = ref(false);
const authModalVisible = ref(false);
const autoStartCaptureOnOpen = ref(false);
const updateModalVisible = ref(false);

function openAuthModal(autoStart = false) {
  autoStartCaptureOnOpen.value = autoStart;
  authModalVisible.value = true;
}

if (typeof window !== 'undefined') {
  window.$openAuthModal = openAuthModal;
}

const updateInfo = ref({
  has_update: false,
  current_version: 'v2.1.3',
  latest_version: 'v2.1.3',
  release_name: '',
  release_notes: '',
  page_url: 'https://github.com/eureka-wu/clairline/releases',
  download_url: 'https://github.com/eureka-wu/clairline/releases'
});

async function runCheckUpdate(manual = false) {
  try {
    const res = await checkSystemUpdate();
    if (res && res.ok) {
      updateInfo.value = res;
      const ignored = localStorage.getItem('ignored_update_version');
      if (res.has_update) {
        if (!manual && ignored === res.latest_version) {
          return;
        }
        updateModalVisible.value = true;
      } else {
        if (manual) {
          updateModalVisible.value = true;
        }
      }
    } else if (manual) {
      updateInfo.value = {
        has_update: false,
        current_version: 'v2.1.3',
        latest_version: 'v2.1.3',
        release_name: '长龙航空畅飞助手 v2.1.3',
        release_notes: '当前已是最新发布版本，暂无新版本发布。可访问 GitHub 开源仓库获取最新动态。',
        page_url: 'https://github.com/eureka-wu/clairline/releases'
      };
      updateModalVisible.value = true;
    }
  } catch (e) {
    if (manual) {
      updateInfo.value = {
        has_update: false,
        current_version: 'v2.1.3',
        latest_version: 'v2.1.3',
        release_name: '长龙航空畅飞助手 v2.1.3',
        release_notes: '当前已是最新发布版本。',
        page_url: 'https://github.com/eureka-wu/clairline/releases'
      };
      updateModalVisible.value = true;
    }
  }
}

function openUpdateModal() {
  runCheckUpdate(true);
}

function handleIgnoreVersion(ver) {
  showToast(`已跳过 ${ver} 的更新提示`);
}


function getInitialAuth() {
  try {
    const c = localStorage.getItem('clairline_auth_cache');
    if (c) {
      const parsed = JSON.parse(c);
      if (parsed && parsed.is_logged_in) return parsed;
    }
  } catch (e) {}
  return {
    is_logged_in: false,
    user_name: '长龙会员',
    mobile: '',
    member_level: '普通会员',
    cert_installed: false,
    update_time: ''
  };
}

const authStatus = ref(getInitialAuth());

async function refreshAuthStatus(directData) {
  if (directData && directData.is_logged_in) {
    authStatus.value = directData;
    return;
  }
  try {
    const res = await fetchAuthStatus();
    if (res && res.ok) {
      authStatus.value = res;
      try {
        if (res.is_logged_in && !res.is_expired) {
          localStorage.setItem('clairline_auth_cache', JSON.stringify(res));
        } else {
          localStorage.removeItem('clairline_auth_cache');
        }
      } catch (e) {}
    }
  } catch (e) {}
}

// 触发全网 397 条航线普查并调起全屏发光雷达扫描进度条
async function startFullPatrol() {
  // 立即乐观初始化状态，杜绝网络请求等待过程中的模式与总数闪烁
  patrolState.value = {
    ...patrolState.value,
    running: true,
    mode: 'all',
    total: patrolState.value.total > 0 ? patrolState.value.total : 397,
    percent: patrolState.value.percent || 2,
    current_route: patrolState.value.current_route || '连接长龙官方航网数据中...'
  };
  fullPatrolVisible.value = true;
  startPatrolPolling();
  try {
    const res = await triggerPatrol('all');
    if (res && res.ok) {
      if (!res.already_running) {
        showToast('已全自动启动全网 397 条直飞航线普查！');
      }
    } else {
      if (res?.error && !res.error.includes('已有巡检')) {
        showAppDialog('普查提示', res.error, 'warning');
      }
    }
  } catch (err) {
    showAppDialog('网络异常', '自动启动全网普查请求异常: ' + (err.message || '网络连接失败'), 'error');
  }
}

function handleFullPatrolCompleted() {
  fullPatrolVisible.value = false;
  showToast('全网 397 条直飞航线普查完毕，已全面更新入库！');
  initData();
}

function handlePatrolTriggered(mode = 'all') {
  if (mode) {
    patrolState.value.mode = mode;
    patrolState.value.running = true;
    if (mode === 'all') {
      patrolState.value.total = patrolState.value.total > 0 ? patrolState.value.total : 397;
    }
  }
  startPatrolPolling();
  if (patrolState.value.mode === 'all') {
    fullPatrolVisible.value = true;
  }
}

function handleOpenPatrol() {
  patrolModalVisible.value = true;
}

function handleExpandFull() {
  patrolModalVisible.value = false;
  fullPatrolVisible.value = true;
}

function handleMinimizePatrol() {
  fullPatrolVisible.value = false;
  showToast('已转入后台普查，可在右下角随时查看实时进度与重新展开！');
}

async function handleAuthSynced() {
  await refreshAuthStatus();
  if (!authStatus.value?.is_logged_in) {
    return;
  }
  showToast('长龙会员登录成功！已自动存入个人数据库');
  // 消除长龙官方接口异步网络时序差：延迟 600ms 与 1500ms 静默刷新，100% 自动显示真实姓名
  setTimeout(refreshAuthStatus, 600);
  setTimeout(refreshAuthStatus, 1500);
  initData();

  // 核心自动化流水线：仅在真实登录成功后才触发全网普查
  startFullPatrol();
}

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
let isHoveringPill = false;
let isHoveringPopover = false;

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

if (typeof window !== 'undefined') {
  window.$toast = showToast;
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
      try {
        localStorage.setItem('clairline_routes_cache', JSON.stringify(data.routes));
      } catch (e) {}
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

function cancelPopoverClose() {
  if (popoverCloseTimer) {
    clearTimeout(popoverCloseTimer);
    popoverCloseTimer = null;
  }
}

function schedulePopoverClose() {
  cancelPopoverClose();
  popoverCloseTimer = setTimeout(() => {
    // 用户核心需求：只有当鼠标既不在胶囊上、也不在气泡上，且当前未处于刷新中时才关闭！
    if (!isHoveringPill && !isHoveringPopover && !popover.value.loading) {
      popover.value.visible = false;
    }
  }, 280);
}

// 触摸已查验胶囊即显
function handleDateHover({ from, to, date, targetEl }) {
  isHoveringPill = true;
  cancelPopoverClose();
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

// 鼠标移出胶囊
function handleDateLeave() {
  isHoveringPill = false;
  schedulePopoverClose();
}

// 鼠标进入气泡主体内部保持显示
function handlePopoverEnter() {
  isHoveringPopover = true;
  cancelPopoverClose();
}

// 鼠标移出气泡主体关闭
function handlePopoverLeave() {
  isHoveringPopover = false;
  schedulePopoverClose();
}

// 点击具体出行日胶囊 (未查验的在此处发起联网查询)
async function handleDateClick({ from, to, date, targetEl }) {
  cancelPopoverClose();
  isHoveringPill = true;

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
      popover.value.visible = true; // 保持常驻
    } else {
      popover.value.loading = false;
      popover.value.flights = [];
      popover.value.visible = true;
    }
  } catch (e) {
    popover.value.loading = false;
    if (e.needLogin || (e.response && e.response.needLogin)) {
      popover.value.visible = false;
      showToast('实时查验具体机位需登录长龙会员账号');
      openAuthModal(true);
    } else {
      popover.value.visible = true;
      showToast(e.message || '查询航班异常，请重试');
    }
  }
}

// 微气泡内点击“刷新” (用户需求：点击后保持在原地，移走再消失)
async function handlePopoverRefresh({ fromCity, toCity, flightDate, targetEl }) {
  cancelPopoverClose();
  isHoveringPopover = true;
  popover.value.loading = true;
  popover.value.visible = true; // 强锁定显示状态

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
      popover.value.visible = true; // 刷新完成后依然稳稳留存在原位！
      showToast('最新票况已刷新！');
    } else {
      popover.value.loading = false;
      popover.value.visible = true;
    }
  } catch (e) {
    popover.value.loading = false;
    if (e.needLogin || (e.response && e.response.needLogin)) {
      popover.value.visible = false;
      showToast('实时刷新余票需登录长龙会员账号');
      openAuthModal(true);
    } else {
      popover.value.visible = true;
      showToast(e.message || '刷新余票异常');
    }
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
      const err = res.error || '';
      if (err.includes('过期') || err.includes('100001') || err.includes('未登录') || err.includes('未登入') || err.includes('失效') || res.authExpired) {
        await refreshAuthStatus();
        openAuthModal(true);
        return;
      }
      showToast(`刷新提示: ${err || '暂无新增'}`);
    }
  } catch (e) {
    const msg = e.message || '';
    if (msg.includes('过期') || msg.includes('100001') || msg.includes('未登录') || msg.includes('未登入') || msg.includes('失效')) {
      await refreshAuthStatus();
      openAuthModal(true);
      return;
    }
    showToast(`刷新提示: ${msg || '网络请求异常'}`);
  } finally {
    done();
  }
}

function openDrawer(route) {
  selectedRoute.value = route;
  drawerVisible.value = true;
}

onMounted(async () => {
  try {
    await Promise.all([
      initData(),
      refreshAuthStatus(),
      checkPatrolStatus(),
      runCheckUpdate(false)
    ]);
  } finally {
    isInitialLoading.value = false;
  }

  // 核心自动化机制：已登录但本地有票航线少于 50 条 (说明全网 397 条航线日历尚未普查全)，全自动调起全网普查！
  if (authStatus.value?.is_logged_in) {
    if (availableRoutes.value.length < 50 && !patrolState.value.running) {
      console.log('检测到尚未完成全网 397 条航线普查，全自动调起全网普查向导...');
      startFullPatrol();
    }
  }
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

/* 右下角高质感悬浮微型雷达进度卡片 */
.mini-patrol-widget {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(2, 132, 199, 0.35);
  box-shadow: 0 12px 32px rgba(2, 132, 199, 0.22), 0 2px 8px rgba(0, 0, 0, 0.08);
  border-radius: 16px;
  padding: 10px 14px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  user-select: none;
  max-width: 330px;
  width: calc(100vw - 48px);
}

.mini-patrol-widget:hover {
  transform: translateY(-3px) scale(1.02);
  border-color: rgba(2, 132, 199, 0.6);
  box-shadow: 0 16px 36px rgba(2, 132, 199, 0.3), 0 4px 12px rgba(0, 0, 0, 0.1);
}

.mini-widget-inner {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mini-radar-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35);
}

.mini-spin-radar {
  display: flex;
  font-size: 1.1rem;
  animation: radar-spin 2.5s linear infinite;
}

.mini-widget-body {
  flex: 1;
  min-width: 0;
}

.mini-widget-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2px;
}

.mini-badge-mode {
  font-size: 0.72rem;
  font-weight: 800;
  color: #0284c7;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  padding: 1px 6px;
  border-radius: 10px;
}

.mini-percent {
  font-size: 0.8rem;
  font-weight: 800;
  color: #0369a1;
}

.mini-route-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.73rem;
  color: #475569;
  margin-bottom: 4px;
}

.mini-route-text {
  font-weight: 700;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 140px;
}

.mini-counter {
  font-size: 0.7rem;
  color: #64748b;
  flex-shrink: 0;
}

.mini-progress-track {
  width: 100%;
  height: 5px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
}

.mini-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #0284c7 0%, #38bdf8 100%);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.mini-expand-btn {
  color: #0284c7;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  flex-shrink: 0;
  padding: 4px;
  border-radius: 6px;
  transition: transform 0.2s ease;
}

.mini-patrol-widget:hover .mini-expand-btn {
  transform: translateX(2px);
}

.mini-pop-enter-active,
.mini-pop-leave-active {
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.mini-pop-enter-from,
.mini-pop-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.9);
}

@keyframes radar-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.routes-loading-card {
  text-align: center;
  padding: 56px 20px;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.loading-spin-circle {
  width: 32px;
  height: 32px;
  border: 3px solid #e2e8f0;
  border-top-color: #0284c7;
  border-radius: 50%;
  animation: spinLoading 0.8s linear infinite;
}

@keyframes spinLoading {
  to { transform: rotate(360deg); }
}

.loading-main-title {
  font-size: 1rem;
  font-weight: 700;
  color: #1e293b;
}

.loading-sub-desc {
  font-size: 0.82rem;
  color: #64748b;
}
</style>
