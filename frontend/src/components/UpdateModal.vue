<template>
  <div v-if="visible" class="update-modal-overlay" @click.self="$emit('close')">
    <div class="update-modal-card">
      <!-- 模态框头部 -->
      <div class="update-modal-header">
        <div class="update-modal-title">
          <span class="header-icon-wrap" v-html="ICONS.radar"></span>
          <span>{{ updateInfo?.has_update ? '发现新版本可用' : '软件版本信息' }}</span>
        </div>
        <button type="button" class="update-close-btn" @click="$emit('close')" title="关闭">
          <span v-html="ICONS.close"></span>
        </button>
      </div>

      <!-- 模态框内容区 (100% 纯白实底，绝不透明穿透) -->
      <div class="update-modal-body">
        <!-- 版本状态横幅卡片 -->
        <div class="version-banner-box">
          <div class="version-meta-row">
            <div class="version-label">
              当前运行版本：<span class="version-tag-number">{{ updateInfo?.current_version || 'v2.1.3' }}</span>
            </div>
            <div v-if="updateInfo?.has_update" class="status-badge badge-new">
              最新：{{ updateInfo?.latest_version }}
            </div>
            <div v-else class="status-badge badge-latest">
              已是最新版本
            </div>
          </div>
          
          <div class="version-app-title">
            {{ updateInfo?.release_name || '长龙航空畅飞助手 v2.1.3' }}
          </div>
        </div>

        <!-- 详细说明或更新日志 -->
        <div v-if="updateInfo?.has_update && formattedNotes" class="release-notes-section">
          <div class="section-title">更新说明与新特性：</div>
          <div class="release-notes-box">
            <pre class="notes-pre">{{ formattedNotes }}</pre>
          </div>
        </div>

        <div v-else class="version-desc-text">
          当前已是官方最新发布版本。本项目完全遵循纯本地开源架构，所有数据仅存留于本机，随时关注 GitHub Releases 获取航网数据与功能迭代。
        </div>

        <!-- 纯本地开源安全声明 -->
        <div class="security-notice-box">
          <span class="notice-icon" v-html="ICONS.shield"></span>
          <span>100% 官方开源发布，绿色单文件免安装，无广告无捆绑</span>
        </div>
      </div>

      <!-- 模态框底部操作栏 -->
      <div class="update-modal-footer">
        <a 
          :href="updateInfo?.page_url || 'https://github.com/eureka-wu/clairline/releases'" 
          target="_blank" 
          rel="noopener noreferrer"
          class="btn-github-link"
          title="在浏览器中查看 GitHub Release 详情"
        >
          <span class="footer-btn-icon" v-html="ICONS.github"></span>
          <span>查看 GitHub 页面</span>
        </a>

        <div class="footer-action-group">
          <button 
            v-if="updateInfo?.has_update"
            type="button" 
            class="btn-ignore" 
            title="跳过此版本，之后不再弹出该版本的更新提示"
            @click="handleIgnore"
          >
            忽略此版本
          </button>
          <button type="button" class="btn-cancel" @click="$emit('close')">
            {{ updateInfo?.has_update ? '暂不更新' : '关闭' }}
          </button>
          <a 
            v-if="updateInfo?.has_update"
            :href="updateInfo?.download_url" 
            target="_blank" 
            rel="noopener noreferrer"
            class="btn-download"
            @click="$emit('close')"
          >
            <span class="footer-btn-icon" v-html="ICONS.arrowRight"></span>
            <span>立即下载最新版 Exe</span>
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { ICONS } from '../data/icons.js';

const props = defineProps({
  visible: Boolean,
  updateInfo: Object
});

const emit = defineEmits(['close', 'ignore-version']);

