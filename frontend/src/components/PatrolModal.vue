<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-card">
      <!-- 模态框头部 -->
      <div class="modal-header">
        <div class="header-title-box">
          <span class="header-radar-icon" v-html="ICONS.radar"></span>
          <span>航线巡检配置</span>
        </div>
        <button type="button" class="btn-modal-close" @click="$emit('close')">&times;</button>
      </div>

      <!-- 现代分段切换器 (Segmented Pills) -->
      <div class="modal-tabs-wrapper">
        <div class="modal-tab-segmented">
          <button 
            type="button" 
            class="tab-pill"
            :class="{ active: activeTab === 'hot' }"
            @click="activeTab = 'hot'"
          >
            <span v-html="ICONS.star"></span>
            <span>重点监控 ({{ routes.length }})</span>
          </button>
          <button 
            type="button" 
            class="tab-pill"
            :class="{ active: activeTab === 'all' }"
            @click="activeTab = 'all'"
          >
            <span v-html="ICONS.globe"></span>
            <span>全网普查 (397条)</span>
          </button>
        </div>
      </div>

      <!-- 模态框主体 -->
      <div class="modal-body">
        
        <!-- ==================== TAB 1：重点监控航线 ==================== -->
        <div v-show="activeTab === 'hot'" class="tab-content">
          <!-- 自动化轮巡微配置条 -->
          <div class="patrol-config-bar">
            <div class="config-bar-left">
              <span class="count-tag">已关注 {{ routes.length }} 条</span>
            </div>
            
            <div class="config-bar-right">
              <label class="toggle-control-label">
                <input 
                  type="checkbox" 
                  :checked="switches.hot_enabled" 
                  @change="onSwitchChange('hot_enabled', $event.target.checked)"
                  class="custom-chk"
                >
                <span>自动轮巡</span>
              </label>

              <div class="interval-input-group">
                <span>每</span>
                <input 
                  type="number" 
                  v-model.number="hotIntervalMinutes" 
                  min="5" 
                  max="720" 
                  class="input-minutes"
                >
                <span>分钟</span>
              </div>
            </div>
          </div>

          <!-- 添加新航线录入框 (极简通透一行) -->
          <div class="add-route-strip">
            <div class="city-pickers-row">
              <select v-model="newFrom" class="select-clean">
                <option v-for="c in availableOrigins" :key="c" :value="c">{{ c }}</option>
              </select>
              <span class="route-arrow-icon">➔</span>
              <select v-model="newTo" class="select-clean">
                <option v-for="c in availableDestsForNew" :key="c" :value="c">{{ c }}</option>
              </select>
            </div>
            <input 
              type="text" 
              v-model="newRouteName" 
              placeholder="备注 (选填)"
              class="input-remark-clean"
              @keydown.enter="addRoute"
            >
            <button 
              type="button" 
              class="btn-add-action" 
              :disabled="!newFrom || !newTo"
              @click="addRoute"
            >
              + 添加
            </button>
          </div>

          <!-- 航线卡片列表流 (替代陈旧表格) -->
          <div class="route-cards-list">
            <div 
              v-for="(r, idx) in routes" 
              :key="`${r.from}-${r.to}-${idx}`"
              class="route-card-item"
            >
              <span class="route-index">{{ String(idx + 1).padStart(2, '0') }}</span>
              <div class="route-cities">
                <span class="city-name">{{ r.from }}</span>
                <span class="plane-sym">✈</span>
                <span class="city-name">{{ r.to }}</span>
              </div>
              <input 
                type="text" 
                v-model="r.name" 
                class="route-inline-remark"
                placeholder="点击添加备注"
                title="点击可直接修改此航线备注"
              >
              <button 
                type="button" 
                class="btn-remove-icon" 
                @click="removeRoute(idx)"
                title="移除此关注航线"
              >
                &times;
              </button>
            </div>

            <div v-if="routes.length === 0" class="empty-state-box">
              <div class="empty-icon">🛫</div>
              <div class="empty-title">暂未添加重点监控航线</div>
              <div class="empty-sub">可在上方选择城市添加，或点击下方导入示例</div>
            </div>
          </div>

          <!-- 巡检实时运行中指示器 -->
          <div v-if="(patrolState.mode === 'hot' || !patrolState.mode) && (patrolState.running || patrolState.percent > 0)" class="running-progress-card">
            <div class="running-header">
              <span class="running-text">⚡ 重点巡检中: {{ currentRouteDisplay }} ({{ patrolState.completed }}/{{ patrolState.total || routes.length }})</span>
              <span class="running-pct">{{ patrolState.percent }}%</span>
            </div>
            <div class="progress-track">
              <div class="progress-bar-inner hot-bar" :style="{ width: `${patrolState.percent}%` }"></div>
            </div>
          </div>
        </div>

        <!-- ==================== TAB 2：全网普查 (极简紧致) ==================== -->
        <div v-show="activeTab === 'all'" class="tab-content">
          <!-- 顶部轻量配置条 (与 Tab 1 严格统一) -->
          <div class="patrol-config-bar">
            <div class="config-bar-left">
              <span class="count-tag green-tag">全国直飞 397 条</span>
            </div>
            
            <div class="config-bar-right">
              <label class="toggle-control-label">
                <input 
                  type="checkbox" 
                  :checked="switches.all_enabled" 
                  @change="onSwitchChange('all_enabled', $event.target.checked)"
                  class="custom-chk green-chk"
                >
                <span>每日定时自动普查</span>
              </label>
            </div>
          </div>

          <!-- 定时时间点微药丸行 -->
          <div class="clean-time-row">
            <span class="time-row-label">执行时间点:</span>
            <div class="time-pills-row">
              <span 
                v-for="(t, idx) in patrolTimes" 
                :key="idx"
                class="time-badge"
              >
                <span>{{ t }}</span>
                <button type="button" class="btn-time-remove" @click="removeTime(idx)">&times;</button>
              </span>

              <div v-if="patrolTimes.length < 3" class="time-add-wrap">
                <input type="time" v-model="newTime" class="input-time-picker">
                <button type="button" class="btn-time-add" @click="addTime">+ 添加</button>
              </div>
            </div>
          </div>

          <!-- 全网普查启动按钮 -->
          <button 
            type="button" 
            class="btn-full-patrol-trigger"
            :disabled="patrolState.running"
            @click="triggerManual('all')"
          >
            <span v-html="ICONS.rocket"></span>
            <span>{{ patrolState.running && patrolState.mode === 'all' ? '正在全网大普查中...' : '立即开始全网大普查 (397条)' }}</span>
          </button>

          <!-- 实时进度条 -->
          <div v-if="patrolState.mode === 'all' && (patrolState.running || patrolState.percent > 0)" class="running-progress-card">
            <div class="running-header">
              <span class="running-text">🌐 全网大普查中: {{ currentRouteDisplay }} ({{ patrolState.completed }}/{{ patrolState.total || 397 }})</span>
              <span class="running-pct">{{ patrolState.percent }}%</span>
            </div>
            <div class="progress-track">
              <div class="progress-bar-inner all-bar" :style="{ width: `${patrolState.percent}%` }"></div>
            </div>
          </div>
        </div>

      </div>

      <!-- 模态框底部操作栏 (精简低噪，Tab 严格隔离) -->
      <div class="modal-footer">
        <!-- 仅在重点监控 Tab 显示清空与导入 -->
        <div v-if="activeTab === 'hot'" class="footer-links-group">
          <button type="button" class="link-btn text-danger" @click="clearAllRoutes">清空</button>
          <span class="divider">·</span>
          <button type="button" class="link-btn text-primary" @click="importExampleRoutes">导入示例(30条)</button>
        </div>
        <div v-else class="footer-links-group">
          <span style="font-size:0.75rem; color:#94a3b8;">多线程并发遍历 · 覆盖数据库放票日历</span>
        </div>

        <div class="footer-actions-group">
          <button 
            v-if="activeTab === 'hot'"
            type="button" 
            class="btn-trigger-action"
            :disabled="patrolState.running || routes.length === 0"
            @click="triggerManual('hot')"
          >
            <span>{{ patrolState.running && patrolState.mode === 'hot' ? '监控中...' : `▶ 立即巡检 (${routes.length})` }}</span>
          </button>
          <button type="button" class="btn-save-primary" @click="saveAll">
            保存配置
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { ICONS } from '../data/icons.js';
import { DIRECT_MAP } from '../data/routes-network.js';
import { 
  fetchPatrolHotRoutes,
  savePatrolHotRoutes,
  fetchPatrolTimes, 
  savePatrolTimes, 
  fetchPatrolSwitches, 
  savePatrolSwitches, 
  triggerPatrol 
} from '../api/patrol.js';

