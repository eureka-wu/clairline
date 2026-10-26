<template>
  <header class="app-header">
    <div class="header-inner">
      <!-- 左侧：品牌 Logo 与 Tab 探索模式切换 -->
      <div class="brand-area">
        <div class="brand-logo-card">
          <img :src="loongAirLogo" alt="长龙航空" class="brand-logo-img" />
        </div>
        <div class="brand-title">长龙航线</div>

        <!-- Tab Segmented 切换器 (34px 高度，垂直精准对齐) -->
        <nav class="tab-segmented">
          <button 
            type="button"
            class="tab-btn" 
            :class="{ active: currentTab === 'routes' }"
            @click="$emit('update:currentTab', 'routes')"
          >
            <span class="tab-icon" v-html="ICONS.plane"></span>
            <span>航线探索</span>
          </button>
          <button 
            type="button"
            class="tab-btn" 
            :class="{ active: currentTab === 'map' }"
            @click="$emit('update:currentTab', 'map')"
          >
            <span class="tab-icon" v-html="ICONS.compass"></span>
            <span>地图探索</span>
          </button>
        </nav>
      </div>

      <!-- 右侧：统一高度 32px、统一对齐、统一字号的专业动作胶囊群 -->
      <div class="header-actions">
        <!-- 1. 会员登录态胶囊 (已登录) -->
        <button 
          v-if="authStatus?.is_logged_in"
          type="button"
          class="header-pill-btn member-pill"
          @click="$emit('open-auth')"
          :title="`凭据有效 · 更新于 ${authStatus.update_time || '刚刚'} (点击可重新同步)`"
        >
          <span class="btn-icon-wrap icon-cyan" v-html="ICONS.memberCard"></span>
          <span class="btn-label-text">{{ authStatus.user_name || '长龙会员' }}</span>
          <span v-if="authStatus.member_level" class="member-level-tag">{{ authStatus.member_level }}</span>
          <span v-else-if="authStatus.mobile" class="member-sub-info">{{ authStatus.mobile }}</span>
        </button>

        <!-- 1. 会员登录态胶囊 (未登录) -->
        <button 
          v-else
          type="button"
          class="header-pill-btn login-pill"
          @click="$emit('open-auth')"
          title="点击通过手机验证码快捷登录长龙会员，解锁机位实时查询"
        >
          <span class="btn-icon-wrap" v-html="ICONS.phone"></span>
          <span class="btn-label-text login-text">手机验证码登录</span>
        </button>

        <!-- 2. 航线监控按钮 -->
        <button 
          type="button" 
          class="header-pill-btn patrol-pill"
          :class="{ 'is-patrolling': patrolState?.running }"
          @click="$emit('open-patrol')"
          title="航线监控与全网放票普查"
        >
          <span 
            class="btn-icon-wrap icon-slate" 
            v-html="ICONS.radar" 
            :class="{ 'spin-icon': patrolState?.running }"
          ></span>
          <span class="btn-label-text">{{ headerLabel }}</span>
        </button>



        <!-- 4. GitHub 官方开源仓库链接 -->
        <a 
          href="https://github.com/eureka-wu/clairline" 
          target="_blank" 
          rel="noopener noreferrer"
          class="header-pill-btn github-pill"
          title="访问 GitHub 官方开源仓库 (eureka-wu/clairline)"
        >
          <span class="btn-icon-wrap icon-dark" v-html="ICONS.github"></span>
          <span class="btn-label-text">GitHub</span>
        </a>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue';
import { ICONS } from '../data/icons.js';
import loongAirLogo from '../assets/loongair-logo.png';

const props = defineProps({
  currentTab: {
    type: String,
    default: 'routes'
  },
  patrolState: {
    type: Object,
    default: () => ({ running: false, mode: 'idle', completed: 0, total: 0 })
  },
  authStatus: {
    type: Object,
    default: () => ({ is_logged_in: false, user_name: '', mobile: '', cert_installed: false })
  },
  updateInfo: {
    type: Object,
    default: () => ({ has_update: false, current_version: 'v2.0.0' })
  }
});

defineEmits(['update:currentTab', 'open-patrol', 'open-auth', 'open-update']);