const formattedNotes = computed(() => {
  const raw = props.updateInfo?.release_notes || '';
  if (!raw) return '';
  // 截取分隔符 --- 之前的核心更新内容，并清理 Markdown 标记符号
  const mainPart = raw.split(/\n---\r?\n/)[0] || raw;
  return mainPart
    .split(/\r?\n/)
    .map(line => line.replace(/^#+\s*/, '').replace(/\*\*(.*?)\*\*/g, '$1').trim())
    .filter((line, idx, arr) => !(line === '' && (idx === 0 || arr[idx - 1] === '')))
    .join('\n')
    .trim();
});

function handleIgnore() {
  const ver = props.updateInfo?.latest_version;
  if (ver) {
    try {
      localStorage.setItem('ignored_update_version', ver);
    } catch (e) {}
    emit('ignore-version', ver);
  }
  emit('close');
}
</script>

<style scoped>
/* 模态框遮罩：深度半透明遮罩 + 磨砂背景，彻底隐藏背景视觉杂乱 */
.update-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  animation: overlayFadeIn 0.2s ease;
}

/* 模态框卡片主壳：100% 纯白实底背景，绝无穿透！立体阴影与圆角 */
.update-modal-card {
  width: 560px;
  max-width: 94vw;
  background: #ffffff !important;
  border: 1px solid #cbd5e1;
  border-radius: 14px;
  box-shadow: 0 25px 60px -15px rgba(15, 23, 42, 0.35), 0 0 0 1px rgba(15, 23, 42, 0.05);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: cardZoomIn 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}

/* 头部 */
.update-modal-header {
  height: 52px;
  background: #ffffff;
  border-bottom: 1px solid #f1f5f9;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.update-modal-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.95rem;
  font-weight: 700;
  color: #0f172a;
}

.header-icon-wrap {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #0284c7;
}

.header-icon-wrap :deep(svg) {
  width: 18px;
  height: 18px;
}

.update-close-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.update-close-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
}

/* 内容区 */
.update-modal-body {
  background: #ffffff;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 版本横幅卡片 */
.version-banner-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px 16px;
}

.version-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.version-label {
  font-size: 0.78rem;
  color: #64748b;
  font-weight: 500;
}

.version-tag-number {
  font-size: 0.88rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: 0.02em;
}

.status-badge {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
  line-height: 1.2;
}

.badge-new {
  background: #dcfce7;
  color: #15803d;
}

.badge-latest {
  background: #e0f2fe;
  color: #0369a1;
}

.version-app-title {
  font-size: 0.95rem;
  font-weight: 800;
  color: #0f172a;
}

/* 说明文本 */
.version-desc-text {
  font-size: 0.8rem;
  color: #475569;
  line-height: 1.6;
}

/* 更新日志 */
.release-notes-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.section-title {
  font-size: 0.78rem;
  font-weight: 700;
  color: #475569;
}

.release-notes-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 14px;
  max-height: 160px;
  overflow-y: auto;
}

.notes-pre {
  margin: 0;
  font-family: inherit;
  font-size: 0.78rem;
  color: #334155;
  line-height: 1.65;
  white-space: pre-wrap;
}

/* 安全提示横条 */
.security-notice-box {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 0.74rem;
  color: #166534;
  display: flex;
  align-items: center;
  gap: 8px;
}

.notice-icon {
  width: 15px;
  height: 15px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #16a34a;
  flex-shrink: 0;
}

.notice-icon :deep(svg) {
  width: 15px;
  height: 15px;
}

/* 底部操作栏 */
.update-modal-footer {
  min-height: 58px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.btn-github-link {
  height: 34px;
  padding: 0 12px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #334155;
  font-size: 0.76rem;
  font-weight: 600;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.btn-github-link:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
  color: #0f172a;
}

.footer-btn-icon {
  width: 14px;
  height: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.footer-btn-icon :deep(svg) {
  width: 14px;
  height: 14px;
}

.footer-action-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.btn-ignore {
  height: 34px;
  padding: 0 10px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid transparent;
  color: #94a3b8;
  font-size: 0.74rem;
  white-space: nowrap;
  flex-shrink: 0;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-ignore:hover {
  color: #64748b;
  background: #f1f5f9;
}

.btn-cancel {
  height: 34px;
  padding: 0 14px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #334155;
  font-size: 0.78rem;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-cancel:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
  color: #0f172a;
}

.btn-download {
  height: 34px;
  padding: 0 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, #10b981, #059669);
  border: none;
  color: #ffffff;
  font-size: 0.78rem;
  font-weight: 700;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  flex-shrink: 0;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);
  transition: all 0.15s ease;
}

.btn-download:hover {
  background: linear-gradient(135deg, #059669, #047857);
  box-shadow: 0 4px 10px rgba(16, 185, 129, 0.4);
}

/* 动效 */
@keyframes overlayFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes cardZoomIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}
</style>