const props = defineProps({
  visible: Boolean,
  patrolState: {
    type: Object,
    default: () => ({ running: false, mode: 'idle', completed: 0, total: 0, percent: 0, current_route: '' })
  }
});

const emit = defineEmits(['close', 'saved', 'triggered', 'expand-full']);

const activeTab = ref('hot');
const routes = ref([]);
const patrolTimes = ref(['08:30', '20:00']);
const switches = ref({ hot_enabled: false, all_enabled: false });
const hotIntervalMinutes = ref(25);

const newFrom = ref('杭州');
const newTo = ref('阿勒泰');
const newRouteName = ref('');
const newTime = ref('12:00');

const availableOrigins = computed(() => Object.keys(DIRECT_MAP).filter(c => (DIRECT_MAP[c] || []).length > 0));
const availableDestsForNew = computed(() => DIRECT_MAP[newFrom.value] || []);

const currentRouteDisplay = computed(() => {
  const cr = props.patrolState.current_route;
  if (!cr) return '准备中...';
  if (Array.isArray(cr) && cr.length >= 2) {
    return `${cr[0]} ➔ ${cr[1]}`;
  }
  return String(cr);
});

watch(newFrom, (val) => {
  const dests = DIRECT_MAP[val] || [];
  if (!dests.includes(newTo.value)) {
    newTo.value = dests[0] || '';
  }
});

