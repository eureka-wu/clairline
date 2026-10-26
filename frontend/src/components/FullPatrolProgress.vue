<template>
  <Teleport to="body">
    <transition name="patrol-fade">
      <div v-if="visible" class="patrol-overlay">
        <div class="patrol-card">
          <!-- 动态雷达扫描光环 -->
          <div class="scanner-avatar-box">
            <div class="pulse-ring ring-1"></div>
            <div class="pulse-ring ring-2"></div>
            <div class="scanner-center">
              <span v-html="ICONS.radar" class="scanner-icon"></span>
            </div>
          </div>

          <!-- 头部标题 (动态区分全网普查与重点巡检) -->
          <h2 class="patrol-main-title">
            {{ modeTitle }}
          </h2>

          <!-- 会员绑定状态信息条 -->
          <div v-if="authStatus?.is_logged_in" class="member-badge-row">
            <span class="member-tag">已锁定会员身份</span>
            <span class="member-name">{{ authStatus.user_name || '长龙会员' }}</span>
            <span class="member-level">{{ authStatus.member_level || '乘云会员' }}</span>
          </div>

          <!-- 动态当前探测航线 -->
          <div class="current-probe-box">
            <span class="probe-label">当前检索:</span>
            <span class="probe-route">{{ formatCurrentRoute }}</span>
          </div>

          <!-- 现代渐变进度条 -->
          <div class="progress-bar-wrapper">
            <div class="progress-bar-track">
              <div 
                class="progress-bar-fill" 
                :style="{ width: `${displayPercent}%` }"
              >
                <div class="progress-glow"></div>
              </div>
            </div>
            <div class="progress-bar-meta">
              <span class="percent-text">{{ displayPercent }}%</span>
              <span class="counter-text">{{ counterText }}</span>
            </div>
          </div>

          <!-- 实时探测成果统计卡 -->
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-val">{{ availableRoutesCount }}</div>
              <div class="stat-desc">有票直飞航线</div>
            </div>
            <div class="stat-card">
              <div class="stat-val">{{ patrolState?.success || 0 }}</div>
              <div class="stat-desc">成功调取日历</div>
            </div>
            <div class="stat-card">
              <div class="stat-val">{{ Math.max(0, safeTotal - (patrolState?.completed || 0)) }}</div>
              <div class="stat-desc">{{ remainingText }}</div>
            </div>
          </div>

          <!-- 底部动作 -->
          <div class="patrol-actions">
            <button 
              type="button" 
              class="btn-minimize" 
              @click="$emit('minimize')"
            >
              <span v-html="ICONS.arrowRight" style="display:inline-flex;"></span>
              <span>转入后台普查 (直接进入大盘页面)</span>
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, watch } from 'vue';
import { ICONS } from '../data/icons.js';

const props = defineProps({
  visible: { type: Boolean, default: false },
  patrolState: { type: Object, default: () => ({}) },
  authStatus: { type: Object, default: () => ({}) },
  availableRoutesCount: { type: Number, default: 0 }
});

const emit = defineEmits(['minimize', 'completed']);

const isCompleted = computed(() => {
  return props.patrolState?.percent >= 100 || (!props.patrolState?.running && props.patrolState?.completed > 0);
});

const isAllMode = computed(() => {
  // 只要不是明确标记为重点巡检 (hot)，一律判定为全网航网普查模式，杜绝异步空窗期 fallback 误显为 30 条重点监控
  return props.patrolState?.mode !== 'hot';
});

const safeTotal = computed(() => {
  if (props.patrolState?.total && props.patrolState.total > 0) return props.patrolState.total;
  // 长龙官方全国直飞航网拓扑基准库为 397 条直飞航线
  return isAllMode.value ? 397 : 30;
});

const modeTitle = computed(() => {
  const total = safeTotal.value;
  if (isCompleted.value) {
    return isAllMode.value ? `全网直飞航网普查圆满完成！(共 ${total} 条)` : `重点监控航线巡检完成！(共 ${total} 条)`;
  }
  return isAllMode.value ? `正在为您全网普查 ${total} 条直飞航线` : `正在为您巡检 ${total} 条重点监控航线`;
});

const counterText = computed(() => {
  const completed = props.patrolState?.completed || 0;
  const total = safeTotal.value;
  const label = isAllMode.value ? '直飞航线' : '重点航线';
  const action = isAllMode.value ? '已普查' : '已巡检';
  return `${action} ${completed} / ${total} 条${label}`;
});

