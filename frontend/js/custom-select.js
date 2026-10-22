/**
 * 高级定制搜索选择框组件 (Custom Searchable Combobox)
 * 具备：实时拼音/中文过滤、区域分组展示、精致交互动效与键盘操作
 */
import { ICONS } from './icons.js';

export class CustomSelect {
  /**
   * @param {Object} options
   * @param {string|HTMLElement} options.container - 挂载容器选择器或 DOM 节点
   * @param {Array<{value: string, label: string, sublabel?: string, badge?: string, group?: string}>} options.options - 选项列表
   * @param {string} options.value - 当前初始值
   * @param {string} options.placeholder - 占位提示文案
   * @param {boolean} options.searchable - 是否启用顶部搜索框
   * @param {Function} options.onChange - 值变更回调 (value, item) => void
   */
  constructor(options) {
    this.container = typeof options.container === 'string' 
      ? document.querySelector(options.container) 
      : options.container;
    
    this.allOptions = options.options || [];
    this.currentValue = options.value || (this.allOptions[0]?.value ?? '');
    this.placeholder = options.placeholder || '请选择';
    this.searchable = options.searchable !== false;
    this.onChange = options.onChange || (() => {});
    this.isOpen = false;
    this.searchTerm = '';

    if (!this.container) {
      console.error('CustomSelect: 未找到挂载容器', options.container);
      return;
    }

    this.render();
    this.bindEvents();
  }

  render() {
    this.container.innerHTML = `
      <div class="custom-select-wrapper">
        <button type="button" class="cs-trigger" aria-haspopup="listbox" aria-expanded="false">
          <span class="cs-trigger-content">
            <span class="cs-selected-label">加载中...</span>
            <span class="cs-selected-sublabel"></span>
          </span>
          <span class="cs-arrow">${ICONS.chevronDown}</span>
        </button>

        <div class="cs-dropdown" style="display: none;">
          ${this.searchable ? `
            <div class="cs-search-box">
              <span class="cs-search-icon">${ICONS.search}</span>
              <input type="text" class="cs-search-input" placeholder="输入城市名 / 拼音检索..." autocomplete="off">
            </div>
          ` : ''}
          <div class="cs-options-list" role="listbox"></div>
        </div>
      </div>
    `;

    this.wrapper = this.container.querySelector('.custom-select-wrapper');
    this.triggerBtn = this.container.querySelector('.cs-trigger');
    this.dropdown = this.container.querySelector('.cs-dropdown');
    this.labelEl = this.container.querySelector('.cs-selected-label');
    this.sublabelEl = this.container.querySelector('.cs-selected-sublabel');
    this.arrowEl = this.container.querySelector('.cs-arrow');
    this.optionsListEl = this.container.querySelector('.cs-options-list');
    this.searchInput = this.container.querySelector('.cs-search-input');

    this.updateTriggerDisplay();
    this.renderOptionsList();
  }

  updateTriggerDisplay() {
    const matched = this.allOptions.find(opt => opt.value === this.currentValue);
    if (matched) {
      this.labelEl.textContent = matched.label;
      this.sublabelEl.textContent = matched.sublabel ? `· ${matched.sublabel}` : '';
    } else {
      this.labelEl.textContent = this.placeholder;
      this.sublabelEl.textContent = '';
    }
  }