async function loadData() {
  try {
    const [hotRes, timesRes, swRes] = await Promise.all([
      fetchPatrolHotRoutes(),
      fetchPatrolTimes(),
      fetchPatrolSwitches()
    ]);
    if (hotRes?.routes && Array.isArray(hotRes.routes)) {
      routes.value = hotRes.routes.map(item => {
        if (typeof item === 'object' && item !== null && !Array.isArray(item)) {
          return {
            from: item.from,
            to: item.to,
            name: item.name || `${item.from} ➔ ${item.to}`
          };
        }
        if (Array.isArray(item) && item.length >= 2) {
          return {
            from: item[0],
            to: item[1],
            name: `${item[0]} ➔ ${item[1]}`
          };
        }
        return null;
      }).filter(Boolean);
      if (hotRes.interval_minutes) {
        hotIntervalMinutes.value = hotRes.interval_minutes;
      }
    }
    if (timesRes?.times && Array.isArray(timesRes.times)) {
      patrolTimes.value = timesRes.times;
    }
    if (swRes?.switches) {
      switches.value = swRes.switches;
    }
  } catch (e) {
    console.error('加载监控配置异常:', e);
  }
}

onMounted(() => {
  loadData();
});

watch(() => props.visible, (val) => {
  if (val) loadData();
});

