<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-card">
      <!-- 模态框头部 -->
      <div class="modal-header">
        <div style="font-weight:800; font-size:1.05rem; display:flex; align-items:center; gap:8px;">
          <span v-html="ICONS.radar" style="color:var(--accent-cyan);"></span>
          <span>航线监控与全网普查</span>
        </div>
        <button type="button" class="btn-popover-close" style="font-size:1.3rem;" @click="$emit('close')">&times;</button>
      </div>

      <!-- 双模式切换 Tab 标签导航 (各自独立，清晰分明) -->
      <div class="patrol-tab-bar">
        <button 
          type="button" 
          class="patrol-tab-item"
          :class="{ active: activeTab === 'hot' }"
          @click="activeTab = 'hot'"
        >
          <span v-html="ICONS.star" style="display:inline-flex;"></span>
          <span>重点监控航线 (已关注 {{ routes.length }} 条)</span>
        </button>
        <button 
          type="button" 
          class="patrol-tab-item tab-all"
          :class="{ active: activeTab === 'all' }"
          @click="activeTab = 'all'"
        >
          <span v-html="ICONS.globe" style="display:inline-flex;"></span>
          <span>全网航网普查 (全量直飞拓扑)</span>
        </button>
      </div>

      <!-- 模态框主体 -->
      <div class="modal-body" style="padding:16px 20px;">
        
        <!-- ==================== 选项卡 1：重点监控航线 (表格列表，不设上限) ==================== -->
        <div v-show="activeTab === 'hot'">
          <!-- 状态与定时批次配置条 -->
          <div class="patrol-bar-status">
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="seat-badge">
                已关注重点航线: {{ routes.length }} 条 · 不设上限
              </span>
            </div>
            
            <!-- 自动轮巡总开关与时间批次调节 -->
            <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
              <label style="display:inline-flex; align-items:center; gap:6px; cursor:pointer; font-size:0.75rem; font-weight:700; color:#334155;">
                <input 
                  type="checkbox" 
                  :checked="switches.hot_enabled" 
                  @change="onSwitchChange('hot_enabled', $event.target.checked)"
                  style="accent-color:#0284c7;"
                >
                <span>后台自动轮巡: {{ switches.hot_enabled ? '已启用' : '已停用' }}</span>
              </label>

              <!-- 时间批次可调 (多少分钟查一次) -->
              <div style="display:inline-flex; align-items:center; gap:4px; font-size:0.75rem; color:#475569;">
                <span>每</span>
                <input 
                  type="number" 
                  v-model.number="hotIntervalMinutes" 
                  min="5" 
                  max="720" 
                  class="custom-number-input"
                  title="后台巡检周期时间间隔 (分钟)"
                >
                <span>分钟巡检一次</span>
              </div>
            </div>
          </div>

          <!-- 添加新航线行 (置顶快捷录入) -->
          <div class="add-route-card">
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
              <select v-model="newFrom" class="custom-select-native" style="padding:4px 8px; font-size:0.8rem;">
                <option v-for="c in availableOrigins" :key="c" :value="c">{{ c }}</option>
              </select>
              <span style="color:#94a3b8; font-weight:bold;">➔</span>
              <select v-model="newTo" class="custom-select-native" style="padding:4px 8px; font-size:0.8rem;">
                <option v-for="c in availableDestsForNew" :key="c" :value="c">{{ c }}</option>
              </select>
              <input 
                type="text" 
                v-model="newRouteName" 
                placeholder="航线别名/备注 (选填，如我的老家/度假专线)"
                class="route-remark-input"
                @keydown.enter="addRoute"
              >
              <button 
                type="button" 
                class="btn-primary" 
                style="padding:5px 14px; font-size:0.78rem; display:inline-flex; align-items:center; gap:4px;" 
                :disabled="!newFrom || !newTo"
                @click="addRoute"
              >
                <span>➕ 加入重点监控</span>
              </button>
            </div>
          </div>

          <!-- 重点监控航线列表 (表格形式，每行带配置名称，支持上下滚动) -->
          <div class="route-table-wrapper">
            <table class="route-table">
              <thead>
                <tr>
                  <th style="width:44px; text-align:center;">#</th>
                  <th style="width:200px; text-align:left;">配置名称 / 航线备注</th>
                  <th style="text-align:left;">航线方向 (出发 ➔ 到达)</th>
                  <th style="width:68px; text-align:center;">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(r, idx) in routes" :key="`${r.from}-${r.to}-${idx}`" class="route-table-row">
                  <td style="text-align:center; font-weight:700; color:#64748b; font-size:0.75rem;">
                    {{ String(idx + 1).padStart(2, '0') }}
                  </td>
                  <td>
                    <input 
                      type="text" 
                      v-model="r.name" 
                      class="route-name-input"
                      placeholder="未命名 (点击输入备注)"
                      title="点击即可直接修改此航线备注"
                    >
                  </td>
                  <td>
                    <span class="route-direction-badge">
                      <span class="city-from">{{ r.from }}</span>
                      <span class="route-arrow">✈</span>
                      <span class="city-to">{{ r.to }}</span>
                    </span>
                  </td>
                  <td style="text-align:center;">
                    <button 
                      type="button" 
                      class="btn-remove-row" 
                      @click="removeRoute(idx)"
                      title="移除此关注航线"
                    >
                      移除
                    </button>
                  </td>
                </tr>
                <tr v-if="routes.length === 0">
                  <td colspan="4" class="empty-table-cell">
                    <div style="font-size:1.3rem; margin-bottom:6px;">✈️</div>
                    <div style="font-weight:700; color:#475569; margin-bottom:4px; font-size:0.85rem;">当前暂未添加重点航线 (默认 0 个，不设上限)</div>
                    <div style="font-size:0.75rem; color:#94a3b8;">请在上方选择城市随心添加，或点击左下角一键导入常用示例</div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 手动即时触发栏 -->
          <div class="trigger-card hot-trigger-card">
            <div>
              <div style="font-size:0.82rem; font-weight:700; color:#0369a1;">手动即时监控</div>
              <div style="font-size:0.72rem; color:#0284c7;">慢速拟人防风控节奏（~4秒/条），更新在库日历，随心自由添加</div>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
              <button 
                type="button" 
                class="btn-primary" 
                style="padding:6px 14px; font-size:0.78rem; display:inline-flex; align-items:center; gap:5px;"
                :disabled="patrolState.running || routes.length === 0"
                @click="triggerManual('hot')"
              >
                <span v-html="ICONS.play" style="display:inline-flex;"></span>
                <span>{{ patrolState.running && patrolState.mode === 'hot' ? '正在监控中...' : `立即监控这 ${routes.length} 条重点航线` }}</span>
              </button>
              <button 
                type="button" 
                class="btn-glass" 
                style="padding:6px 12px; font-size:0.78rem; color:#059669; border-color:#a7f3d0; background:#ecfdf5; display:inline-flex; align-items:center; gap:4px;"
                :disabled="patrolState.running"
                @click="triggerManual('all')"
                title="一键普查全国直飞拓扑所有航线"
              >
                <span v-html="ICONS.rocket" style="display:inline-flex;"></span>
                <span>全网大普查 (全量)</span>
              </button>
            </div>
          </div>

          <!-- Tab 1 专属重点监控进度条 (两边严格隔离，仅在跑重点监控时显示) -->
          <div v-if="(patrolState.mode === 'hot' || !patrolState.mode) && (patrolState.running || patrolState.percent > 0)" class="tab-progress-box hot-progress-box">
            <div class="progress-title-row">
              <span class="progress-title">⚡ 重点巡检中: {{ currentRouteDisplay }} ({{ patrolState.completed }}/{{ patrolState.total || routes.length }})</span>
              <div class="progress-right">
                <span class="progress-pct">{{ patrolState.percent }}%</span>
                <button type="button" class="btn-expand-link" @click="$emit('expand-full')">展开全屏大图</button>
              </div>
            </div>
            <div class="progress-bar-bg">
              <div class="progress-bar-fill hot-fill" :style="{ width: `${patrolState.percent}%` }"></div>
            </div>
          </div>
        </div>


        <!-- ==================== 选项卡 2：全网航网普查 (全量拓扑) ==================== -->
        <div v-show="activeTab === 'all'">
          <!-- 说明面板 -->
          <div class="patrol-info-card">
            <div style="font-size:0.82rem; font-weight:700; color:#15803d; margin-bottom:4px; display:flex; align-items:center; gap:6px;">
              <span v-html="ICONS.globe" style="display:inline-flex;"></span>
              <span>长龙航空全航网地毯式普查</span>
            </div>
            <div style="font-size:0.75rem; color:#166534; line-height:1.5;">
              自动遍历长龙航空全国所有直飞拓扑航线，拉取官方未来 61 天真实放票日历，全面更新大盘数据库，让所有目的地余票一目了然。
            </div>
          </div>

          <!-- 定时时间点配置 -->
          <div style="background:#ffffff; border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:10px 14px; margin-bottom:14px;">
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
              <div style="font-size:0.82rem; font-weight:700; display:flex; align-items:center; gap:6px;">
                <span v-html="ICONS.clock" style="color:#059669;"></span>
                <span>全量普查定时时间点 (至多 3 个):</span>
                <span style="font-size:0.72rem; color:#059669;">已设 {{ patrolTimes.length }}/3 个</span>
              </div>
              <label style="display:inline-flex; align-items:center; gap:6px; cursor:pointer; font-size:0.75rem; font-weight:700; color:#334155;">
                <input 
                  type="checkbox" 
                  :checked="switches.all_enabled" 
                  @change="onSwitchChange('all_enabled', $event.target.checked)"
                  style="accent-color:#059669;"
                >
                <span>定时普查开关: {{ switches.all_enabled ? '已启用' : '已停用' }}</span>
              </label>
            </div>

            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
              <span 
                v-for="(t, idx) in patrolTimes" 
                :key="idx"
                class="time-pill"
              >
                <span>{{ t }}</span>
                <button 
                  type="button" 
                  @click="removeTime(idx)"
                  style="border:none; background:transparent; color:#059669; cursor:pointer;"
                >&times;</button>
              </span>

              <div v-if="patrolTimes.length < 3" style="display:inline-flex; align-items:center; gap:6px;">
                <input type="time" v-model="newTime" style="padding:2px 6px; font-size:0.78rem; border:1px solid #cbd5e1; border-radius:4px;">
                <button type="button" class="btn-glass" style="padding:3px 8px; font-size:0.75rem;" @click="addTime">+ 添加</button>
              </div>
            </div>
          </div>

          <!-- 立即执行全量普查 -->
          <div class="trigger-card all-trigger-card">
            <div>
              <div style="font-size:0.82rem; font-weight:700; color:#047857;">手动即时全网普查</div>
              <div style="font-size:0.72rem; color:#059669;">受控多线程并发池遍历全国拓扑，逐条覆盖更新数据库</div>
            </div>
            <button 
              type="button" 
              class="btn-primary" 
              style="padding:6px 14px; font-size:0.78rem; background:linear-gradient(135deg, #059669, #047857); display:inline-flex; align-items:center; gap:5px;"
              :disabled="patrolState.running"
              @click="triggerManual('all')"
            >
              <span v-html="ICONS.rocket" style="display:inline-flex;"></span>
              <span>{{ patrolState.running && patrolState.mode === 'all' ? '正在全网普查中...' : '立即全网普查 (全量直飞拓扑)' }}</span>
            </button>
          </div>

          <!-- Tab 2 专属全网普查进度条 (两边严格隔离，仅在跑全网普查时显示) -->
          <div v-if="patrolState.mode === 'all' && (patrolState.running || patrolState.percent > 0)" class="tab-progress-box all-progress-box">
            <div class="progress-title-row">
              <span class="progress-title">🌐 全网大普查中: {{ currentRouteDisplay }} ({{ patrolState.completed }}/{{ patrolState.total || 490 }})</span>
              <div class="progress-right">
                <span class="progress-pct">{{ patrolState.percent }}%</span>
                <button type="button" class="btn-expand-link" @click="$emit('expand-full')">展开全屏大图</button>
              </div>
            </div>
            <div class="progress-bar-bg">
              <div class="progress-bar-fill all-fill" :style="{ width: `${patrolState.percent}%` }"></div>
            </div>
          </div>
        </div>

      </div>

      <!-- 模态框底部 -->
      <div class="modal-footer" style="justify-content:space-between; align-items:center;">
        <div style="display:flex; gap:8px;">
          <button type="button" class="btn-glass" style="font-size:0.75rem; color:#ef4444; border-color:#fecaca;" @click="clearAllRoutes">清空全部航线</button>
          <button type="button" class="btn-glass" style="font-size:0.75rem; color:#0284c7;" @click="importExampleRoutes">💡 导入示例 30 条</button>
        </div>
        <div style="display:flex; gap:8px;">
          <button type="button" class="btn-glass" style="font-size:0.78rem;" @click="$emit('close')">取消</button>
          <button type="button" class="btn-primary" style="font-size:0.78rem;" @click="saveAll">保存配置</button>
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
            name: item[2] || `${item[0]} ➔ ${item[1]}`
          };
        }
        return null;
      }).filter(Boolean);
    }
    if (hotRes?.interval) {
      hotIntervalMinutes.value = Number(hotRes.interval) || 25;
    }
    if (timesRes?.times && Array.isArray(timesRes.times)) patrolTimes.value = timesRes.times;
    if (swRes?.switches) switches.value = swRes.switches;
  } catch (e) {
    console.warn('加载巡检配置失败:', e);
  }
}