const headerLabel = computed(() => {
  if (!props.patrolState?.running) {
    return '航线监控';
  }
  const { mode, completed, total, percent } = props.patrolState;
  const isAll = mode === 'all';
  const safeTotal = total > 0 ? total : (isAll ? 397 : 30);
  const prefix = isAll ? '普查中' : '监控中';
  const pct = percent !== undefined && percent !== null ? ` (${percent}%)` : '';
  return `${prefix} ${completed}/${safeTotal}${pct}`;
});
</script>

<style scoped>
/* 顶部 Header 主骨架 */
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-bottom: 1px solid #e2e8f0;
  height: 56px;
  box-sizing: border-box;
}

.header-inner {
  max-width: 1280px;
  height: 100%;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

/* 左侧品牌区 */
.brand-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-logo-card {
  width: 32px;
  height: 32px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 2px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  flex-shrink: 0;
}

.brand-logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 6px;
  display: block;
}

.brand-title {
  font-size: 1.12rem;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.01em;
  margin-right: 4px;
  white-space: nowrap;
}

/* Tab Segmented 切换器 */
.tab-segmented {
  display: inline-flex;
  align-items: center;
  background: #f1f5f9;
  height: 34px;
  padding: 2px;
  border-radius: 17px;
  box-sizing: border-box;
  gap: 2px;
}

.tab-btn {
  height: 30px;
  border: none;
  background: transparent;
  padding: 0 14px;
  border-radius: 15px;
  font-size: 0.8rem;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.18s ease;
  white-space: nowrap;
}

.tab-btn.active {
  background: #ffffff;
  color: #0284c7;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.tab-icon {
  width: 14px;
  height: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

/* ========================================================
   右侧动作胶囊群：统一标准规范
   - 统一高度：32px
   - 统一圆角：8px
   - 统一边框：1px solid #e2e8f0
   - 统一图标：14x14px 居中
   - 统一文字：font-size: 0.76rem, font-weight: 600
======================================================== */
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-pill-btn {
  height: 32px;
  padding: 0 10px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  box-sizing: border-box;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.15s ease;
  white-space: nowrap;
  outline: none;
}

.header-pill-btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  transform: translateY(-1px);
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
}

.header-pill-btn:active {
  transform: translateY(0);
}

/* 统一图标包裹器 */
.btn-icon-wrap {
  width: 14px;
  height: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  line-height: 1;
}

.btn-icon-wrap :deep(svg) {
  width: 14px;
  height: 14px;
  display: block;
}

.icon-cyan {
  color: #0284c7;
}

.icon-slate {
  color: #475569;
}

.icon-tag {
  color: #64748b;
}

.icon-dark {
  color: #1e293b;
}

/* 统一文字基线与字体 */
.btn-label-text {
  font-size: 0.76rem;
  font-weight: 600;
  color: #334155;
  line-height: 1;
  display: inline-flex;
  align-items: center;
}

/* 会员级别内嵌徽标 */
.member-level-tag {
  font-size: 0.68rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  background: #eff6ff;
  color: #2563eb;
  line-height: 1;
  margin-left: 2px;
}

.member-sub-info {
  font-size: 0.7rem;
  color: #94a3b8;
  margin-left: 2px;
}

/* 未登录时的渐变同步按钮 */
.login-pill {
  background: linear-gradient(135deg, #0284c7, #0369a1);
  border-color: transparent;
  color: #ffffff;
}

.login-pill .btn-icon-wrap {
  color: #ffffff;
}

.login-pill .login-text {
  color: #ffffff;
}

.login-pill:hover {
  background: linear-gradient(135deg, #0369a1, #075985);
  border-color: transparent;
  box-shadow: 0 2px 6px rgba(2, 132, 199, 0.35);
}

/* 巡检执行中的高亮与旋转动画 */
.patrol-pill.is-patrolling {
  border-color: #86efac;
  background: #f0fdf4;
}

.patrol-pill.is-patrolling .btn-label-text {
  color: #166534;
  font-weight: 700;
}

.spin-icon {
  animation: spinIcon 1.2s linear infinite;
  transform-origin: center center;
}

@keyframes spinIcon {
  100% { transform: rotate(360deg); }
}

/* 发现新版本时的柔和醒目高亮 */
.version-pill.has-new-version {
  border-color: #86efac;
  background: #f0fdf4;
}

.version-pill.has-new-version .btn-label-text {
  color: #166534;
  font-weight: 700;
}

.version-pill.has-new-version .icon-tag {
  color: #10b981;
}
</style>