function addRoute() {
  if (!newFrom.value || !newTo.value) return;
  const exists = routes.value.some(r => r.from === newFrom.value && r.to === newTo.value);
  if (exists) {
    if (typeof window !== 'undefined' && window.$toast) {
      window.$toast(`已存在监控航线: ${newFrom.value} ➔ ${newTo.value}`);
    } else {
      alert(`已存在监控航线: ${newFrom.value} ➔ ${newTo.value}`);
    }
    return;
  }
  routes.value.unshift({
    from: newFrom.value,
    to: newTo.value,
    name: newRouteName.value.trim() || `${newFrom.value} ➔ ${newTo.value}`
  });
  newRouteName.value = '';
}

function removeRoute(idx) {
  routes.value.splice(idx, 1);
}

function clearAllRoutes() {
  if (routes.value.length === 0) return;
  const doClear = () => {
    routes.value = [];
  };
  if (typeof window !== 'undefined' && window.$confirm) {
    window.$confirm('清空关注航线', '确定清空所有已关注的监控航线吗？', doClear, { type: 'danger', confirmText: '清空' });
  } else if (confirm('确定清空所有已关注的监控航线吗？')) {
    doClear();
  }
}

function importExampleRoutes() {
  const exampleHubs = [
    { from: '杭州', to: '阿勒泰', name: '雪都滑雪度假' },
    { from: '杭州', to: '哈尔滨', name: '冰雪大世界' },
    { from: '杭州', to: '长春', name: '东北长白山' },
    { from: '杭州', to: '银川', name: '大漠塞上江南' },
    { from: '杭州', to: '喀什', name: '南疆古城丝路' },
    { from: '杭州', to: '西双版纳', name: '热带雨林避寒' },
    { from: '杭州', to: '三亚', name: '热带海岛暖冬' },
    { from: '杭州', to: '海口', name: '海南环岛自由行' },
    { from: '杭州', to: '乌鲁木齐', name: '新疆核心大本营' },
    { from: '杭州', to: '阿克苏', name: '南疆苹果之乡' },
    { from: '杭州', to: '海拉尔', name: '呼伦贝尔大草原' },
    { from: '杭州', to: '丽江', name: '云南丽江古城' },
    { from: '杭州', to: '成都', name: '天府美食慢生活' },
    { from: '杭州', to: '重庆', name: '魔幻山城火锅' },
    { from: '杭州', to: '西安', name: '千年古都十三朝' },
    { from: '杭州', to: '郑州', name: '中原少林文化' },
    { from: '杭州', to: '北京', name: '首都政经枢纽' },
    { from: '杭州', to: '深圳', name: '大湾区科技前沿' },
    { from: '杭州', to: '广州', name: '羊城早茶食在广州' },
    { from: '杭州', to: '武汉', name: '九省通衢楚天阔' },
    { from: '银川', to: '杭州', name: '江南水乡返程' },
    { from: '银川', to: '宁波', name: '东海港口商务' },
    { from: '长春', to: '杭州', name: '长三角大本营直达' },
    { from: '宁波', to: '重庆', name: '沿海通达巴蜀' },
    { from: '宁波', to: '成都', name: '蓉城天府互通' },
    { from: '温州', to: '贵阳', name: '山水爽爽贵阳' },
    { from: '温州', to: '武汉', name: '华中经贸要道' },
    { from: '杭州', to: '贵阳', name: '黔灵甲天下' },
    { from: '杭州', to: '昆明', name: '春城彩云之南' },
    { from: '杭州', to: '南宁', name: '北部湾东盟门户' }
  ];

  const doImport = () => {
    const existingPairs = new Set(routes.value.map(r => `${r.from}-${r.to}`));
    let added = 0;
    exampleHubs.forEach(h => {
      const pair = `${h.from}-${h.to}`;
      if (!existingPairs.has(pair)) {
        routes.value.push(h);
        existingPairs.add(pair);
        added++;
      }
    });
    if (typeof window !== 'undefined' && window.$toast) {
      window.$toast(`已导入 ${added} 条核心示例航线`);
    }
  };

  if (typeof window !== 'undefined' && window.$confirm) {
    window.$confirm('导入常用示例航线', '将导入长龙官方 30 条核心文旅与公商务主力航线，是否导入？', doImport, { type: 'primary', confirmText: '导入' });
  } else {
    doImport();
  }
}