watch(() => props.visible, (val) => {
  if (val) loadData();
});

function removeRoute(idx) {
  routes.value.splice(idx, 1);
}

async function clearAllRoutes() {
  if (routes.value.length === 0) return;
  let confirmed = false;
  if (typeof window !== 'undefined' && window.$confirm) {
    confirmed = await window.$confirm({
      title: '清空重点监控航线',
      message: '确定要清空全部重点监控航线列表吗？已保存的巡检配置将一并清空。',
      type: 'warning',
      confirmText: '确定清空',
      cancelText: '取消'
    });
  } else {
    confirmed = confirm('确定要清空全部重点监控航线吗？');
  }
  if (!confirmed) return;
  routes.value = [];
}

function addRoute() {
  if (!newFrom.value || !newTo.value) return;
  const exists = routes.value.some(r => r.from === newFrom.value && r.to === newTo.value);
  if (exists) {
    if (typeof window !== 'undefined' && window.$dialog) {
      window.$dialog('提示', `航线【${newFrom.value} ➔ ${newTo.value}】已在列表中，无需重复添加`);
    } else {
      alert(`航线【${newFrom.value} ➔ ${newTo.value}】已在列表中`);
    }
    return;
  }
  const defaultName = newRouteName.value.trim() || `${newFrom.value} ➔ ${newTo.value}`;
  routes.value.unshift({
    from: newFrom.value,
    to: newTo.value,
    name: defaultName
  });
  newRouteName.value = '';
}

