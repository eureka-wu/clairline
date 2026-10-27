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

          <!-- 添加新航线录入框 (使用与主页相同的现代 el-select 组件) -->
          <div class="add-route-strip">
            <div class="city-pickers-row">
              <el-select
                v-model="newFrom"
                filterable
                :filter-method="filterOriginMethod"
                placeholder="出发地"
                class="custom-el-select modal-city-select"
              >
                <el-option
                  v-for="c in filteredOrigins"
                  :key="c"
                  :label="`${c} (${CITY_METADATA[c]?.province || ''})`"
                  :value="c"
                >
                  <div style="display:flex; justify-content:space-between; align-items:center; width:100%;">
                    <span style="font-weight:700;">{{ c }}</span>
                    <span style="font-size:0.75rem; color:#64748b;">{{ CITY_METADATA[c]?.province || '' }}</span>
                  </div>
                </el-option>
              </el-select>

              <span class="route-arrow-icon">➔</span>

              <el-select
                v-model="newTo"
                filterable
                :filter-method="filterDestMethod"
                placeholder="目的地"
                class="custom-el-select modal-city-select"
              >
                <el-option
                  v-for="c in filteredDests"
                  :key="c"
                  :label="`${c} (${CITY_METADATA[c]?.province || ''})`"
                  :value="c"
                >
                  <div style="display:flex; justify-content:space-between; align-items:center; width:100%;">
                    <span style="font-weight:700;">{{ c }}</span>
                    <span style="font-size:0.75rem; color:#64748b;">{{ CITY_METADATA[c]?.province || '' }}</span>
                  </div>
                </el-option>
              </el-select>
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
                <span class="plane-sym">➔</span>
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
              <div class="empty-title">暂未添加重点监控航线</div>
              <div class="empty-sub">可在上方选择城市并点击添加</div>
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

        <!-- ==================== TAB 2：全网普查 (极简一体化) ==================== -->
        <div v-show="activeTab === 'all'" class="tab-content">
          <!-- 全网普查设置一体化卡片 -->
          <div class="patrol-unified-card">
            <div class="unified-card-row">
              <label class="toggle-control-label">
                <input 
                  type="checkbox" 
                  :checked="switches.all_enabled" 
                  @change="onSwitchChange('all_enabled', $event.target.checked)"
                  class="custom-chk green-chk"
                >
                <span class="bold-label">每日定时自动普查</span>
              </label>
              <span class="count-tag green-tag">全网 397 航线</span>
            </div>

            <div class="unified-card-row time-row-sub">
              <span class="time-label-clean">执行时间:</span>
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
          </div>

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

      <!-- 模态框底部操作栏 (精简纯净，双Tab对称统一) -->
      <div class="modal-footer">
        <div class="footer-actions-group">
          <!-- Tab 1 重点监控立即巡检 -->
          <button 
            v-if="activeTab === 'hot'"
            type="button" 
            class="btn-trigger-action"
            :disabled="patrolState.running || routes.length === 0"
            @click="triggerManual('hot')"
          >
            <span>{{ patrolState.running && patrolState.mode === 'hot' ? '监控中...' : `▶ 立即巡检 (${routes.length})` }}</span>
          </button>

          <!-- Tab 2 全网大普查立即触发 -->
          <button 
            v-else
            type="button" 
            class="btn-trigger-action all-trigger-btn"
            :disabled="patrolState.running"
            @click="triggerManual('all')"
          >
            <span>{{ patrolState.running && patrolState.mode === 'all' ? '普查中...' : '▶ 立即全网普查 (397条)' }}</span>
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
import { CITY_METADATA } from '../data/city-meta.js';
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

// 拼音/文字搜索状态
const originQuery = ref('');
const destQuery = ref('');

function filterOriginMethod(query) {
  originQuery.value = query;
}

function filterDestMethod(query) {
  destQuery.value = query;
}

// 可出发城市 (按直达航线数量由多到少排序，常用城市居前)
const availableOrigins = computed(() => {
  return Object.keys(CITY_METADATA)
    .filter(c => (DIRECT_MAP[c] || []).length > 0)
    .sort((a, b) => (DIRECT_MAP[b] || []).length - (DIRECT_MAP[a] || []).length);
});

const filteredOrigins = computed(() => {
  const q = originQuery.value.trim().toLowerCase();
  if (!q) return availableOrigins.value;
  return availableOrigins.value.filter(c => {
    const meta = CITY_METADATA[c] || {};
    const pinyin = meta.pinyin || '';
    const prov = meta.province || '';
    return c.includes(q) || pinyin.toLowerCase().includes(q) || prov.includes(q) || (meta.code || '').toLowerCase().includes(q);
  });
});

const availableDestsForNew = computed(() => DIRECT_MAP[newFrom.value] || []);

const filteredDests = computed(() => {
  const q = destQuery.value.trim().toLowerCase();
  if (!q) return availableDestsForNew.value;
  return availableDestsForNew.value.filter(c => {
    const meta = CITY_METADATA[c] || {};
    const pinyin = meta.pinyin || '';
    const prov = meta.province || '';
    return c.includes(q) || pinyin.toLowerCase().includes(q) || prov.includes(q) || (meta.code || '').toLowerCase().includes(q);
  });
});

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

.modal-city-select {
  width: 152px;
  flex-shrink: 0;
}

:deep(.modal-city-select .el-select__wrapper) {
  min-height: 32px !important;
  height: 32px !important;
  padding: 0 8px !important;
  font-size: 0.82rem !important;
  font-weight: 700;
  border-radius: 6px !important;
  box-shadow: 0 0 0 1px #cbd5e1 inset !important;
}

:deep(.modal-city-select .el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1.5px #0284c7 inset !important;
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

/* 全网普查设置一体化卡片 */
.patrol-unified-card {
  display: flex;
  flex-direction: column;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
  gap: 10px;
}

.unified-card-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.unified-card-row.time-row-sub {
  justify-content: flex-start;
  gap: 10px;
  padding-top: 10px;
  border-top: 1px dashed #e2e8f0;
  flex-wrap: wrap;
}

.bold-label {
  font-size: 0.84rem;
  font-weight: 700;
  color: #0f172a;
}

.time-label-clean {
  font-size: 0.78rem;
  font-weight: 600;
  color: #475569;
  flex-shrink: 0;
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

/* 底部操作栏 (精炼纯净) */
.modal-footer {
  padding: 12px 18px;
  border-top: 1px solid #f1f5f9;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.footer-actions-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.all-trigger-btn {
  background: #f0fdf4 !important;
  border: 1px solid #86efac !important;
  color: #15803d !important;
}
.all-trigger-btn:hover:not(:disabled) {
  background: #dcfce7 !important;
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

  .modal-city-select {
    flex: 1 1 0;
    min-width: 0;
    width: auto !important;
  }

  :deep(.modal-city-select .el-select__wrapper) {
    min-height: 34px !important;
    height: 34px !important;
    padding: 0 6px !important;
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
    padding: 12px 14px calc(12px + env(safe-area-inset-bottom));
  }

  .footer-actions-group {
    width: 100%;
    gap: 8px;
  }

  .btn-trigger-action {
    flex: 1;
    height: 38px;
    font-size: 0.82rem;
  }

  .btn-save-primary {
    flex: 1;
    height: 38px;
    font-size: 0.84rem;
  }
}

@keyframes slideUpModal {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}
</style>