function addTime() {
  if (!newTime.value) return;
  if (patrolTimes.value.includes(newTime.value)) return;
  if (patrolTimes.value.length >= 3) return;
  patrolTimes.value.push(newTime.value);
  patrolTimes.value.sort();
}

function removeTime(idx) {
  patrolTimes.value.splice(idx, 1);
}

function onSwitchChange(key, checked) {
  switches.value[key] = checked;
}

async function triggerManual(mode) {
  try {
    const res = await triggerPatrol(mode);
    if (res && res.ok) {
      emit('triggered', mode);
      if (mode === 'all') {
        emit('expand-full');
      }
    } else {
      const err = res?.error || '';
      if (err.includes('过期') || err.includes('100001') || err.includes('未登录') || err.includes('失效') || err.includes('授权') || err.includes('400')) {
        emit('close');
        if (typeof window !== 'undefined' && window.$openAuthModal) {
          window.$openAuthModal(true);
        }
        return;
      }
      if (typeof window !== 'undefined' && window.$dialog) {
        window.$dialog('提示', err || '未能成功触发巡检', 'warning');
      } else {
        alert(err || '未能成功触发巡检');
      }
    }
  } catch (e) {
    const msg = e.message || '';
    if (typeof window !== 'undefined' && window.$dialog) {
      window.$dialog('操作失败', msg || '网络请求异常', 'error');
    } else {
      alert(msg || '触发失败');
    }
  }
}