function importExampleRoutes() {
  const exampleDefaults = [
    { from: "杭州", to: "阿勒泰", name: "滑雪胜地 · 阿勒泰" },
    { from: "杭州", to: "喀什", name: "丝路古城 · 喀什" },
    { from: "杭州", to: "三亚", name: "海岛度假 · 三亚" },
    { from: "杭州", to: "哈尔滨", name: "冰雪大世界" },
    { from: "杭州", to: "成都", name: "天府之国 · 成都" },
    { from: "杭州", to: "重庆", name: "山城火锅" },
    { from: "杭州", to: "广州", name: "粤韵风华" },
    { from: "杭州", to: "深圳", name: "大湾区核心" },
    { from: "杭州", to: "乌鲁木齐", name: "大美新疆" },
    { from: "杭州", to: "长春", name: "北国春城" },
    { from: "杭州", to: "西宁", name: "青海湖之门" },
    { from: "杭州", to: "银川", name: "塞上江南" },
    { from: "杭州", to: "海拉尔", name: "呼伦贝尔大草原" },
    { from: "银川", to: "杭州", name: "塞上入江南" },
    { from: "银川", to: "乌鲁木齐", name: "丝绸之路" },
    { from: "银川", to: "三亚", name: "暖冬直达" },
    { from: "长春", to: "杭州", name: "南北干线" },
    { from: "长春", to: "三亚", name: "候鸟度假专线" },
    { from: "长春", to: "成都", name: "西南畅飞" }
  ];
  let addedCount = 0;
  for (const ex of exampleDefaults) {
    if (!routes.value.some(r => r.from === ex.from && r.to === ex.to)) {
      routes.value.push({ ...ex });
      addedCount++;
    }
  }
  if (typeof window !== 'undefined' && window.$dialog) {
    window.$dialog('导入成功', `已为您导入 ${addedCount} 条热门优质示例航线！点击【保存配置】即可生效。`, 'success');
  }
}