const remainingText = computed(() => {
  return isAllMode.value ? '待检索航线' : '待巡检航线';
});

const displayPercent = computed(() => {
  if (isCompleted.value) return 100;
  return Math.min(Math.max(props.patrolState?.percent || 2, 2), 100);
});

const formatCurrentRoute = computed(() => {
  if (isCompleted.value) return '全部航线已处理完毕，机位大盘已就绪';
  const r = props.patrolState?.current_route;
  if (Array.isArray(r) && r.length >= 2) {
    return `${r[0]} ➔ ${r[1]}`;
  }
  if (typeof r === 'string' && r) return r;
  return '连接长龙官方航网数据中...';
});

// 当探测达到 100% 时，延迟 1.2 秒自动平滑通知父组件完成并进入大盘页面
watch(() => isCompleted.value, (done) => {
  if (done && props.visible) {
    setTimeout(() => {
      emit('completed');
    }, 1200);
  }
});
</script>

<style scoped>
.patrol-overlay {
  position: fixed;
  inset: 0;
  z-index: 99990;
  background: rgba(15, 23, 42, 0.78);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.patrol-card {
  width: 100%;
  max-width: 520px;
  background: #ffffff;
  border-radius: 20px;
  padding: 36px 32px 28px;
  box-shadow: 0 30px 60px -12px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(226, 232, 240, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  animation: patrol-pop 0.26s cubic-bezier(0.16, 1, 0.3, 1);
}

.scanner-avatar-box {
  position: relative;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.scanner-center {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(2, 132, 199, 0.35);
  z-index: 2;
}

.scanner-icon {
  color: #ffffff;
  display: flex;
  font-size: 1.5rem;
  animation: radar-spin 3s linear infinite;
}

.pulse-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid rgba(2, 132, 199, 0.4);
  animation: pulse-out 2s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
}
.ring-2 {
  animation-delay: 1s;
}

.patrol-main-title {
  margin: 0 0 10px;
  font-size: 1.25rem;
  font-weight: 800;
  color: #0f172a;
}

.member-badge-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  padding: 4px 12px;
  border-radius: 20px;
  margin-bottom: 16px;
  font-size: 0.78rem;
}

.member-tag {
  color: #16a34a;
  font-weight: 700;
}
.member-name {
  color: #0f172a;
  font-weight: 800;
}
.member-level {
  background: #dcfce7;
  color: #15803d;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 0.72rem;
  font-weight: 700;
}

.current-probe-box {
  font-size: 0.82rem;
  color: #64748b;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.probe-route {
  color: #0284c7;
  font-weight: 800;
}

/* 进度条 */
.progress-bar-wrapper {
  width: 100%;
  margin-bottom: 24px;
}

.progress-bar-track {
  width: 100%;
  height: 12px;
  background: #f1f5f9;
  border-radius: 8px;
  overflow: hidden;
  position: relative;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.05);
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #06b6d4 0%, #0284c7 100%);
  border-radius: 8px;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.progress-glow {
  position: absolute;
  top: 0;
  bottom: 0;
  right: 0;
  width: 20px;
  background: rgba(255, 255, 255, 0.4);
  filter: blur(2px);
}

.progress-bar-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 0.78rem;
}
.percent-text {
  font-weight: 800;
  color: #0284c7;
  font-size: 0.95rem;
}
.counter-text {
  color: #64748b;
  font-weight: 600;
}

/* 统计卡网格 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  width: 100%;
  margin-bottom: 24px;
}

.stat-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 8px;
}
.stat-val {
  font-size: 1.15rem;
  font-weight: 800;
  color: #0f172a;
}
.stat-desc {
  font-size: 0.72rem;
  color: #64748b;
  margin-top: 2px;
}

/* 动作按钮 */
.patrol-actions {
  width: 100%;
}

.btn-minimize {
  width: 100%;
  padding: 10px 18px;
  border-radius: 10px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.15s ease;
}
.btn-minimize:hover {
  background: #f8fafc;
  border-color: #94a3b8;
  color: #0f172a;
}

/* 动效 */
.patrol-fade-enter-active,
.patrol-fade-leave-active {
  transition: opacity 0.25s ease;
}
.patrol-fade-enter-from,
.patrol-fade-leave-to {
  opacity: 0;
}

@keyframes patrol-pop {
  0% { transform: scale(0.92); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

@keyframes radar-spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes pulse-out {
  0% { transform: scale(0.7); opacity: 1; }
  100% { transform: scale(1.4); opacity: 0; }
}
</style>