async function saveAll() {
  try {
    const payload = routes.value.map(r => ({
      from: r.from,
      to: r.to,
      name: r.name || `${r.from} ➔ ${r.to}`
    }));
    await Promise.all([
      savePatrolHotRoutes(payload, hotIntervalMinutes.value),
      savePatrolTimes(patrolTimes.value),
      savePatrolSwitches(switches.value.hot_enabled, switches.value.all_enabled)
    ]);
    emit('saved');
    emit('close');
    if (typeof window !== 'undefined' && window.$toast) {
      window.$toast('监控配置已保存！');
    }
  } catch (e) {
    console.error('保存监控配置失败:', e);
    alert('保存配置失败，请检查服务连接');
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-card {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 24px 48px -12px rgba(15, 23, 42, 0.25);
  border: 1px solid rgba(226, 232, 240, 0.8);
  width: 100%;
  max-width: 580px;
  max-height: 86vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modalPop 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

/* 模态框头部 */
.modal-header {
  padding: 14px 18px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title-box {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 800;
  font-size: 1.02rem;
  color: #0f172a;
  letter-spacing: -0.01em;
}

.header-radar-icon {
  display: inline-flex;
  color: #0284c7;
}

.btn-modal-close {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: #f1f5f9;
  color: #64748b;
  font-size: 1.2rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-modal-close:hover {
  background: #e2e8f0;
  color: #0f172a;
}

/* 胶囊分段导航 (Segmented Tabs) */
.modal-tabs-wrapper {
  padding: 10px 18px 0;
  background: #ffffff;
}

.modal-tab-segmented {
  display: flex;
  background: #f1f5f9;
  padding: 3px;
  border-radius: 10px;
  gap: 4px;
}

.tab-pill {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 7px 12px;
  border-radius: 8px;
  border: none;
  background: transparent;
  font-size: 0.82rem;
  font-weight: 700;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-pill.active {
  background: #ffffff;
  color: #0284c7;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

/* 模态框主体 */
.modal-body {
  padding: 14px 18px;
  overflow-y: auto;
  flex: 1;
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 顶部轻量配置条 */
.patrol-config-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

.count-tag {
  font-size: 0.76rem;
  font-weight: 700;
  color: #0369a1;
  background: #e0f2fe;
  padding: 2px 8px;
  border-radius: 6px;
}

.config-bar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toggle-control-label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.78rem;
  font-weight: 600;
  color: #334155;
  cursor: pointer;
}

.custom-chk {
  accent-color: #0284c7;
  width: 15px;
  height: 15px;
}
.custom-chk.green-chk {
  accent-color: #059669;
}

.interval-input-group {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.76rem;
  color: #64748b;
}

.input-minutes {
  width: 44px;
  height: 26px;
  text-align: center;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 700;
  color: #0f172a;
  outline: none;
}
.input-minutes:focus {
  border-color: #0284c7;
}

/* 添加新航线录入框 (极简通透一行) */
.add-route-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

.city-pickers-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.select-clean {
  height: 32px;
  padding: 0 6px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.82rem;
  font-weight: 700;
  color: #0f172a;
  background: #ffffff;
  outline: none;
  cursor: pointer;
}

.select-clean:focus {
  border-color: #0284c7;
}

.route-arrow-icon {
  font-size: 0.75rem;
  color: #94a3b8;
  font-weight: 700;
}

.input-remark-clean {
  flex: 1;
  min-width: 0;
  height: 32px;
  padding: 0 8px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.8rem;
  outline: none;
}
.input-remark-clean:focus {
  border-color: #0284c7;
}

.btn-add-action {
  height: 32px;
  padding: 0 14px;
  border: none;
  background: #0284c7;
  color: #ffffff;
  font-size: 0.82rem;
  font-weight: 700;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}
.btn-add-action:hover:not(:disabled) {
  background: #0369a1;
}
.btn-add-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 航线卡片流 */
.route-cards-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 250px;
  overflow-y: auto;
  padding-right: 2px;
}

.route-card-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #ffffff;
  border: 1px solid #f1f5f9;
  border-radius: 8px;
  transition: all 0.2s;
}

.route-card-item:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.route-index {
  font-size: 0.72rem;
  font-weight: 800;
  color: #94a3b8;
  width: 20px;
}

.route-cities {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 800;
  font-size: 0.85rem;
  color: #0f172a;
}

.plane-sym {
  font-size: 0.75rem;
  color: #0284c7;
}

.route-inline-remark {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  font-size: 0.78rem;
  color: #64748b;
  padding: 2px 4px;
  outline: none;
  border-radius: 4px;
}
.route-inline-remark:focus {
  background: #ffffff;
  box-shadow: 0 0 0 1px #0284c7;
  color: #0f172a;
}

.btn-remove-icon {
  width: 22px;
  height: 22px;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.btn-remove-icon:hover {
  background: #fee2e2;
  color: #ef4444;
}

/* 空状态 */
.empty-state-box {
  padding: 32px 16px;
  text-align: center;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px dashed #e2e8f0;
}
.empty-icon {
  font-size: 1.6rem;
  margin-bottom: 4px;
}
.empty-title {
  font-weight: 700;
  font-size: 0.85rem;
  color: #475569;
}
.empty-sub {
  font-size: 0.74rem;
  color: #94a3b8;
  margin-top: 2px;
}

/* 进度条 */
.running-progress-card {
  padding: 8px 12px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
}
.running-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.75rem;
  font-weight: 700;
  color: #15803d;
  margin-bottom: 6px;
}
.progress-track {
  width: 100%;
  height: 6px;
  background: #dcfce7;
  border-radius: 3px;
  overflow: hidden;
}
.progress-bar-inner {
  height: 100%;
  transition: width 0.3s ease;
}
.hot-bar {
  background: linear-gradient(90deg, #0284c7, #38bdf8);
}
.all-bar {
  background: linear-gradient(90deg, #10b981, #059669);
}

/* Tab 2 全网普查极简定时行 */
.count-tag.green-tag {
  background: #ecfdf5;
  color: #047857;
}

.clean-time-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  gap: 8px;
  flex-wrap: wrap;
}

.time-row-label {
  font-size: 0.78rem;
  font-weight: 700;
  color: #334155;
}

.time-pills-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.time-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: #ffffff;
  border: 1px solid #a7f3d0;
  color: #047857;
  font-weight: 700;
  font-size: 0.78rem;
  border-radius: 6px;
}
.btn-time-remove {
  border: none;
  background: transparent;
  color: #059669;
  cursor: pointer;
  font-size: 0.9rem;
  padding: 0;
  line-height: 1;
}

.time-add-wrap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.input-time-picker {
  height: 26px;
  padding: 0 4px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.75rem;
}
.btn-time-add {
  height: 26px;
  padding: 0 8px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
}

.btn-full-patrol-trigger {
  width: 100%;
  height: 40px;
  border: none;
  background: linear-gradient(135deg, #059669, #047857);
  color: #ffffff;
  font-size: 0.86rem;
  font-weight: 800;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  box-shadow: 0 2px 8px rgba(5, 150, 105, 0.25);
  transition: all 0.2s;
}
.btn-full-patrol-trigger:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(5, 150, 105, 0.35);
  transform: translateY(-1px);
}
.btn-full-patrol-trigger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 底部操作栏 (精炼对齐) */
.modal-footer {
  padding: 12px 18px;
  border-top: 1px solid #f1f5f9;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.footer-links-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.link-btn {
  border: none;
  background: transparent;
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}
.link-btn.text-danger { color: #ef4444; }
.link-btn.text-danger:hover { text-decoration: underline; }
.link-btn.text-primary { color: #0284c7; }
.link-btn.text-primary:hover { text-decoration: underline; }

.divider {
  color: #cbd5e1;
  font-size: 0.7rem;
}

.footer-actions-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-trigger-action {
  height: 34px;
  padding: 0 14px;
  border: 1px solid #bbf7d0;
  background: #f0fdf4;
  color: #15803d;
  font-size: 0.8rem;
  font-weight: 700;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-trigger-action:hover:not(:disabled) {
  background: #dcfce7;
}

.btn-save-primary {
  height: 34px;
  padding: 0 18px;
  border: none;
  background: #0284c7;
  color: #ffffff;
  font-size: 0.82rem;
  font-weight: 700;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-save-primary:hover {
  background: #0369a1;
}

@keyframes modalPop {
  from { opacity: 0; transform: scale(0.96); }
  to { opacity: 1; transform: scale(1); }
}

/* 移动端专属适配 (Bottom Sheet) */
@media (max-width: 768px) {
  .modal-overlay {
    align-items: flex-end !important;
    padding: 0 !important;
  }

  .modal-card {
    width: 100% !important;
    max-width: 100% !important;
    max-height: 88vh !important;
    border-radius: 20px 20px 0 0 !important;
    border-bottom: none;
    animation: slideUpModal 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
  }

  .modal-header {
    padding: 12px 16px;
  }

  .modal-body {
    padding: 12px 14px !important;
  }

  .modal-tabs-wrapper {
    padding: 8px 14px 0;
  }

  .add-route-strip {
    flex-wrap: wrap;
    gap: 6px;
  }

  .city-pickers-row {
    width: 100%;
    justify-content: space-between;
  }

  .select-clean {
    flex: 1;
    height: 34px;
  }

  .input-remark-clean {
    width: 100%;
    min-width: 100%;
    height: 34px;
  }

  .btn-add-action {
    width: 100%;
    height: 34px;
  }

  .route-cards-list {
    max-height: 220px;
  }

  .modal-footer {
    padding: 10px 14px calc(12px + env(safe-area-inset-bottom));
    flex-direction: column-reverse;
    gap: 10px;
  }

  .footer-actions-group {
    width: 100%;
    gap: 8px;
  }

  .btn-trigger-action {
    flex: 1;
    height: 38px;
  }

  .btn-save-primary {
    flex: 1.4;
    height: 38px;
    font-size: 0.86rem;
  }

  .footer-links-group {
    width: 100%;
    justify-content: center;
  }
}

@keyframes slideUpModal {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}
</style>