function removeTime(idx) {
  patrolTimes.value.splice(idx, 1);
}

function addTime() {
  if (patrolTimes.value.length >= 3) return;
  if (!newTime.value || patrolTimes.value.includes(newTime.value)) return;
  patrolTimes.value.push(newTime.value);
  patrolTimes.value.sort();
}

async function onSwitchChange(key, checked) {
  switches.value[key] = checked;
  try {
    await savePatrolSwitches(switches.value.hot_enabled, switches.value.all_enabled);
  } catch (e) {
    console.warn('更新开关失败:', e);
  }
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
        window.$dialog('触发普查提示', err || '未能成功触发巡检普查', 'warning');
      } else {
        alert(err || '未能成功触发巡检普查');
      }
    }
  } catch (e) {
    const msg = e.message || '';
    if (msg.includes('过期') || msg.includes('100001') || msg.includes('未登录') || msg.includes('失效') || msg.includes('授权') || msg.includes('400')) {
      emit('close');
      if (typeof window !== 'undefined' && window.$openAuthModal) {
        window.$openAuthModal(true);
      }
      return;
    }
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
  } catch (e) {
    console.error('保存监控配置失败:', e);
    alert('保存配置失败，请检查服务连接');
  }
}

function resetDefault() {
  importExampleRoutes();
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-card {
  background: #ffffff;
  border-radius: var(--radius-lg);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
  width: 100%;
  max-width: 680px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modalPop 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.modal-header {
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.patrol-tab-bar {
  padding: 10px 20px 0;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  gap: 12px;
}

.patrol-tab-item {
  padding: 8px 16px;
  font-size: 0.82rem;
  font-weight: 700;
  border: none;
  background: transparent;
  cursor: pointer;
  position: relative;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #64748b;
  border-bottom: 2px solid transparent;
}

.patrol-tab-item.active {
  color: var(--accent-cyan);
  border-bottom-color: var(--accent-cyan);
}

.patrol-tab-item.tab-all.active {
  color: #059669;
  border-bottom-color: #059669;
}

.patrol-bar-status {
  padding: 8px 12px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.seat-badge {
  font-size: 0.75rem;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 4px;
  background: #0284c7;
  color: #ffffff;
}

.custom-number-input {
  width: 48px;
  padding: 2px 4px;
  text-align: center;
  font-size: 0.75rem;
  font-weight: 700;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  outline: none;
}
.custom-number-input:focus {
  border-color: #0284c7;
}

.add-route-card {
  background: #f8fafc;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  margin-bottom: 12px;
}

.route-remark-input {
  flex: 1;
  min-width: 170px;
  padding: 5px 8px;
  font-size: 0.78rem;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  outline: none;
}
.route-remark-input:focus {
  border-color: #0284c7;
}

/* 航线表格列表样式 */
.route-table-wrapper {
  max-height: 250px;
  overflow-y: auto;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  margin-bottom: 14px;
  background: #ffffff;
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.02);
}

.route-table-wrapper::-webkit-scrollbar {
  width: 5px;
}
.route-table-wrapper::-webkit-scrollbar-track {
  background: #f8fafc;
}
.route-table-wrapper::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
.route-table-wrapper::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.route-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
}

.route-table thead {
  position: sticky;
  top: 0;
  background: #f1f5f9;
  z-index: 2;
}

.route-table th {
  padding: 8px 10px;
  font-weight: 700;
  color: #475569;
  border-bottom: 1px solid #cbd5e1;
  font-size: 0.75rem;
}

.route-table-row {
  border-bottom: 1px solid #f1f5f9;
  transition: background 0.15s;
}

.route-table-row:hover {
  background: #f8fafc;
}

.route-table td {
  padding: 6px 10px;
  vertical-align: middle;
}

.route-name-input {
  width: 100%;
  border: 1px solid transparent;
  background: transparent;
  padding: 4px 6px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  color: #0f172a;
  outline: none;
  transition: border-color 0.15s, background 0.15s;
}

.route-name-input:hover {
  border-color: #cbd5e1;
  background: #ffffff;
}

.route-name-input:focus {
  border-color: #0284c7;
  background: #ffffff;
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15);
}

.route-direction-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 2px 8px;
}