  renderOptionsList() {
    const filtered = this.allOptions.filter(opt => {
      if (!this.searchTerm.trim()) return true;
      const term = this.searchTerm.toLowerCase().trim();
      const matchLabel = opt.label.toLowerCase().includes(term);
      const matchSub = (opt.sublabel || '').toLowerCase().includes(term);
      const matchBadge = (opt.badge || '').toLowerCase().includes(term);
      const matchPinyin = (opt.pinyin || '').toLowerCase().includes(term);
      return matchLabel || matchSub || matchBadge || matchPinyin;
    });

    if (filtered.length === 0) {
      this.optionsListEl.innerHTML = `
        <div class="cs-empty-state">
          <span>未找到相关城市</span>
        </div>
      `;
      return;
    }

    // 按 Group 分组（如有）
    const groups = {};
    filtered.forEach(opt => {
      const g = opt.group || '常用选项';
      if (!groups[g]) groups[g] = [];
      groups[g].push(opt);
    });

    let html = '';
    Object.entries(groups).forEach(([groupName, items]) => {
      if (Object.keys(groups).length > 1) {
        html += `<div class="cs-group-header">${groupName}</div>`;
      }
      items.forEach(item => {
        const isSelected = item.value === this.currentValue;
        html += `
          <div class="cs-option-item ${isSelected ? 'selected' : ''}" data-value="${item.value}">
            <div class="cs-option-main">
              <span class="cs-opt-name">${item.label}</span>
              ${item.sublabel ? `<span class="cs-opt-sub">${item.sublabel}</span>` : ''}
            </div>
            <div class="cs-option-right">
              ${item.badge ? `<span class="cs-opt-badge">${item.badge}</span>` : ''}
              ${isSelected ? `<span class="cs-check-icon">${ICONS.check}</span>` : ''}
            </div>
          </div>
        `;
      });
    });

    this.optionsListEl.innerHTML = html;

    // 绑定选项点击事件
    this.optionsListEl.querySelectorAll('.cs-option-item').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        const val = el.getAttribute('data-value');
        this.selectValue(val);
      });
    });
  }

  selectValue(val) {
    this.currentValue = val;
    this.updateTriggerDisplay();
    this.renderOptionsList();
    this.close();
    const item = this.allOptions.find(o => o.value === val);
    this.onChange(val, item);
  }

  setValue(val) {
    this.currentValue = val;
    this.updateTriggerDisplay();
    this.renderOptionsList();
  }

  getValue() {
    return this.currentValue;
  }

  setOptions(newOptions, defaultValue) {
    this.allOptions = newOptions || [];
    if (defaultValue !== undefined && this.allOptions.some(o => o.value === defaultValue)) {
      this.currentValue = defaultValue;
    } else if (!this.allOptions.some(o => o.value === this.currentValue)) {
      this.currentValue = this.allOptions[0]?.value || '';
    }
    this.updateTriggerDisplay();
    this.renderOptionsList();
  }

  open() {
    // 关闭页面上其他所有下拉
    document.querySelectorAll('.cs-dropdown').forEach(d => {
      if (d !== this.dropdown) d.style.display = 'none';
    });
    document.querySelectorAll('.cs-trigger').forEach(t => {
      if (t !== this.triggerBtn) t.classList.remove('active');
    });

    this.isOpen = true;
    this.dropdown.style.display = 'block';
    this.triggerBtn.classList.add('active');
    this.triggerBtn.setAttribute('aria-expanded', 'true');

    if (this.searchInput) {
      this.searchInput.value = '';
      this.searchTerm = '';
      this.renderOptionsList();
      setTimeout(() => this.searchInput.focus(), 50);
    }
  }

  close() {
    this.isOpen = false;
    this.dropdown.style.display = 'none';
    this.triggerBtn.classList.remove('active');
    this.triggerBtn.setAttribute('aria-expanded', 'false');
  }

  toggle() {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  bindEvents() {
    this.triggerBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggle();
    });

    if (this.searchInput) {
      this.searchInput.addEventListener('input', (e) => {
        this.searchTerm = e.target.value;
        this.renderOptionsList();
      });

      this.searchInput.addEventListener('click', (e) => {
        e.stopPropagation();
      });
    }

    // 点击外部自动收起
    document.addEventListener('click', (e) => {
      if (!this.container.contains(e.target)) {
        if (this.isOpen) this.close();
      }
    });

    // 键盘 Esc 关闭
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isOpen) {
        this.close();
      }
    });
  }
}