.city-from {
  font-weight: 700;
  color: #0284c7;
  font-size: 0.76rem;
}

.route-arrow {
  font-size: 0.72rem;
  color: #94a3b8;
}

.city-to {
  font-weight: 700;
  color: #4f46e5;
  font-size: 0.76rem;
}

.btn-remove-row {
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #ef4444;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-remove-row:hover {
  background: #ef4444;
  color: #ffffff;
}

.empty-table-cell {
  text-align: center;
  padding: 30px 16px;
  background: #f8fafc;
}

/* 触发卡片 */
.trigger-card {
  border-radius: 6px;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.hot-trigger-card {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
}

.all-trigger-card {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
}

/* 进度条独立展示 */
.tab-progress-box {
  border-radius: 6px;
  padding: 10px 12px;
  margin-top: 10px;
}

.hot-progress-box {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.all-progress-box {
  background: #f0fdf4;
  border: 1px solid #86efac;
}

.progress-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.78rem;
  margin-bottom: 6px;
  font-weight: 700;
  color: #15803d;
}

.progress-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-pct {
  font-size: 0.82rem;
  color: #047857;
  font-weight: 800;
}

.btn-expand-link {
  border: 1px solid #99f6e4;
  background: #f0fdfa;
  color: #0d9488;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.btn-expand-link:hover {
  background: #0d9488;
  color: #ffffff;
}

.progress-bar-bg {
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.hot-fill {
  background: linear-gradient(90deg, #0284c7, #38bdf8);
}

.all-fill {
  background: linear-gradient(90deg, #10b981, #059669);
}

.patrol-info-card {
  padding: 10px 14px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  margin-bottom: 12px;
}

.time-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #047857;
  font-weight: 800;
  font-size: 0.78rem;
  padding: 2px 6px;
  border-radius: 4px;
}

.modal-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--border-subtle);
  background: #f8fafc;
  display: flex;
}

@keyframes modalPop {
  from { opacity: 0; transform: scale(0.96); }
  to { opacity: 1; transform: scale(1); }
}
</style>
