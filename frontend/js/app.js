/**
 * 主控制器 App.js
 * 负责页面交互、事件绑定、自定义组件挂载与各个功能模块的数据驱动渲染
 */
import { CITY_METADATA, HIGH_SPEED_RAIL_CONNECTIONS, SEASONAL_GUIDE } from './routes-data.js';
import { DIRECT_MAP, REVERSE_MAP, ROUTES_NETWORK } from './routes-network.js';
import { getFeeConfig, saveFeeConfig, calculateTaxes, simulateTripEconomy, DEFAULT_FEE_CONFIG } from './cost-calculator.js';
import { queryDirectRoutes, planMultiLegRoutes, getNearbyRadiationHubs, rollRandomBlindbox } from './transfer-engine.js';
import { AIRPORT_GUIDES } from './airport-guide.js';
import { CustomSelect } from './custom-select.js';
import { ICONS } from './icons.js';
import { FLIGHTS_SCHEDULE } from './flights-schedule.js';
import { queryLiveFlights } from './api.js';
import { CHINA_PROVINCES } from './china-geo.js';

// 当前状态 (默认定位长龙大本营·杭州)
let currentOrigin = '杭州';
let currentDestination = '全部';
let currentRegion = '全部';

// CustomSelect 实例引用
let csOriginInstance = null;
let csDestInstance = null;
let csRegionInstance = null;
let csTransferOriginInstance = null;
let csTransferTargetInstance = null;
let csBlindboxOriginInstance = null;
let csBlindboxTagInstance = null;
let csMapCityInstance = null;

// 全网官方放票大盘索引 (from-to => available info)
let AVAILABLE_ROUTES_MAP = {};

// 官方实时余票查验本地持久化缓存 (保存在 localStorage 中，刷新页面依然保留时间与余票，无需重复查验)
const SEAT_QUERY_CACHE_KEY = 'changlong_seat_live_cache_v2';
function getSeatQueryCache() {
  try {
    const raw = localStorage.getItem(SEAT_QUERY_CACHE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch (e) {
    return {};
  }
}
function setSeatQueryCache(cache) {
  try {
    localStorage.setItem(SEAT_QUERY_CACHE_KEY, JSON.stringify(cache));
  } catch (e) {}
}
window.LIVE_QUERY_CACHE = getSeatQueryCache();

// 格式化查询时间微标 (当天显示 "16:18查"，非当天显示 "10-21查")
function formatCheckTime(timestamp, fallback) {
  if (!timestamp) return fallback || '刚刚';
  const dt = new Date(timestamp);
  if (isNaN(dt.getTime())) return fallback || '刚刚';
  const now = new Date();
  const isToday = dt.getFullYear() === now.getFullYear() && 
                  dt.getMonth() === now.getMonth() && 
                  dt.getDate() === now.getDate();
  const hh = String(dt.getHours()).padStart(2, '0');
  const mm = String(dt.getMinutes()).padStart(2, '0');
  if (isToday) {
    return `${hh}:${mm}查`;
  } else {
    const m = dt.getMonth() + 1;
    const d = dt.getDate();
    return `${m}-${d}查`;
  }
}

function initAvailableRoutesData() {
  if (window.AVAILABLE_ROUTES_DATA && window.AVAILABLE_ROUTES_DATA.routes) {
    window.AVAILABLE_ROUTES_DATA.routes.forEach(r => {
      AVAILABLE_ROUTES_MAP[`${r.from}-${r.to}`] = r;
    });
    updateTicketStatusBanner(window.AVAILABLE_ROUTES_DATA);
  }

  // 核心架构：全面通过后端 SQLite 数据库动态 API /api/available-routes 获取大盘与在库查验流水
  fetch('/api/available-routes')
    .then(res => res.json())
    .then(data => {
      if (data && data.routes && data.routes.length > 0) {
        window.AVAILABLE_ROUTES_DATA = data;
        AVAILABLE_ROUTES_MAP = {};
        data.routes.forEach(r => {
          AVAILABLE_ROUTES_MAP[`${r.from}-${r.to}`] = r;
        });
        // 自动将后端数据库已落库的实时查验流水（如 17:25查）同步至前端缓存
        if (data.seatCache && typeof data.seatCache === 'object') {
          window.LIVE_QUERY_CACHE = window.LIVE_QUERY_CACHE || {};
          Object.assign(window.LIVE_QUERY_CACHE, data.seatCache);
        }
        updateTicketStatusBanner(data);
        renderDirectRoutes();
      }
    })
    .catch(err => {
      console.warn('获取数据库放票大盘接口异常:', err);
    });
}

function updateTicketStatusBanner(data) {
  const banner = document.getElementById('ticketStatusBanner');
  const textEl = document.getElementById('ticketStatusText');
  if (banner && textEl && data) {
    textEl.textContent = `官方放票大盘已同步 · ${data.totalAvailableRoutes || 309} 条航线有票 (${(data.totalDatePoints || 6315).toLocaleString()} 个出行日)`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  injectSvgIcons();
  initAvailableRoutesData();
  initCustomSelects();
  initFeeConfigModal();
  initPatrolConfigModal();
  initFliggyGuideModal();
  initTabNavigation();

  renderDirectRoutes();
  renderTransferPlanner();
  renderSeasonalGuide();

  // 绑定事件
  const toggleOnlyAvail = document.getElementById('toggleOnlyAvailable');
  if (toggleOnlyAvail) {
    toggleOnlyAvail.addEventListener('change', () => {
      renderDirectRoutes();
    });
  }

  document.getElementById('btnPlanTransfer').addEventListener('click', () => {
    const from = csTransferOriginInstance.getValue();
    const to = csTransferTargetInstance.getValue();
    executeTransferPlanning(from, to);
  });

  document.getElementById('btnRollBlindbox').addEventListener('click', () => {
    executeBlindboxRoll();
  });
});

/**
 * 注入各处专业 SVG 矢量图标
 */
function injectSvgIcons() {
  const setHtml = (id, iconSvg) => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = iconSvg;
  };

  setHtml('iconLogo', ICONS.plane);
  setHtml('iconSettings', ICONS.settings);
  setHtml('iconRadar', ICONS.radar);
  setHtml('iconModalRadar', ICONS.radar);
  setHtml('iconArrowTransfer', ICONS.arrowRight);
  setHtml('iconZap', ICONS.zap);
  setHtml('iconDices', ICONS.dices);
  setHtml('iconDiceBtn', ICONS.compass);
  setHtml('iconCalcBtn', ICONS.calculator);
  setHtml('iconRadarBtn', ICONS.radar);
  setHtml('iconModalSettings', ICONS.settings);

  document.querySelectorAll('.tab-btn .tab-icon').forEach(el => {
    const iconName = el.getAttribute('data-icon');
    if (ICONS[iconName]) {
      el.innerHTML = ICONS[iconName];
    }
  });
}

/**
 * 交互式 Toast 轻提示
 */
export function showToast(message, duration = 3200) {
  const existing = document.querySelector('.app-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'app-toast';
  toast.innerHTML = `<span>${message}</span>`;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translate(-50%, -10px)';
    toast.style.transition = 'all 0.25s ease-in';
    setTimeout(() => toast.remove(), 260);
  }, duration);
}

/**
 * 飞猪国内机票直达查票跳转
 */
window.openFliggyFlight = function(origin, target, event) {
  if (event) event.stopPropagation();
  
  // 飞猪机票预订专区入口
  const url = `https://www.fliggy.com/flight/`;
  window.open(url, '_blank', 'noopener,noreferrer');
  
  showToast(`已为您打开飞猪网页端！可在搜索栏输入【${origin} ➔ ${target}】快速查看长龙执飞班次与商业票价`);
};

/**
 * 初始化飞猪卡券兑换指南弹窗
 */
function initFliggyGuideModal() {
  const modal = document.getElementById('modalFliggyGuide');
  const btnOpenHeader = document.getElementById('btnOpenFliggyModal');
  const btnOpenBanner = document.getElementById('btnQuickFliggyTips');
  const btnClose = document.getElementById('btnCloseFliggyGuide');

  const openModal = () => {
    if (modal) modal.style.display = 'flex';
  };

  const closeModal = () => {
    if (modal) modal.style.display = 'none';
  };

  if (btnOpenHeader) btnOpenHeader.addEventListener('click', openModal);
  if (btnOpenBanner) btnOpenBanner.addEventListener('click', openModal);
  if (btnClose) btnClose.addEventListener('click', closeModal);

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });
  }
}

/**
 * 构建目的地选择框的选项列表
 * 核心规则：严格只展示当前出发地真实可直达的目的地城市！绝不包含无法直飞的城市！
 * 如果出发地为“全部”，则展示全网所有长龙通航城市供反向查询。
 */
function buildDestinationOptions(originCity) {
  const REGION_ORDER = ['华东', '华南', '西南', '西北', '华中', '华北', '东北'];

  // 情况 1: 用户指定了具体出发地（非“全部”）
  if (originCity && originCity !== '全部') {
    const directDests = DIRECT_MAP[originCity] || [];

    if (directDests.length === 0) {
      return [
        { 
          value: '全部', 
          label: '暂无直飞目的地', 
          sublabel: `${originCity}暂无出港直飞航线`, 
          badge: '无直飞',
          group: '全部直达'
        }
      ];
    }

    const firstOption = {
      value: '全部',
      label: '全部直飞目的地',
      sublabel: `查看【${originCity}】直达全部 ${directDests.length} 个城市`,
      badge: `${directDests.length}个直达`,
      group: '全部直达'
    };

    // 严格过滤：仅收录该出发地能直达的目的地城市，不包含任何需中转的冗余城市
    const destItems = directDests.map(city => {
      const meta = CITY_METADATA[city] || {};
      const route = ROUTES_NETWORK.find(r => r.from === originCity && r.to === city);
      const distanceStr = route && route.distance ? `${route.distance}km` : '';
      const region = meta.region || '其他';
      const province = meta.province || '';
      const sublabel = [province, distanceStr].filter(Boolean).join(' · ');

      return {
        value: city,
        label: city,
        sublabel: sublabel,
        badge: meta.tags?.[0] || `${region}直达`,
        group: `${region}地区 (${originCity}直飞)`,
        region: region,
        pinyin: meta.pinyin || ''
      };
    });

    destItems.sort((a, b) => {
      const rA = REGION_ORDER.indexOf(a.region);
      const rB = REGION_ORDER.indexOf(b.region);
      const rankA = rA === -1 ? 99 : rA;
      const rankB = rB === -1 ? 99 : rB;
      if (rankA !== rankB) return rankA - rankB;
      return a.label.localeCompare(b.label, 'zh-Hans-CN');
    });

    return [firstOption, ...destItems];
  }

  // 情况 2: 出发地为“全部”（全网漫游反查）
  const firstOption = {
    value: '全部',
    label: '全部直飞目的地',
    sublabel: '全国 71 城市漫游反查',
    badge: '全网71城',
    group: '全部航线'
  };

  const allDestItems = Object.keys(CITY_METADATA).map(city => {
    const meta = CITY_METADATA[city] || {};
    const region = meta.region || '其他';
    const inCount = Object.values(DIRECT_MAP).filter(dests => dests.includes(city)).length;

    return {
      value: city,
      label: city,
      sublabel: meta.province || '',
      badge: inCount > 0 ? `${inCount}城直通` : '长龙通航点',
      group: `${region}地区`,
      region: region,
      pinyin: meta.pinyin || ''
    };
  });

  allDestItems.sort((a, b) => {
    const rA = REGION_ORDER.indexOf(a.region);
    const rB = REGION_ORDER.indexOf(b.region);
    const rankA = rA === -1 ? 99 : rA;
    const rankB = rB === -1 ? 99 : rB;
    if (rankA !== rankB) return rankA - rankB;
    return a.label.localeCompare(b.label, 'zh-Hans-CN');
  });

  return [firstOption, ...allDestItems];
}

/**
 * 初始化所有高级定制搜索下拉组件 CustomSelect
 */
function initCustomSelects() {
  const allCityOptions = Object.keys(CITY_METADATA).map(city => {
    const meta = CITY_METADATA[city] || {};
    const count = (DIRECT_MAP[city] || []).length;
    let group = '其他通航城市';
    if (city === '杭州') group = '核心特级大本营 (Tier 1)';
    else if (city === '银川' || city === '长春') group = '区域核心主枢纽 (Tier 1)';
    else if (meta.hub === 'tier2') group = '重点枢纽与基地 (Tier 2)';
    else if (meta.tags?.some(t => t.includes('滑雪') || t.includes('避寒') || t.includes('草原'))) group = '度假与风景胜地';

    return {
      value: city,
      label: city,
      sublabel: meta.province,
      badge: count > 0 ? `${count} 直飞` : '外围点',
      group,
      meta
    };
  }).sort((a, b) => {
    const groupRank = {
      '核心特级大本营 (Tier 1)': 1,
      '区域核心主枢纽 (Tier 1)': 2,
      '重点枢纽与基地 (Tier 2)': 3,
      '度假与风景胜地': 4,
      '其他通航城市': 5
    };
    if (groupRank[a.group] !== groupRank[b.group]) {
      return groupRank[a.group] - groupRank[b.group];
    }
    const countA = (DIRECT_MAP[a.value] || []).length;
    const countB = (DIRECT_MAP[b.value] || []).length;
    return countB - countA;
  });

  const originSelectOptions = [
    { value: '全部', label: '全部出发地', sublabel: '全国 71 个城市', badge: '全网' },
    ...allCityOptions
  ];

  // 1. 出发地选择器 (支持选择后联动更新目的地选择框，并自动匹配可选目的地)
  csOriginInstance = new CustomSelect({
    container: '#csOriginMount',
    options: originSelectOptions,
    value: currentOrigin,
    placeholder: '选择出发城市',
    onChange: (val) => {
      currentOrigin = val;

      // 1. 重新构建仅包含可选目的地的选项列表
      const nextDestOptions = buildDestinationOptions(currentOrigin);

      // 2. 自动匹配可选择的目的地：
      // 如果原目的地仍在新出发地的可选直飞列表中（且不等于当前出发地），保留原目的地；
      // 否则自动重置匹配为“全部”（即查看该出发地所有直飞航班）
      const isStillAvailable = nextDestOptions.some(opt => opt.value === currentDestination && opt.value !== '全部' && opt.value !== currentOrigin);
      if (!isStillAvailable) {
        currentDestination = '全部';
      }

      // 3. 更新目的地选择框组件的选项与当前选中值
      if (csDestInstance) {
        csDestInstance.setOptions(nextDestOptions, currentDestination);
      }

      // 4. 刷新航线展示
      renderDirectRoutes();
    }
  });

  // 1.5 目的地选择器 (解决用户选完出发地后只看可选目的地的精确匹配需求)
  csDestInstance = new CustomSelect({
    container: '#csDestMount',
    options: buildDestinationOptions(currentOrigin),
    value: currentDestination,
    placeholder: '选择目的地',
    onChange: (val) => {
      currentDestination = val;
      renderDirectRoutes();
    }
  });

  // 互换出发地与目的地
  const btnSwap = document.getElementById('btnSwapCity');
  if (btnSwap) {
    btnSwap.addEventListener('click', () => {
      if (currentDestination === '全部') {
        showToast('请先选择一个具体目的地再进行互换');
        return;
      }
      const prevOrigin = currentOrigin;
      const prevDest = currentDestination;

      currentOrigin = prevDest;

      // 计算互换后新出发地的可选目的地列表
      const nextDestOptions = buildDestinationOptions(currentOrigin);
      // 自动匹配：检查原出发地是否在反向直飞列表中
      const canFlyBack = nextDestOptions.some(opt => opt.value === prevOrigin);
      currentDestination = canFlyBack ? prevOrigin : '全部';

      csOriginInstance.setValue(currentOrigin);
      csDestInstance.setOptions(nextDestOptions, currentDestination);
      renderDirectRoutes();

      if (canFlyBack) {
        showToast(`已互换航线：${currentOrigin} ⇄ ${currentDestination}`);
      } else {
        showToast(`已切换出发地为【${currentOrigin}】，已自动匹配为其所有直飞目的地`);
      }
    });
  }

  // 2. 区域筛选器
  csRegionInstance = new CustomSelect({
    container: '#csRegionMount',
    options: [
      { value: '全部', label: '全部区域', badge: '全网' },
      { value: '西北', label: '西北地区', sublabel: '新疆/宁夏/青海/甘肃/陕西' },
      { value: '西南', label: '西南地区', sublabel: '云南/四川/贵州/重庆' },
      { value: '东北', label: '东北地区', sublabel: '黑龙江/吉林/辽宁' },
      { value: '华东', label: '华东地区', sublabel: '江浙沪/山东/江西/福建' },
      { value: '华南', label: '华南地区', sublabel: '广东/海南/广西' },
      { value: '华中', label: '华中地区', sublabel: '湖北/湖南/河南' },
      { value: '华北', label: '华北地区', sublabel: '北京/内蒙古/山西/河北' }
    ],
    value: currentRegion,
    placeholder: '区域筛选',
    searchable: false,
    onChange: (val) => {
      currentRegion = val;
      renderDirectRoutes();
    }
  });

  // 3. 接驳出发地与目的地
  csTransferOriginInstance = new CustomSelect({
    container: '#csTransferOriginMount',
    options: allCityOptions,
    value: '杭州',
    placeholder: '接驳出发地'
  });

  csTransferTargetInstance = new CustomSelect({
    container: '#csTransferTargetMount',
    options: allCityOptions,
    value: '阿勒泰',
    placeholder: '梦想目的地'
  });

  // 4. 盲盒城市与主题偏好
  csBlindboxOriginInstance = new CustomSelect({
    container: '#csBlindboxOriginMount',
    options: allCityOptions,
    value: '杭州',
    placeholder: '盲盒出发城市'
  });

  csBlindboxTagInstance = new CustomSelect({
    container: '#csBlindboxTagMount',
    options: [
      { value: '全部', label: '随心不限', badge: '所有' },
      { value: '滑雪', label: '滑雪与粉雪天堂', sublabel: '阿勒泰/长春/哈尔滨/通化' },
      { value: '避寒', label: '温暖过冬避寒', sublabel: '西双版纳/三亚/海口/芒市' },
      { value: '草原', label: '初夏草原与湖泊', sublabel: '北疆/呼伦贝尔/西宁' },
      { value: '美食', label: '市井烟火逛吃', sublabel: '成都/广州/徐州/长沙' },
      { value: '水乡', label: '水乡古镇与山水', sublabel: '杭州/嘉兴/丽江/恩施' }
    ],
    value: '全部',
    searchable: false
  });
}

/**
 * 选项卡 Tab 切换
 */
function initTabNavigation() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.style.display = 'none');

      btn.classList.add('active');
      const contentEl = document.getElementById(targetTab);
      if (contentEl) contentEl.style.display = 'block';

      if (targetTab === 'tab-map') {
        renderMapExplorer();
      }
    });
  });
}

/**
 * 机建燃油配置模态框
 */
function initFeeConfigModal() {
  const modal = document.getElementById('modalFeeConfig');
  const btnOpen = document.getElementById('btnOpenFeeConfig');
  const btnClose = document.getElementById('btnCloseFeeModal');
  const btnReset = document.getElementById('btnResetFeeConfig');
  const btnSave = document.getElementById('btnSaveFeeConfig');

  const updateHeaderLabel = (config) => {
    document.getElementById('currentFeeLabel').textContent = 
      `税费: 机建¥${config.airportBuildFee} / 燃油¥${config.fuel800Above}`;
  };

  const syncFormValues = () => {
    const cfg = getFeeConfig();
    document.getElementById('inputAirportBuild').value = cfg.airportBuildFee;
    document.getElementById('inputFuel800Below').value = cfg.fuel800Below;
    document.getElementById('inputFuel800Above').value = cfg.fuel800Above;
    updateHeaderLabel(cfg);
  };

  syncFormValues();

  btnOpen.addEventListener('click', () => {
    syncFormValues();
    modal.style.display = 'flex';
  });

  btnClose.addEventListener('click', () => {
    modal.style.display = 'none';
  });

  btnReset.addEventListener('click', () => {
    saveFeeConfig(DEFAULT_FEE_CONFIG);
    syncFormValues();
    renderDirectRoutes();
    renderCalculator();
  });

  btnSave.addEventListener('click', () => {
    const nextCfg = {
      airportBuildFee: Number(document.getElementById('inputAirportBuild').value) || 0,
      fuel800Below: Number(document.getElementById('inputFuel800Below').value) || 0,
      fuel800Above: Number(document.getElementById('inputFuel800Above').value) || 0
    };
    saveFeeConfig(nextCfg);
    syncFormValues();
    modal.style.display = 'none';
    renderDirectRoutes();
    renderCalculator();
  });
}

/**
 * 核心巡检航线配置模态框 (上限30条，删一个才能加一个，城市级联直飞，支持保存到后端)
 */
const DEFAULT_HOT_ROUTES = [
  ["杭州", "阿勒泰"], ["杭州", "喀什"], ["杭州", "克拉玛依"], ["杭州", "西双版纳"],
  ["杭州", "丽江"], ["杭州", "三亚"], ["杭州", "海口"], ["杭州", "哈尔滨"],
  ["杭州", "长春"], ["杭州", "成都"], ["杭州", "重庆"], ["杭州", "广州"],
  ["杭州", "深圳"], ["杭州", "珠海"], ["杭州", "贵阳"], ["杭州", "昆明"],
  ["杭州", "乌鲁木齐"], ["杭州", "西宁"], ["杭州", "银川"], ["杭州", "大连"],
  ["杭州", "沈阳"], ["杭州", "海拉尔"], ["银川", "杭州"], ["银川", "乌鲁木齐"],
  ["银川", "喀什"], ["银川", "三亚"], ["银川", "广州"], ["长春", "杭州"],
  ["长春", "三亚"], ["长春", "成都"]
];

const PATROL_STORAGE_KEY = 'changlong_custom_patrol_routes_v1';

function initPatrolConfigModal() {
  const modal = document.getElementById('modalPatrolConfig');
  const btnOpen = document.getElementById('btnOpenPatrolConfig');
  const btnClose = document.getElementById('btnClosePatrolModal');
  const btnCancel = document.getElementById('btnCancelPatrolConfig');
  const btnReset = document.getElementById('btnResetPatrolConfig');
  const btnSave = document.getElementById('btnSavePatrolConfig');

  const btnLabel = document.getElementById('patrolConfigBtnLabel');
  const badgeStatus = document.getElementById('patrolSlotsBadge');
  const slotsDesc = document.getElementById('patrolSlotsDesc');
  const listCount = document.getElementById('patrolListCount');
  const routesGrid = document.getElementById('patrolRoutesGrid');

  const addCard = document.getElementById('patrolAddCard');
  const addTip = document.getElementById('patrolAddTip');
  const btnAdd = document.getElementById('btnAddPatrolRoute');
  const statusBanner = document.querySelector('.patrol-status-banner');

  if (!modal || !btnOpen) return;

  const MAX_SLOTS = 30;
  let currentRoutes = [...DEFAULT_HOT_ROUTES];
  let csPatrolFromInstance = null;
  let csPatrolToInstance = null;

  const updateHeaderDisplay = () => {
    if (btnLabel) {
      btnLabel.textContent = `巡检航线: ${currentRoutes.length}/${MAX_SLOTS}`;
    }
  };

  // 从本地 localStorage 或后端 API 同步当前配置
  const syncFromServer = async () => {
    try {
      const res = await fetch('/api/patrol/hot-routes');
      if (res.ok) {
        const json = await res.json();
        if (json && Array.isArray(json.routes) && json.routes.length > 0) {
          currentRoutes = json.routes.slice(0, MAX_SLOTS);
          localStorage.setItem(PATROL_STORAGE_KEY, JSON.stringify(currentRoutes));
        }
      }
    } catch (e) {
      const local = localStorage.getItem(PATROL_STORAGE_KEY);
      if (local) {
        try {
          const parsed = JSON.parse(local);
          if (Array.isArray(parsed) && parsed.length > 0) {
            currentRoutes = parsed.slice(0, MAX_SLOTS);
          }
        } catch (err) {}
      }
    }
    updateHeaderDisplay();
  };

  // 根据出发城市构建直飞到达城市的可选项
  const buildPatrolDestOptions = (originCity) => {
    const dests = DIRECT_MAP[originCity] || [];
    if (dests.length === 0) {
      return [{ value: '', label: '暂无直飞目的地', sublabel: `${originCity}暂无出港航班`, badge: '无直飞', group: '直飞' }];
    }
    return dests.map(city => {
      const meta = CITY_METADATA[city] || {};
      const region = meta.region || '其他';
      return {
        value: city,
        label: city,
        sublabel: meta.province || '',
        badge: '直飞',
        group: `${originCity} 直飞`
      };
    });
  };

  // 初始化高级定制搜索选择框 (CustomSelect，支持打字和拼音检索)
  const initCitySelects = () => {
    const mountFrom = document.getElementById('patrolFromMount');
    const mountTo = document.getElementById('patrolToMount');
    if (!mountFrom || !mountTo) return;

    if (csPatrolFromInstance && csPatrolToInstance) return;

    const origins = Object.keys(DIRECT_MAP).filter(city => (DIRECT_MAP[city] || []).length > 0);
    origins.sort((a, b) => (DIRECT_MAP[b] || []).length - (DIRECT_MAP[a] || []).length);

    const fromOptions = origins.map(city => {
      const count = (DIRECT_MAP[city] || []).length;
      const meta = CITY_METADATA[city] || {};
      let group = '其他通航城市';
      if (city === '杭州') group = '核心大本营 (Tier 1)';
      else if (city === '银川' || city === '长春') group = '区域核心主枢纽';
      else if (count >= 8) group = '重点枢纽与基地';

      return {
        value: city,
        label: city,
        sublabel: meta.province || '',
        badge: `${count}直飞`,
        group
      };
    });

    const defaultFrom = '杭州';
    const initialDestOptions = buildPatrolDestOptions(defaultFrom);

    csPatrolFromInstance = new CustomSelect({
      container: '#patrolFromMount',
      options: fromOptions,
      value: defaultFrom,
      placeholder: '打字或拼音搜索出发地',
      searchable: true,
      onChange: (val) => {
        const nextDestOpts = buildPatrolDestOptions(val);
        const nextDefaultDest = nextDestOpts[0]?.value || '';
        csPatrolToInstance.setOptions(nextDestOpts, nextDefaultDest);
      }
    });

    csPatrolToInstance = new CustomSelect({
      container: '#patrolToMount',
      options: initialDestOptions,
      value: initialDestOptions[0]?.value || '',
      placeholder: '搜索/选择直飞目的地',
      searchable: true
    });
  };

  // 渲染 30 槽位已选列表与满额锁定控制（删一个才能加一个）
  const renderList = () => {
    const len = currentRoutes.length;
    if (listCount) listCount.textContent = len;

    const isFull = len >= MAX_SLOTS;

    // 顶部状态栏与 Badge 状态
    if (statusBanner) {
      if (isFull) {
        statusBanner.className = 'patrol-status-banner is-full';
      } else {
        statusBanner.className = 'patrol-status-banner is-available';
      }
    }

    if (badgeStatus) {
      if (isFull) {
        badgeStatus.className = 'patrol-badge-status status-full';
        badgeStatus.textContent = `席位: ${len} / ${MAX_SLOTS} 满载`;
      } else {
        badgeStatus.className = 'patrol-badge-status status-avail';
        badgeStatus.textContent = `席位: ${len} / ${MAX_SLOTS} 可添加`;
      }
    }

    if (slotsDesc) {
      if (isFull) {
        slotsDesc.textContent = '(已达 30 席位上限，删一个方可添加新航线)';
        slotsDesc.style.color = '#dc2626';
      } else {
        slotsDesc.textContent = `(剩余 ${MAX_SLOTS - len} 个空位，可自由添加新航线)`;
        slotsDesc.style.color = '#059669';
      }
    }

    // 添加卡片锁定/置灰控制（满额时禁用）
    if (addCard) {
      if (isFull) {
        addCard.classList.add('is-locked');
        if (addTip) addTip.textContent = '已达 30 席位上限，请先点击上方已有航线的 × 移除一条释放槽位';
        if (csPatrolFromInstance) csPatrolFromInstance.setDisabled(true);
        if (csPatrolToInstance) csPatrolToInstance.setDisabled(true);
        if (btnAdd) btnAdd.disabled = true;
      } else {
        addCard.classList.remove('is-locked');
        if (addTip) addTip.textContent = `当前剩余 ${MAX_SLOTS - len} 个可用席位，请选择直飞航线后点击添加`;
        if (csPatrolFromInstance) csPatrolFromInstance.setDisabled(false);
        if (csPatrolToInstance) csPatrolToInstance.setDisabled(false);
        if (btnAdd) btnAdd.disabled = false;
      }
    }

    // 渲染精致航线 Tag 流
    if (routesGrid) {
      if (currentRoutes.length === 0) {
        routesGrid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 24px 0;">当前暂无巡检航线，可从下方添加</div>`;
      } else {
        routesGrid.innerHTML = currentRoutes.map((r, idx) => {
          const from = r[0];
          const to = r[1];
          return `
            <div class="patrol-route-pill">
              <span class="patrol-route-idx">${idx + 1}</span>
              <span class="patrol-route-name">${from} <span class="route-sep">→</span> ${to}</span>
              <button type="button" class="patrol-route-remove" data-idx="${idx}" title="移除该航线以腾出席位">&times;</button>
            </div>
          `;
        }).join('');

        // 绑定删除按钮
        routesGrid.querySelectorAll('.patrol-route-remove').forEach(btn => {
          btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const idx = parseInt(btn.getAttribute('data-idx'), 10);
            if (!isNaN(idx) && idx >= 0 && idx < currentRoutes.length) {
              const removed = currentRoutes.splice(idx, 1)[0];
              renderList();
              showToast(`已移除【${removed[0]} ➔ ${removed[1]}】，腾出 1 个席位`);
            }
          });
        });
      }
    }
  };

  // 添加航线事件
  if (btnAdd) {
    btnAdd.addEventListener('click', () => {
      if (currentRoutes.length >= MAX_SLOTS) {
        showToast('已达到 30 条席位上限！请先点击已有航线右侧的 × 删一个再添加');
        return;
      }
      const from = csPatrolFromInstance ? csPatrolFromInstance.getValue() : '';
      const to = csPatrolToInstance ? csPatrolToInstance.getValue() : '';
      if (!from || !to) {
        showToast('请选择有效的出发地与目的地');
        return;
      }
      if (from === to) {
        showToast('出发地与目的地不能相同');
        return;
      }
      const exists = currentRoutes.some(r => r[0] === from && r[1] === to);
      if (exists) {
        showToast(`【${from} ➔ ${to}】已在巡检名单中，无需重复添加`);
        return;
      }
      currentRoutes.push([from, to]);
      renderList();
      showToast(`已成功添加【${from} ➔ ${to}】`);
    });
  }

  // 恢复默认 30 条
  if (btnReset) {
    btnReset.addEventListener('click', () => {
      currentRoutes = [...DEFAULT_HOT_ROUTES];
      renderList();
      showToast('已重置为官方推荐 Top 30 核心热门航线');
    });
  }

  // 保存配置
  if (btnSave) {
    btnSave.addEventListener('click', async () => {
      if (currentRoutes.length === 0) {
        showToast('巡检航线列表不能为空！');
        return;
      }
      localStorage.setItem(PATROL_STORAGE_KEY, JSON.stringify(currentRoutes));
      updateHeaderDisplay();

      try {
        const res = await fetch('/api/patrol/hot-routes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ routes: currentRoutes })
        });
        if (res.ok) {
          const ret = await res.json();
          showToast(`巡检航线已成功保存！共 ${ret.count || currentRoutes.length} 条已实时生效`);
        } else {
          showToast('已保存到本地配置 (后端服务正在后台同步)');
        }
      } catch (err) {
        showToast('已保存到本地浏览器配置');
      }

      modal.style.display = 'none';
    });
  }

  // 手动触发巡检与实时进度轮询 (平时待命，用户点击才执行)
  const btnTrigger = document.getElementById('btnTriggerPatrol');
  const indicator = document.getElementById('patrolRunningIndicator');
  const statusText = document.getElementById('patrolStatusText');
  const barWrap = document.getElementById('patrolProgressBarWrap');
  const bar = document.getElementById('patrolProgressBar');

  let pollTimer = null;

  const updatePatrolProgressUI = (state) => {
    if (!state) return;
    const isRunning = state.running;
    if (indicator) {
      if (isRunning) {
        indicator.textContent = '慢速拟人巡检中';
        indicator.style.background = '#fef3c7';
        indicator.style.color = '#b45309';
      } else {
        indicator.textContent = '待命静默中';
        indicator.style.background = '#e2e8f0';
        indicator.style.color = '#475569';
      }
    }
    if (statusText) {
      statusText.textContent = state.status_text || '待命状态 (无正在运行的巡检任务)';
    }
    if (btnTrigger) {
      btnTrigger.disabled = isRunning;
      btnTrigger.innerHTML = isRunning 
        ? `<span class="spin">⏳</span> 巡检执行中 (${state.completed || 0}/${state.total || 30})...` 
        : `<span>🚀</span> 立即开始巡检 (慢速安全)`;
    }
    if (barWrap && bar) {
      if (isRunning) {
        barWrap.style.display = 'block';
        const percent = state.total > 0 ? Math.round((state.completed / state.total) * 100) : 0;
        bar.style.width = `${percent}%`;
      } else {
        barWrap.style.display = 'none';
        bar.style.width = '0%';
      }
    }
  };

  const pollPatrolStatus = async () => {
    try {
      const res = await fetch('/api/patrol/status');
      if (res.ok) {
        const json = await res.json();
        const state = json.state;
        updatePatrolProgressUI(state);
        if (state && state.running) {
          pollTimer = setTimeout(pollPatrolStatus, 2000);
        } else {
          pollTimer = null;
        }
      }
    } catch (e) {
      pollTimer = null;
    }
  };

  if (btnTrigger) {
    btnTrigger.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/patrol/trigger', { method: 'POST' });
        const json = await res.json();
        if (res.ok && json.ok) {
          showToast('已在后台启动慢速拟人巡检 (~4.5秒/条，耗时约2~3分钟)');
          if (pollTimer) clearTimeout(pollTimer);
          pollPatrolStatus();
        } else {
          showToast(json.error || '启动巡检失败');
        }
      } catch (err) {
        showToast('请求后端巡检接口失败，请检查服务状态');
      }
    });
  }

  // 弹窗开关控制
  const openModal = () => {
    initCitySelects();
    renderList();
    pollPatrolStatus();
    modal.style.display = 'flex';
  };
  const closeModal = () => {
    modal.style.display = 'none';
  };

  btnOpen.addEventListener('click', openModal);
  if (btnClose) btnClose.addEventListener('click', closeModal);
  if (btnCancel) btnCancel.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  // 首次自同步
  syncFromServer();
}

// 2026/2027 冬春航季长龙航空官方排班数据索引表 (支持一对多班次)
const ROUTE_FLIGHTS_MAP = {};
FLIGHTS_SCHEDULE.forEach(f => {
  const key = `${f.from}-${f.to}`;
  (ROUTE_FLIGHTS_MAP[key] = ROUTE_FLIGHTS_MAP[key] || []).push(f);
});

function formatFrequency(freq) {
  if (!freq) return '以放票为准';
  if (freq === '1234567') return '天天执飞';
  if (freq === '1357') return '周一三五日';
  if (freq === '246') return '周二四六';
  if (freq === '146') return '周一四六';
  if (freq === '23467') return '周二三四六日';
  const weekMap = { '1':'一', '2':'二', '3':'三', '4':'四', '5':'五', '6':'六', '7':'日' };
  return '周' + freq.split('').map(d => weekMap[d] || d).join('');
}

// 航线列表默认排序方式：按每日计划起飞时刻从早到晚排序
let currentRouteSort = 'time-asc';

window.setRouteSort = function(sortType) {
  currentRouteSort = sortType;
  renderDirectRoutes();
};

/**
 * 渲染 TAB 1: 航线列表 (全新现代化高信息密度列表与表格设计)
 * 支持：出发地单向查询、目的地反向查询、点对点精确匹配与智能中转引导
 */
function renderDirectRoutes() {
  const container = document.getElementById('routesContainer') || document.getElementById('routesGrid');
  const summaryEl = document.getElementById('originSummary');

  // Case 1: 出发地与目的地相同
  if (currentOrigin !== '全部' && currentDestination !== '全部' && currentOrigin === currentDestination) {
    summaryEl.textContent = `出发地与目的地不能相同，请选择不同的目的地城市`;
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 48px 20px; color: var(--text-secondary); background:#ffffff; border-radius:var(--radius-md); border:1px solid var(--border-subtle);">
        <p style="font-size: 1.05rem; font-weight:700; color:var(--text-primary); margin-bottom: 6px;">出发地与目的地相同 (${currentOrigin})</p>
        <p style="font-size: 0.86rem; color:var(--text-muted);">请在上方的【目的地】下拉框中选择您想要前往的其他城市！</p>
      </div>
    `;
    return;
  }

  // Case 2: 出发地 != 全部，目的地 == 全部 （经典全景单程直飞探索）
  if (currentOrigin !== '全部' && currentDestination === '全部') {
    const queryResult = queryDirectRoutes(currentOrigin);
    let filtered = queryResult.directList;

    if (currentRegion !== '全部') {
      filtered = filtered.filter(item => item.region === currentRegion);
    }

    summaryEl.textContent = `出发共 ${filtered.length} 个直飞目的地`;

    renderRouteCards(container, filtered, currentOrigin);
    return;
  }

  // Case 3: 出发地 != 全部，目的地 != 全部 （点对点精准航线查询）
  if (currentOrigin !== '全部' && currentDestination !== '全部') {
    const directDests = DIRECT_MAP[currentOrigin] || [];
    if (directDests.includes(currentDestination)) {
      const routeInfo = ROUTES_NETWORK.find(r => r.from === currentOrigin && r.to === currentDestination) || {};
      const tax = calculateTaxes(routeInfo.distance || 1000);
      const destMeta = CITY_METADATA[currentDestination] || {};
      const matched = [{
        from: currentOrigin,
        to: currentDestination,
        distance: routeInfo.distance || 0,
        isOver800Km: Boolean(routeInfo.isOver800Km),
        seasonStatus: routeInfo.seasonStatus || '正常执飞',
        hasReturn: (DIRECT_MAP[currentDestination] || []).includes(currentOrigin),
        tags: destMeta.tags || [],
        region: destMeta.region || '',
        airport: destMeta.airport || '',
        tax: tax.totalTax
      }];
      summaryEl.textContent = `${currentOrigin} ➔ ${currentDestination}`;
      renderRouteCards(container, matched, currentOrigin);
    } else {
      // 无直飞，智能提示中转
      const hasReverse = (DIRECT_MAP[currentDestination] || []).includes(currentOrigin);
      summaryEl.textContent = `暂无直飞`;
      container.innerHTML = `
        <div style="grid-column: 1 / -1; background:#ffffff; border:1px solid var(--border-subtle); border-radius:var(--radius-lg); padding:36px 24px; text-align:center; box-shadow:var(--shadow-subtle);">
          <h3 style="font-size:1.15rem; font-weight:800; color:var(--text-primary); margin-bottom:8px;">
            暂无【${currentOrigin} 直飞 ${currentDestination}】
          </h3>
          <p style="font-size:0.88rem; color:var(--text-secondary); max-width:540px; margin:0 auto 20px; line-height:1.6;">
            建议通过高铁接驳周边超级基地或经由大本营中转到达。
            ${hasReverse ? `<br><strong style="color:var(--accent-cyan);">反向【${currentDestination} ➔ ${currentOrigin}】有直飞，可点击上方互换按钮查看。</strong>` : ''}
          </p>
          <button class="btn-primary" id="btnGoTransferFromRoutes" style="margin:0 auto; padding:10px 24px; font-size:0.9rem;">
            规划【${currentOrigin} ➔ ${currentDestination}】中转接驳
          </button>
        </div>
      `;
      const btnGo = document.getElementById('btnGoTransferFromRoutes');
      if (btnGo) {
        btnGo.addEventListener('click', () => {
          document.querySelector('[data-tab="tab-transfer"]').click();
          csTransferOriginInstance.setValue(currentOrigin);
          csTransferTargetInstance.setValue(currentDestination);
          executeTransferPlanning(currentOrigin, currentDestination);
        });
      }
    }
    return;
  }

  // Case 4: 出发地 == 全部，目的地 != 全部 （反查哪些城市能直飞此目的地）
  if (currentOrigin === '全部' && currentDestination !== '全部') {
    const origins = [];
    Object.entries(DIRECT_MAP).forEach(([fromCity, dests]) => {
      if (dests.includes(currentDestination)) {
        const routeInfo = ROUTES_NETWORK.find(r => r.from === fromCity && r.to === currentDestination) || {};
        const destMeta = CITY_METADATA[currentDestination] || {};
        const fromMeta = CITY_METADATA[fromCity] || {};
        const tax = calculateTaxes(routeInfo.distance || 1000);
        origins.push({
          from: fromCity,
          to: currentDestination,
          distance: routeInfo.distance || 0,
          isOver800Km: Boolean(routeInfo.isOver800Km),
          seasonStatus: routeInfo.seasonStatus || '正常执飞',
          hasReturn: (DIRECT_MAP[currentDestination] || []).includes(fromCity),
          tags: fromMeta.tags || [],
          region: fromMeta.region || '',
          airport: destMeta.airport || '',
          tax: tax.totalTax
        });
      }
    });

    let filtered = origins;
    if (currentRegion !== '全部') {
      filtered = filtered.filter(item => item.region === currentRegion);
    }

    summaryEl.textContent = `共 ${filtered.length} 个城市直飞【${currentDestination}】`;
    renderRouteCards(container, filtered, null);
    return;
  }

  // Case 5: 出发地 == 全部，目的地 == 全部 （展示热门枢纽直飞航线）
  summaryEl.textContent = '';
  const hotList = [];
  ['杭州', '银川', '长春', '广州', '成都', '西安'].forEach(hub => {
    (DIRECT_MAP[hub] || []).slice(0, 5).forEach(dest => {
      const routeInfo = ROUTES_NETWORK.find(r => r.from === hub && r.to === dest) || {};
      const tax = calculateTaxes(routeInfo.distance || 1000);
      const destMeta = CITY_METADATA[dest] || {};
      hotList.push({
        from: hub,
        to: dest,
        distance: routeInfo.distance || 0,
        isOver800Km: Boolean(routeInfo.isOver800Km),
        seasonStatus: routeInfo.seasonStatus || '正常执飞',
        hasReturn: (DIRECT_MAP[dest] || []).includes(hub),
        tags: destMeta.tags || [],
        region: destMeta.region || '',
        airport: destMeta.airport || '',
        tax: tax.totalTax
      });
    });
  });
  renderRouteCards(container, hotList, null);
}

/**
 * 统一渲染航线列表（现代数据列表 / 表格视图，直观展示哪天有票与可兑天数）
 */
function renderRouteCards(container, list, fixedOrigin) {
  if (!list || list.length === 0) {
    container.innerHTML = `
      <div class="route-list-empty">
        <p style="font-size: 1.05rem; font-weight:700; color:var(--text-primary); margin-bottom: 6px;">该筛选条件下暂无直飞航线</p>
        <p style="font-size: 0.86rem; color:var(--text-muted); max-width:460px; margin:0 auto 16px;">建议切换区域或点击【接驳规划】查看周边高铁 1~2 小时大基地辐射方案！</p>
        <button class="btn-primary" onclick="document.querySelector('[data-tab=\\'tab-transfer\\']').click()">前往跨城接驳规划器</button>
      </div>
    `;
    return;
  }

  const onlyAvailable = document.getElementById('toggleOnlyAvailable')?.checked ?? true;

  // 1. 过滤：若开启“仅看有票航线”，只保留放票大盘中可兑天数 > 0 的航线
  let filteredList = [...list];
  if (onlyAvailable) {
    filteredList = filteredList.filter(item => {
      const fCity = fixedOrigin || item.from;
      const tCity = item.to;
      const avail = AVAILABLE_ROUTES_MAP[`${fCity}-${tCity}`];
      return Boolean(avail && avail.availableDaysCount > 0);
    });
  }

  if (filteredList.length === 0 && list.length > 0) {
    container.innerHTML = `
      <div class="route-list-empty">
        <p style="font-size: 1.05rem; font-weight:700; color:var(--text-primary); margin-bottom: 6px;">该城市当前暂无官方放票航线（或已被抢完）</p>
        <p style="font-size: 0.86rem; color:var(--text-muted); max-width:460px; margin:0 auto 16px;">您可以关闭上方的【仅看有票航线】开关查看所有常态直飞班次，或选择杭州/哈尔滨等大盘放票大户！</p>
        <button class="btn-primary" onclick="document.getElementById('toggleOnlyAvailable').checked=false; renderDirectRoutes();">查看全部常规排班</button>
      </div>
    `;
    return;
  }

  // 2. 排序处理：默认按可兑换天数由多到少从上到下排列 (放票最多排最前)
  let sortedList = [...filteredList];
  if (currentRouteSort === 'tickets-desc' || currentRouteSort === 'default') {
    sortedList.sort((a, b) => {
      const fA = fixedOrigin || a.from;
      const fB = fixedOrigin || b.from;
      const cntA = AVAILABLE_ROUTES_MAP[`${fA}-${a.to}`]?.availableDaysCount || 0;
      const cntB = AVAILABLE_ROUTES_MAP[`${fB}-${b.to}`]?.availableDaysCount || 0;
      if (cntB !== cntA) return cntB - cntA;
      return (b.distance || 0) - (a.distance || 0);
    });
  } else if (currentRouteSort === 'time-asc') {
    sortedList.sort((a, b) => {
      const listA = ROUTE_FLIGHTS_MAP[`${fixedOrigin || a.from}-${a.to}`] || [];
      const listB = ROUTE_FLIGHTS_MAP[`${fixedOrigin || b.from}-${b.to}`] || [];
      const timeA = listA[0]?.depTime || '99:99';
      const timeB = listB[0]?.depTime || '99:99';
      const diff = timeA.localeCompare(timeB);
      if (diff !== 0) return diff;
      return (b.distance || 0) - (a.distance || 0);
    });
  } else if (currentRouteSort === 'dist-desc') {
    sortedList.sort((a, b) => (b.distance || 0) - (a.distance || 0));
  } else if (currentRouteSort === 'dist-asc') {
    sortedList.sort((a, b) => (a.distance || 0) - (b.distance || 0));
  } else if (currentRouteSort === 'tax-asc') {
    sortedList.sort((a, b) => (a.tax || 0) - (b.tax || 0));
  } else if (currentRouteSort === 'name-asc') {
    sortedList.sort((a, b) => a.to.localeCompare(b.to, 'zh-Hans-CN'));
  }

  const rowsHtml = sortedList.map((item, idx) => {
    const fromCity = fixedOrigin || item.from;
    const toCity = item.to;
    const originMeta = CITY_METADATA[fromCity] || {};
    const destMeta = CITY_METADATA[toCity] || {};
    const fromAirport = originMeta.airport ? originMeta.airport.replace('国际机场','机场') : '出发地';
    const toAirport = destMeta.airport ? destMeta.airport.replace('国际机场','机场') : (item.airport || '目的地');

    // 官方放票余票信息
    const availInfo = AVAILABLE_ROUTES_MAP[`${fromCity}-${toCity}`];
    const hasTickets = Boolean(availInfo && availInfo.availableDaysCount > 0);
    const availDaysCount = availInfo ? availInfo.availableDaysCount : 0;
    const availDates = availInfo ? availInfo.availableDates : [];

    let distTag = '';
    if (item.distance >= 2500) {
      distTag = '<span class="tag-dist ultra" style="font-size:0.68rem; padding:2px 6px; border-radius:4px; background:#eff6ff; color:#1d4ed8;">超长大线</span>';
    } else if (item.distance >= 1500) {
      distTag = '<span class="tag-dist long" style="font-size:0.68rem; padding:2px 6px; border-radius:4px; background:#f0fdf4; color:#15803d;">中长线</span>';
    }

    let seasonBadge = '';
    if (item.seasonStatus && (item.seasonStatus.includes('待换季') || item.seasonStatus.includes('季节性'))) {
      seasonBadge = `<span class="carrier-mini" style="background:var(--accent-rose-light); color:var(--accent-rose); border:1px solid rgba(225,29,72,0.25); font-size:0.7rem; padding:1px 6px; border-radius:4px;">${item.seasonStatus}</span>`;
    }

    // 获取真实冬春航季排班信息
    const flightList = ROUTE_FLIGHTS_MAP[`${fromCity}-${toCity}`] || [];
    const f0 = flightList[0];
    let flightScheduleHtml = '';
    if (f0 && f0.flightNo) {
      flightScheduleHtml = `
        <div class="rc-flight-block">
          <div class="rc-flight-badges">
            <span class="${f0.stopover === '直飞' ? 'badge-stopover-direct' : 'badge-stopover-via'}" style="font-size:0.72rem; padding:2px 7px; border-radius:4px;">${f0.stopover || '直飞'}</span>
            <span style="font-weight:800; font-size:0.95rem; color:var(--text-primary); font-variant-numeric:tabular-nums;">${f0.flightNo}</span>
            <span style="font-size:0.75rem; color:var(--text-secondary); background:#f1f5f9; padding:2px 6px; border-radius:4px;">${f0.aircraft || 'A320'}</span>
            ${flightList.length > 1 ? `<span style="font-size:0.7rem; background:#ecfeff; color:#0e7490; padding:2px 6px; border-radius:4px; font-weight:700;">共${flightList.length}班</span>` : ''}
          </div>
          <div class="rc-schedule-time">
            <span>${f0.depTime}</span>
            <span style="color:var(--text-muted); font-size:0.85rem;">➔</span>
            <span>${f0.arrTime}</span>
            <span style="font-size:0.76rem; font-weight:500; color:var(--text-muted);">(${f0.duration})</span>
          </div>
          <div class="rc-flight-meta">
            <span>${formatFrequency(f0.frequency)}</span>
            ${flightList.length > 1 ? `<span style="color:var(--text-muted); font-size:0.72rem;">(另有 ${flightList.slice(1).map(f => f.depTime).join(', ')})</span>` : ''}
          </div>
        </div>
      `;
    } else {
      flightScheduleHtml = `
        <div class="rc-flight-block" style="color:var(--text-muted); font-size:0.8rem; justify-content:center;">
          <span style="color:var(--accent-amber); font-weight:700;">冬春换季排班</span>
          <span style="font-size:0.74rem;">长龙官方定期放票</span>
        </div>
      `;
    }

    // 具体可兑换出行日胶囊标签流
    let datesFlowHtml = '';
    if (hasTickets && availDates.length > 0) {
      const INITIAL_SHOW = 10;
      const firstSlice = availDates.slice(0, INITIAL_SHOW);
      const remainingSlice = availDates.slice(INITIAL_SHOW);

      const renderChip = (d) => {
        const dt = new Date(d);
        const dayOfWeek = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][dt.getDay()];
        const isWeekend = dt.getDay() === 0 || dt.getDay() === 6;
        const shortDate = d.slice(5); // "10-25"
        const cacheKey = `${fromCity}-${toCity}-${d}`;
        const cached = window.LIVE_QUERY_CACHE?.[cacheKey];
        let badgeHtml = '';
        let isChecked = false;
        let titleAttr = `点击查询 ${d} (${dayOfWeek}) 官方航班实时余票`;
        if (cached) {
          isChecked = true;
          const timeLabel = formatCheckTime(cached.timestamp, cached.timeFormatted);
          titleAttr = `查询时间：${cached.timeFormatted} · 畅飞卡余 ${cached.count} 张 (点击可重新查验)`;
          badgeHtml = cached.count > 0 
            ? `<span class="pill-check-tag pill-tag-success">余${cached.count} · ${timeLabel}</span>`
            : `<span class="pill-check-tag pill-tag-empty">兑完 · ${timeLabel}</span>`;
        }
        return `<span class="date-pill ${isWeekend ? 'date-pill-weekend' : ''} ${isChecked ? 'is-checked' : ''}" 
                      data-check-key="${cacheKey}" 
                      data-base-text="${shortDate} ${dayOfWeek}" 
                      onclick="window.checkLiveSeatCount('${fromCity}', '${toCity}', '${d}')" 
                      title="${titleAttr}"><span class="pill-date-txt">${shortDate} ${dayOfWeek}</span>${badgeHtml}</span>`;
      };

      datesFlowHtml = `
        <div class="rc-dates-deck">
          <div class="rc-dates-header">
            <div class="rc-dates-title">
              <span class="rc-dates-badge">可兑换 ${availDaysCount} 天</span>
            </div>
          </div>
          <div class="rc-dates-grid">
            ${firstSlice.map(renderChip).join('')}
            ${remainingSlice.length > 0 ? `
              <div class="rc-more-wrapper" id="more-dates-${idx}" style="display:none; gap:7px; flex-wrap:wrap;">
                ${remainingSlice.map(renderChip).join('')}
              </div>
              <button type="button" class="rc-show-more-btn" onclick="window.toggleMoreDates('${idx}', this)">展开全部 (${availDates.length}天) ▾</button>
            ` : ''}
          </div>
        </div>
      `;
    } else {
      datesFlowHtml = `
        <div class="rc-dates-deck" style="background:#f8fafc; border-color:#e2e8f0;">
          <div style="font-size:0.8rem; color:var(--text-muted); display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
            <span>暂无可兑换配额</span>
            <button class="btn-glass" style="padding:4px 10px; font-size:0.75rem;" onclick="window.openMapDrawer('${fromCity}-${toCity}')">接驳方案</button>
          </div>
        </div>
      `;
    }

    return `
      <div class="route-card-premium" data-route="${fromCity}-${toCity}">
        <div class="rc-main-row">
          <!-- 航线与机场起降 -->
          <div class="rc-city-block">
            <div class="rc-cities">
              <span>${fromCity}</span>
              <span class="rc-plane-icon">➔</span>
              <span>${toCity}</span>
            </div>
            <div class="rc-airports">
              <span>${fromAirport}</span>
              <span>➔</span>
              <span>${toAirport}</span>
              ${seasonBadge}
            </div>
          </div>

          <!-- 真实执飞航班与计划时刻 -->
          ${flightScheduleHtml}

          <!-- 右侧核心数据与操作区 -->
          <div class="rc-stats-action-block">
            <div class="rc-stat-item">
              <div class="rc-stat-val">${item.distance ? item.distance.toLocaleString() : '--'} <span style="font-size:0.75rem; font-weight:500;">km</span></div>
              <div class="rc-stat-label">${distTag || (item.distance < 800 ? '短途航线' : '常规航线')}</div>
            </div>

            <div class="rc-stat-item">
              <div class="rc-stat-val" style="color:var(--accent-cyan);">¥${item.tax || 140}</div>
              <div class="rc-stat-label">${item.distance < 800 ? '机建¥50' : '机建¥50+燃油¥90'}</div>
            </div>

            <div class="rc-stat-item">
              <span class="region-pill" style="font-size:0.76rem; padding:4px 10px;">${item.region || destMeta.region || '国内'}</span>
            </div>

            <div class="rc-stat-item" style="flex-direction:row; gap:8px; align-items:center;">
              <button class="btn-primary" style="padding:6px 12px; font-size:0.8rem; border-radius:6px;" onclick="window.locateOnMap('${fromCity}', '${toCity}')" title="在地图中查看">
                地图查看
              </button>
              <button class="btn-glass" style="padding:6px 12px; font-size:0.8rem; border-radius:6px;" onclick="window.openMapDrawer('${fromCity}-${toCity}')" title="查看余票与接驳规划">
                接驳方案
              </button>
            </div>
          </div>
        </div>

        <!-- 卡片下半部：近60天可兑换出行日专区 -->
        ${datesFlowHtml}
      </div>
    `;
  }).join('');

  container.innerHTML = `
    <div class="route-cards-list-stream">
      <!-- 列表操作栏 -->
      <div class="route-list-toolbar" style="margin-bottom:16px;">
        <div class="route-list-summary-info">
          <span class="route-count-badge">共 ${sortedList.length} 条直飞航线</span>
        </div>
        <div class="route-list-sort-bar">
          <span class="sort-label">排序:</span>
          <div class="sort-btn-group">
            <button class="sort-pill-btn ${currentRouteSort === 'tickets-desc' || currentRouteSort === 'default' ? 'active' : ''}" onclick="window.setRouteSort('tickets-desc')">可兑天数最多 ↓</button>
            <button class="sort-pill-btn ${currentRouteSort === 'time-asc' ? 'active' : ''}" onclick="window.setRouteSort('time-asc')">起飞时间 (早到晚)</button>
            <button class="sort-pill-btn ${currentRouteSort === 'dist-desc' ? 'active' : ''}" onclick="window.setRouteSort('dist-desc')">航距最长 ↓</button>
            <button class="sort-pill-btn ${currentRouteSort === 'name-asc' ? 'active' : ''}" onclick="window.setRouteSort('name-asc')">目的地首字母</button>
          </div>
        </div>
      </div>

      <!-- 现代宽幅高级卡片流 -->
      <div style="display:flex; flex-direction:column; gap:16px;">
        ${rowsHtml}
      </div>
    </div>
  `;
}

// 供全局点击快速切换航段类型
window.switchToFlightType = function(type) {
  currentFlightType = type;
  document.querySelectorAll('#flightTypeFilter .type-pill').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-type') === type);
  });
  renderDirectRoutes();
};

window.switchToOrigin = function(city) {
  currentOrigin = city;
  const nextDestOptions = buildDestinationOptions(city);
  const isStillAvailable = nextDestOptions.some(opt => opt.value === currentDestination && opt.value !== '全部' && opt.value !== city);
  if (!isStillAvailable) {
    currentDestination = '全部';
  }
  if (csOriginInstance) csOriginInstance.setValue(city);
  if (csDestInstance) csDestInstance.setOptions(nextDestOptions, currentDestination);
  renderDirectRoutes();
};

// 供全局点击快速跳转中转规划
window.selectForTransfer = function(from, to) {
  if (csTransferOriginInstance) csTransferOriginInstance.setValue(from);
  if (csTransferTargetInstance) csTransferTargetInstance.setValue(to);
  
  const btn = document.querySelector('[data-tab="tab-transfer"]');
  if (btn) btn.click();
  executeTransferPlanning(from, to);
};

// ==========================================================================
// 地图探索与毛玻璃探层 (Map Explorer & Frosted Glass Drawer)
// ==========================================================================
let selectedMapRoute = null;
let mapInitialized = false;
let mapEventsBound = false;

// 基础 SVG 投影坐标系与 ViewBox 视口管理
const MAP_DEFAULT_VB = { x: 0, y: 0, w: 1000, h: 780 };
let currentMapVb = { ...MAP_DEFAULT_VB };
let mapAnimFrameId = null;

// 经纬度投影到 SVG 坐标 (1000 x 780)，完全与中国省份多边形严密对齐
const projectMapX = (lng) => 40 + ((lng - 73.0) / (135.0 - 73.0)) * 920.0;
const projectMapY = (lat) => 40 + ((53.5 - lat) / (53.5 - 18.0)) * 700.0;

function setMapViewBox(x, y, w, h) {
  currentMapVb.x = x;
  currentMapVb.y = y;
  currentMapVb.w = w;
  currentMapVb.h = h;
  const svg = document.getElementById('chinaFlightMapSvg');
  if (svg) {
    svg.setAttribute('viewBox', `${x.toFixed(2)} ${y.toFixed(2)} ${w.toFixed(2)} ${h.toFixed(2)}`);
  }
}

function animateMapViewBox(targetX, targetY, targetW, targetH, duration = 380, callback) {
  if (mapAnimFrameId) {
    cancelAnimationFrame(mapAnimFrameId);
    mapAnimFrameId = null;
  }
  const startX = currentMapVb.x;
  const startY = currentMapVb.y;
  const startW = currentMapVb.w;
  const startH = currentMapVb.h;
  const startTime = performance.now();

  function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  function step(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const ease = easeOutCubic(progress);

    const curX = startX + (targetX - startX) * ease;
    const curY = startY + (targetY - startY) * ease;
    const curW = startW + (targetW - startW) * ease;
    const curH = startH + (targetH - startH) * ease;

    setMapViewBox(curX, curY, curW, curH);

    if (progress < 1) {
      mapAnimFrameId = requestAnimationFrame(step);
    } else {
      mapAnimFrameId = null;
      if (typeof callback === 'function') callback();
    }
  }

  mapAnimFrameId = requestAnimationFrame(step);
}

// 切换选择地图聚焦城市 (不改变当前视口缩放/不移动镜头，保持全景或当前视口不变)
window.selectMapCity = function(cityName) {
  if (csMapCityInstance && csMapCityInstance.getValue() !== cityName) {
    csMapCityInstance.setValue(cityName);
  }
  if (window._renderMapLines) {
    window._renderMapLines(cityName);
  }
};

window.zoomToCity = window.selectMapCity;
window.filterMapByCity = window.selectMapCity;

window.zoomToRoute = function(fromCity, toCity) {
  window.selectMapCity(fromCity);
};

let isDraggingMap = false;
let isPointerDown = false;
let dragStartX = 0;
let dragStartY = 0;
let dragStartVb = { ...currentMapVb };

window.isMapDragging = function() {
  return isDraggingMap;
};

function initMapInteractions(svg) {
  if (mapEventsBound || !svg) return;
  mapEventsBound = true;

  // 1. 鼠标滚轮缩放 (以鼠标指针所在位置为中心平滑缩放)
  svg.addEventListener('wheel', (e) => {
    e.preventDefault();
    if (mapAnimFrameId) {
      cancelAnimationFrame(mapAnimFrameId);
      mapAnimFrameId = null;
    }
    const rect = svg.getBoundingClientRect();
    const mousePctX = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const mousePctY = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    const mouseSvgX = currentMapVb.x + mousePctX * currentMapVb.w;
    const mouseSvgY = currentMapVb.y + mousePctY * currentMapVb.h;

    const factor = e.deltaY < 0 ? 0.82 : 1.22;
    let newW = currentMapVb.w * factor;
    newW = Math.max(120, Math.min(1300, newW));
    let newH = newW * (780 / 1000);

    let newX = mouseSvgX - mousePctX * newW;
    let newY = mouseSvgY - mousePctY * newH;

    newX = Math.max(-200, Math.min(1200 - newW, newX));
    newY = Math.max(-150, Math.min(930 - newH, newY));

    setMapViewBox(newX, newY, newW, newH);
  }, { passive: false });

  // 2. 鼠标拖拽平移
  svg.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    if (mapAnimFrameId) {
      cancelAnimationFrame(mapAnimFrameId);
      mapAnimFrameId = null;
    }
    isPointerDown = true;
    isDraggingMap = false;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    dragStartVb = { ...currentMapVb };
  });

  window.addEventListener('mousemove', (e) => {
    if (!isPointerDown) return;
    const dx = e.clientX - dragStartX;
    const dy = e.clientY - dragStartY;
    if (!isDraggingMap && Math.hypot(dx, dy) > 5) {
      isDraggingMap = true;
      svg.classList.add('is-dragging');
    }
    if (isDraggingMap) {
      const rect = svg.getBoundingClientRect();
      const scaleX = currentMapVb.w / rect.width;
      const scaleY = currentMapVb.h / rect.height;
      const newX = dragStartVb.x - dx * scaleX;
      const newY = dragStartVb.y - dy * scaleY;
      setMapViewBox(newX, newY, currentMapVb.w, currentMapVb.h);
    }
  });

  window.addEventListener('mouseup', () => {
    if (isPointerDown) {
      isPointerDown = false;
      setTimeout(() => {
        isDraggingMap = false;
        svg.classList.remove('is-dragging');
      }, 50);
    }
  });

  // 3. 双击空白处放大
  svg.addEventListener('dblclick', (e) => {
    if (e.target.closest('.city-point') || e.target.closest('.flight-arc')) return;
    const rect = svg.getBoundingClientRect();
    const mousePctX = (e.clientX - rect.left) / rect.width;
    const mousePctY = (e.clientY - rect.top) / rect.height;
    const mouseSvgX = currentMapVb.x + mousePctX * currentMapVb.w;
    const mouseSvgY = currentMapVb.y + mousePctY * currentMapVb.h;

    const newW = Math.max(160, currentMapVb.w * 0.65);
    const newH = newW * (780 / 1000);
    const newX = mouseSvgX - mousePctX * newW;
    const newY = mouseSvgY - mousePctY * newH;
    animateMapViewBox(newX, newY, newW, newH, 320);
  });

  // 4. 重置按钮 (恢复全貌)
  const btnReset = document.getElementById('btnMapReset');
  if (btnReset) {
    btnReset.onclick = (e) => {
      e.stopPropagation();
      animateMapViewBox(0, 0, 1000, 780, 380);
      if (csMapCityInstance) {
        csMapCityInstance.setValue('ALL');
      }
      if (window._renderMapLines) {
        window._renderMapLines('ALL');
      }
    };
  }
}

function renderMapExplorer() {
  const svg = document.getElementById('chinaFlightMapSvg');
  const mountEl = document.getElementById('csMapCityMount');
  const drawer = document.getElementById('mapDetailDrawer');
  const closeBtn = document.getElementById('btnCloseMapDrawer');

  if (!svg) return;

  initMapInteractions(svg);

  // 绑定关闭按钮
  if (closeBtn) {
    closeBtn.onclick = () => {
      drawer.style.display = 'none';
      if (selectedMapRoute) {
        document.querySelectorAll('.flight-arc').forEach(el => el.classList.remove('selected'));
        selectedMapRoute = null;
      }
    };
  }

  // 1. 提取所有有可兑换票的航线列表 (来自 AVAILABLE_ROUTES_MAP)
  const availableRoutes = [];
  const activeCitiesSet = new Set();

  Object.values(AVAILABLE_ROUTES_MAP).forEach(r => {
    if (r.availableDaysCount > 0 && CITY_METADATA[r.from] && CITY_METADATA[r.to]) {
      availableRoutes.push(r);
      activeCitiesSet.add(r.from);
      activeCitiesSet.add(r.to);
    }
  });

  // 2. 初始化带搜索功能的城市选择下拉组件 CustomSelect
  if (mountEl && !csMapCityInstance) {
    const sortedCities = Array.from(activeCitiesSet).sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'));
    const mapCityOptions = [
      { value: 'ALL', label: `全部有票航线 (${availableRoutes.length}条)`, group: '航网总览' },
      { value: '杭州', label: '杭州', sublabel: '浙江 · 大本营', badge: '核心枢纽', group: '大本营' },
      ...sortedCities.filter(c => c !== '杭州').map(c => {
        const meta = CITY_METADATA[c] || {};
        return {
          value: c,
          label: c,
          sublabel: meta.province || '',
          badge: meta.hub === 'tier1' ? '枢纽' : '',
          group: meta.region || '通航城市',
          pinyin: meta.pinyin || c
        };
      })
    ];

    csMapCityInstance = new CustomSelect({
      container: mountEl,
      options: mapCityOptions,
      value: '杭州',
      placeholder: '搜索通航城市...',
      searchable: true,
      onChange: (val) => {
        window.selectMapCity(val);
      }
    });
  }

  function renderMapLines(focusedCity = 'ALL') {
    let svgHtml = '';

    // 背景微网格线与装饰
    svgHtml += `
      <defs>
        <linearGradient id="arcGlow" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.8" />
          <stop offset="50%" stop-color="#818cf8" stop-opacity="0.9" />
          <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.8" />
        </linearGradient>
      </defs>
    `;

    // 绘制中国经纬度经线纬线网格微底纹
    for (let x = 80; x < 960; x += 90) {
      svgHtml += `<line x1="${x}" y1="20" x2="${x}" y2="760" class="map-bg-grid" />`;
    }
    for (let y = 60; y < 740; y += 75) {
      svgHtml += `<line x1="30" y1="${y}" x2="970" y2="${y}" class="map-bg-grid" />`;
    }

    // 绘制中国各省份行政地理轮廓底层
    svgHtml += '<g class="map-china-provinces">';
    if (typeof CHINA_PROVINCES !== 'undefined' && Array.isArray(CHINA_PROVINCES)) {
      CHINA_PROVINCES.forEach(prov => {
        svgHtml += `<path d="${prov.path}" class="map-province-path"><title>${prov.name}</title></path>`;
      });
    }
    svgHtml += '</g>';

    // 绘制航线 (严格只绘制有票航线！)
    const displayedRoutes = availableRoutes.filter(r => {
      if (focusedCity === 'ALL') return true;
      return r.from === focusedCity || r.to === focusedCity;
    });

    displayedRoutes.forEach(r => {
      const metaFrom = CITY_METADATA[r.from];
      const metaTo = CITY_METADATA[r.to];
      const x1 = projectMapX(metaFrom.coords[0]);
      const y1 = projectMapY(metaFrom.coords[1]);
      const x2 = projectMapX(metaTo.coords[0]);
      const y2 = projectMapY(metaTo.coords[1]);

      // 贝塞尔曲线控制点 (产生优美的飞行动感弧线)
      const dx = x2 - x1;
      const dy = y2 - y1;
      const dist = Math.hypot(dx, dy);
      const cx = (x1 + x2) / 2 - (dy / dist) * Math.min(dist * 0.22, 60);
      const cy = (y1 + y2) / 2 + (dx / dist) * Math.min(dist * 0.22, 60) - 20;

      const routeKey = `${r.from}-${r.to}`;
      const isSelected = selectedMapRoute === routeKey;

      svgHtml += `
        <path d="M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}" 
              class="flight-arc ${isSelected ? 'selected' : ''}" 
              data-route="${routeKey}"
              onclick="if (!window.isMapDragging || !window.isMapDragging()) { window.openMapDrawer('${routeKey}'); }"
              onmouseenter="window.showMapTooltip(event, '${r.from} ➔ ${r.to}', '${r.availableDaysCount}')"
              onmouseleave="window.hideMapTooltip()" />
      `;
    });

    // 确定当前应该显示的城市集合：
    // 如果选定了某城市（如武汉），仅显示当前聚焦城市与有直飞航线连通的目的地城市；
    // 其余无直飞航线关联的城市，圆点与名字全部隐藏！
    const visibleCitiesSet = new Set();
    if (focusedCity === 'ALL') {
      activeCitiesSet.forEach(c => visibleCitiesSet.add(c));
    } else {
      visibleCitiesSet.add(focusedCity);
      displayedRoutes.forEach(r => {
        visibleCitiesSet.add(r.from);
        visibleCitiesSet.add(r.to);
      });
    }

// 密集区域城市专属字形排版与防重叠偏移映射表
const CITY_LABEL_LAYOUT = {
  // 长三角密集机场群 (放射状错开排版)
  '杭州': { dx: -12, dy: 6, anchor: 'end' },       // 大本营，文字向左下方，避开嘉兴与宁波
  '宁波': { dx: 11, dy: 5, anchor: 'start' },      // 向正右东海方向排
  '上海': { dx: 11, dy: -2, anchor: 'start' },     // 向东北东海方向排
  '嘉兴': { dx: -10, dy: 0, anchor: 'end' },       // 居中向左正横排
  '无锡': { dx: -10, dy: -5, anchor: 'end' },      // 向左上方排
  '常州': { dx: -10, dy: -3, anchor: 'end' },      // 向左排
  '南京': { dx: -10, dy: 4, anchor: 'end' },       // 向左排
  '温州': { dx: 10, dy: 4, anchor: 'start' },      // 向右排

  // 粤港澳大湾区
  '广州': { dx: -11, dy: -2, anchor: 'end' },
  '深圳': { dx: 11, dy: 4, anchor: 'start' },
  '珠海': { dx: -11, dy: 6, anchor: 'end' },

  // 成渝与西南
  '成都': { dx: -10, dy: 4, anchor: 'end' },
  '重庆': { dx: 10, dy: 4, anchor: 'start' },
  '泸州': { dx: -10, dy: 5, anchor: 'end' },
  '茅台': { dx: -10, dy: -2, anchor: 'end' },
  '遵义': { dx: 10, dy: 4, anchor: 'start' },

  // 京津冀
  '北京': { dx: -10, dy: -2, anchor: 'end' },

  // 山东群
  '青岛': { dx: 10, dy: 4, anchor: 'start' },
  '烟台': { dx: 10, dy: -2, anchor: 'start' },
  '威海': { dx: 10, dy: 4, anchor: 'start' },
  '济南': { dx: -10, dy: -3, anchor: 'end' },
  '潍坊': { dx: 0, dy: 13, anchor: 'middle' },
};

    // 绘制城市节点 (支持点击名字与圆点直接选择)
    activeCitiesSet.forEach(city => {
      if (!visibleCitiesSet.has(city)) return; // 隐藏无航线城市的名字与圆点！

      const meta = CITY_METADATA[city];
      if (!meta || !meta.coords) return;
      const cx = projectMapX(meta.coords[0]);
      const cy = projectMapY(meta.coords[1]);
      const isHub = city === '杭州' || meta.hub === 'tier1';
      const isFocused = city === focusedCity;

      // 获取当前城市专属排版偏移
      const layout = CITY_LABEL_LAYOUT[city] || { dx: 0, dy: -8, anchor: 'middle' };
      const textX = cx + layout.dx;
      const textY = cy + layout.dy;
      const textAnchor = layout.anchor;

      svgHtml += `
        <g class="city-point ${isHub ? 'hub' : ''} ${isFocused ? 'focused' : ''}" 
           data-city="${city}"
           onmouseenter="this.parentNode.appendChild(this);"
           onclick="if (!window.isMapDragging || !window.isMapDragging()) { window.selectMapCity('${city}'); }">
          <!-- 贴合圆点的紧凑圆形感应区 (半径 12px)，易点且绝不遮挡相邻城市 -->
          <circle cx="${cx}" cy="${cy}" r="12" fill="transparent" style="cursor:pointer;" />
          ${isFocused ? `<circle cx="${cx}" cy="${cy}" r="16" fill="none" stroke="#38bdf8" stroke-width="2" opacity="0.85"><animate attributeName="r" values="8;22;8" dur="2s" repeatCount="indefinite" /><animate attributeName="opacity" values="0.9;0.2;0.9" dur="2s" repeatCount="indefinite" /></circle>` : ''}
          ${city === '杭州' && !isFocused ? `<circle cx="${cx}" cy="${cy}" r="14" fill="none" stroke="#f59e0b" stroke-width="1.5" opacity="0.5"><animate attributeName="r" values="8;18;8" dur="3s" repeatCount="indefinite" /></circle>` : ''}
          <circle cx="${cx}" cy="${cy}" r="${isFocused ? 7 : isHub ? 5 : 3.5}" class="base-dot" fill="${isFocused ? '#38bdf8' : city === '杭州' ? '#f59e0b' : isHub ? '#38bdf8' : '#94a3b8'}" />
          <text x="${textX}" y="${textY}" text-anchor="${textAnchor}" style="cursor:pointer; pointer-events:auto;">${city}</text>
        </g>
      `;
    });

    svg.innerHTML = svgHtml;
  }

  window._renderMapLines = renderMapLines;

  // 默认渲染高亮初始城市航线
  const initialCity = csMapCityInstance ? csMapCityInstance.getValue() : '杭州';
  renderMapLines(initialCity);
  mapInitialized = true;
}

window.openMapDrawer = function(routeKey) {
  const [fromCity, toCity] = routeKey.split('-');
  const drawer = document.getElementById('mapDetailDrawer');
  const titleEl = document.getElementById('drawerRouteTitle');
  const bodyEl = document.getElementById('drawerBody');

  if (!drawer || !titleEl || !bodyEl) return;

  selectedMapRoute = routeKey;
  document.querySelectorAll('.flight-arc').forEach(el => {
    el.classList.toggle('selected', el.getAttribute('data-route') === routeKey);
  });

  const availInfo = AVAILABLE_ROUTES_MAP[routeKey] || { availableDaysCount: 0, availableDates: [] };
  const flightList = ROUTE_FLIGHTS_MAP[routeKey] || [];
  const f0 = flightList[0];
  const metaFrom = CITY_METADATA[fromCity] || {};
  const metaTo = CITY_METADATA[toCity] || {};
  const routeMeta = ROUTES_NETWORK.find(r => r.from === fromCity && r.to === toCity) || {};
  const tax = calculateTaxes(routeMeta.distance || 1000);

  titleEl.innerHTML = `<span>${fromCity}</span> <span style="color:var(--accent-cyan);">➔</span> <span>${toCity}</span>`;

  // 1. 航班起降概览
  let scheduleHtml = '';
  if (f0) {
    scheduleHtml = `
      <div class="drawer-section">
        <div class="drawer-section-title">航班排班与时刻</div>
        <div class="drawer-stat-grid">
          <div class="drawer-stat-box">
            <span class="drawer-stat-val">${f0.flightNo}</span>
            <span class="drawer-stat-lbl">${f0.stopover || '直飞'} · ${f0.aircraft || 'A320'}</span>
          </div>
          <div class="drawer-stat-box">
            <span class="drawer-stat-val">${f0.depTime} ➔ ${f0.arrTime}</span>
            <span class="drawer-stat-lbl">飞行 ${f0.duration}</span>
          </div>
          <div class="drawer-stat-box">
            <span class="drawer-stat-val" style="color:var(--accent-cyan);">¥${tax.totalTax}</span>
            <span class="drawer-stat-lbl">机建¥${tax.airportBuildFee || tax.buildFee || 50} + 燃油¥${tax.fuelFee}</span>
          </div>
        </div>
      </div>
    `;
  }

  // 2. 近 60 天官方放票日期流 (点击直接查当天余票张数，已查验日期直接读取缓存展示)
  let datesHtml = '';
  if (availInfo.availableDaysCount > 0) {
    let checkedCount = 0;
    let latestTimeObj = null;
    availInfo.availableDates.forEach(d => {
      const k = `${fromCity}-${toCity}-${d}`;
      const c = window.LIVE_QUERY_CACHE?.[k];
      if (c) {
        checkedCount++;
        if (!latestTimeObj || (c.timestamp && c.timestamp > (latestTimeObj.timestamp || 0))) {
          latestTimeObj = c;
        }
      }
    });

    let summaryHtml = '';
    if (checkedCount > 0 && latestTimeObj) {
      const latestStr = formatCheckTime(latestTimeObj.timestamp, latestTimeObj.timeFormatted);
      summaryHtml = `<span class="drawer-checked-summary" id="drawerCheckSummary" title="缓存已保存在本地，刷新不丢失">已查 ${checkedCount} 天 · 最近 ${latestStr}</span>`;
    } else {
      summaryHtml = `<span id="drawerCheckSummary" style="display:none;"></span>`;
    }

    datesHtml = `
      <div class="drawer-section">
        <div class="drawer-section-title" style="color:#059669; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:6px;">
          <span>近 60 天可兑换出行日 (${availInfo.availableDaysCount} 天)</span>
          ${summaryHtml}
        </div>
        <div class="drawer-dates-container">
          <div class="drawer-dates-grid">
            ${availInfo.availableDates.map(d => {
              const dt = new Date(d);
              const dayOfWeek = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][dt.getDay()];
              const isWeekend = dt.getDay() === 0 || dt.getDay() === 6;
              const shortDate = d.slice(5);
              const cacheKey = `${fromCity}-${toCity}-${d}`;
              const cached = window.LIVE_QUERY_CACHE?.[cacheKey];
              let badgeHtml = '';
              let isChecked = false;
              let titleAttr = `查询 ${d} 官方航班余票`;
              if (cached) {
                isChecked = true;
                const timeLabel = formatCheckTime(cached.timestamp, cached.timeFormatted);
                titleAttr = `查询时间：${cached.timeFormatted} · 畅飞卡余 ${cached.count} 张 (点击可重新查验)`;
                badgeHtml = cached.count > 0 
                  ? `<span class="pill-check-tag pill-tag-success">余${cached.count} · ${timeLabel}</span>`
                  : `<span class="pill-check-tag pill-tag-empty">兑完 · ${timeLabel}</span>`;
              }
              return `<span class="date-pill ${isWeekend ? 'date-pill-weekend' : ''} ${isChecked ? 'is-checked' : ''}" 
                            data-check-key="${cacheKey}" 
                            data-base-text="${shortDate} ${dayOfWeek}" 
                            onclick="window.checkLiveSeatCount('${fromCity}', '${toCity}', '${d}')" 
                            title="${titleAttr}"><span class="pill-date-txt">${shortDate} ${dayOfWeek}</span>${badgeHtml}</span>`;
            }).join('')}
          </div>
        </div>
      </div>
    `;
  } else {
    datesHtml = `
      <div class="drawer-section">
        <div class="drawer-dates-container" style="background:#f8fafc; border-color:#e2e8f0;">
          <span style="font-size:0.8rem; color:var(--text-muted);">本航线未来 60 天内暂无可兑换配额</span>
        </div>
      </div>
    `;
  }

  // 3. 跨城高铁接驳、落地延伸漫游与中转规划方案 (深度集成接驳规划)
  let transferHtml = '';
  try {
    const nearbyHubs = getNearbyRadiationHubs(fromCity);
    const transferSolutions = planMultiLegRoutes(fromCity, toCity);
    const destMeta = CITY_METADATA[toCity] || {};
    const destTags = destMeta.tags || [];

    // 落地后周边高铁/快线辐射与延伸漫游建议
    const DEST_ONWARD_TIPS = {
      '图木舒克': '唐王城机场出口乘车或城际铁路，1.5h 直抵【喀什古城/徕宁】、2h 直通【阿克苏托木尔峰大峡谷】，轻松串联南疆环线。',
      '阿勒泰': '雪都机场已开通【将军山雪场】免费接驳专线，更有直通车 3h 抵达【禾木村 / 喀纳斯】。',
      '喀什': '喀什徕宁机场 15 分钟直达喀什老城，可自驾沿中巴公路探秘白沙湖、慕士塔格峰与帕米尔高原。',
      '阿克苏': '阿克苏红旗坡机场前往托木尔大峡谷极为顺畅，搭乘南疆铁路动车快速通达库车大寺与龟兹遗址。',
      '阿拉尔': '塔里木机场出发，自驾 2 小时深入塔克拉玛干沙漠公路与塔里木河秋季胡杨林。',
      '西双版纳': '嘎洒机场 20 分钟可达星光夜市，中老铁路版纳站已开行至磨憨口岸及老挝琅勃拉邦跨境动车。',
      '丽江': '三义机场大巴 40 分钟直达大研古城，动车 1.5h 贯通大理苍山洱海或香格里拉雪山。',
      '长春': '龙嘉国际机场地下高铁站直通长春站与吉林站，高铁 1.5h 可达长白山站，滑雪温泉无缝换乘。',
      '哈尔滨': '太平机场已开通直通亚布力滑雪旅游度假区巴士专线，高铁 1h 可达亚布力西站滑雪。',
      '银川': '河东机场高铁站直通吴忠、中卫沙坡头，40 分钟即可从塞上江南踏入腾格里沙漠。'
    };

    const tagsText = (destTags && destTags.length > 0) ? destTags.slice(0, 3).join('、') : '当季特色风景与周边名胜';
    const onwardTip = DEST_ONWARD_TIPS[toCity] || `到达【${toCity}】(${destMeta.airport || '目的地机场'})后，可借助周边高铁与交通网络畅游 ${tagsText}。`;

    // 出发地周边超级高铁枢纽接驳建议
    let hubAdvice = '';
    const railHubs = (HIGH_SPEED_RAIL_CONNECTIONS && HIGH_SPEED_RAIL_CONNECTIONS[fromCity]) || [];
    if (railHubs.length > 0 && fromCity !== '杭州') {
      const validHubs = railHubs.filter(h => h && h.target && h.duration);
      if (validHubs.length > 0) {
        hubAdvice = validHubs.slice(0, 2).map(h => `
          <div class="drawer-transfer-card" style="margin-bottom:8px;">
            <div class="drawer-transfer-route">高铁接驳周边枢纽：【${h.target}】</div>
            <div class="drawer-transfer-detail">
              从 ${fromCity} 乘坐高铁约 ${h.duration}（参考票价 ${h.priceRange || '几十元'}）到达 ${h.target}，即可直飞全国更多目的地。
            </div>
          </div>
        `).join('');
      }
    }

    // 联程中转备选
    let solutionItems = '';
    if (transferSolutions && transferSolutions.length > 0) {
      const nonDirectSols = transferSolutions.filter(s => s.type !== 'direct');
      if (nonDirectSols.length > 0) {
        solutionItems = nonDirectSols.slice(0, 2).map(sol => `
          <div class="drawer-transfer-card" style="margin-bottom:8px;">
            <div class="drawer-transfer-route">备选中转：经由【${sol.steps[0].to}】中转联程</div>
            <div class="drawer-transfer-detail">
              第1程：${sol.steps[0].from} ➔ ${sol.steps[0].to} (${sol.steps[0].mode === 'flight' ? '长龙航空' : sol.steps[0].carrier || '高铁'})<br>
              第2程：${sol.steps[1].from} ➔ ${sol.steps[1].to} (长龙航空)<br>
              <strong>预计中转用时：${sol.estimatedDuration || '半日'} · 预估税费约 ¥${sol.totalTax || 280}</strong>
            </div>
          </div>
        `).join('');
      }
    }

    transferHtml = `
      <div class="drawer-section">
        <div class="drawer-section-title">接驳规划与延伸交通</div>
        
        <!-- 落地周边延伸接驳圈 -->
        <div class="drawer-transfer-card" style="margin-bottom:8px; background:rgba(238,242,255,0.7); border-color:#c7d2fe;">
          <div class="drawer-transfer-route" style="color:#3730a3;">落地【${toCity}】周边延伸漫游</div>
          <div class="drawer-transfer-detail" style="color:#312e81;">
            ${onwardTip}
          </div>
        </div>

        ${hubAdvice || ''}
        ${solutionItems || '<div style="font-size:0.78rem; color:var(--text-muted); padding:4px 0;">该航线为长龙直飞优势航线，建议优先兑换直飞出行；若直飞售罄，可考虑经由杭州或银川大本营中转。</div>'}
      </div>
    `;
  } catch(e) {
    console.warn('接驳规划计算失败:', e);
  }

  bodyEl.innerHTML = `
    ${scheduleHtml}
    ${datesHtml}
    ${transferHtml}
  `;

  drawer.style.display = 'flex';
};

window.locateOnMap = function(fromCity, toCity) {
  const mapTabBtn = document.querySelector('[data-tab="tab-map"]');
  if (mapTabBtn) mapTabBtn.click();
  setTimeout(() => {
    if (window.zoomToRoute) {
      window.zoomToRoute(fromCity, toCity);
    } else if (window.zoomToCity) {
      window.zoomToCity(fromCity);
    }
    window.openMapDrawer(`${fromCity}-${toCity}`);
  }, 120);
};

window.showMapTooltip = function(e, title, count) {
  const tip = document.getElementById('mapTooltip');
  if (!tip) return;
  const rect = document.getElementById('mapCanvasWrapper').getBoundingClientRect();
  tip.style.left = `${e.clientX - rect.left}px`;
  tip.style.top = `${e.clientY - rect.top}px`;
  tip.innerHTML = `<strong>${title}</strong> · 可兑 ${count} 天`;
  tip.style.display = 'block';
};

window.hideMapTooltip = function() {
  const tip = document.getElementById('mapTooltip');
  if (tip) tip.style.display = 'none';
};

window.filterMapByCity = function(city) {
  if (window.zoomToCity) {
    window.zoomToCity(city);
  }
};

/**
 * 渲染 TAB 2: 接驳规划
 */
function renderTransferPlanner() {
  const from = csTransferOriginInstance ? csTransferOriginInstance.getValue() : '杭州';
  const to = csTransferTargetInstance ? csTransferTargetInstance.getValue() : '阿勒泰';
  executeTransferPlanning(from, to);
}

function executeTransferPlanning(from, to) {
  const radiationArea = document.getElementById('radiationHubsArea');
  const resultsArea = document.getElementById('transferResultsArea');

  // 1. 渲染周边辐射枢纽
  const radiationHubs = getNearbyRadiationHubs(from);
  radiationArea.innerHTML = `
    <div style="background:#f8fafc; border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:16px 20px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <h4 style="font-size:0.95rem; font-weight:700; color:var(--accent-cyan); display:flex; align-items:center; gap:6px;">
          ${ICONS.train} ${from}周边高铁 1~2.5 小时大基地辐射圈
        </h4>
        <span style="font-size:0.75rem; color:var(--text-muted);">非枢纽城市也能畅飞全国</span>
      </div>
      <div style="display:flex; flex-wrap:wrap; gap:10px;">
        ${radiationHubs.map(h => `
          <div style="background:#ffffff; border:1px solid var(--border-subtle); border-radius:var(--radius-sm); padding:8px 14px; font-size:0.84rem; box-shadow:0 1px 3px rgba(15,23,42,0.04);">
            <div style="font-weight:700; color:var(--text-primary);">${h.city} <span style="font-size:0.74rem; color:var(--accent-cyan); font-weight:600;">(${h.relation})</span></div>
            <div style="color:var(--text-muted); font-size:0.76rem; margin-top:2px;">长龙直飞 ${h.directCount} 航点</div>
          </div>
        `).join('')}
      </div>
    </div>
  `;

  // 2. 计算出行方案
  const solutions = planMultiLegRoutes(from, to);

  // 收集本行程涉及的所有城市
  const relatedCities = Array.from(new Set([
    from, 
    to, 
    ...solutions.flatMap(s => s.steps.map(st => st.to)), 
    ...solutions.flatMap(s => s.steps.map(st => st.from))
  ])).filter(c => AIRPORT_GUIDES[c]);

  if (solutions.length === 0) {
    resultsArea.innerHTML = `
      <div style="text-align:center; padding:36px; color:var(--text-secondary); background:#ffffff; border-radius:var(--radius-md); border:1px solid var(--border-subtle);">
        暂未匹配到从 ${from} ➔ ${to} 的推荐联程方案，可尝试将中转站设为杭州超级基地。
      </div>
    `;
    return;
  }

  // 方案卡片列表渲染（内嵌机场交通特性微条）
  const solutionsHtml = solutions.map((sol, idx) => {
    const solAirports = [];
    sol.steps.forEach(st => {
      if (st.mode !== 'rail' && AIRPORT_GUIDES[st.from]) {
        solAirports.push({ city: st.from, guide: AIRPORT_GUIDES[st.from], role: '起飞出港' });
      }
      if (AIRPORT_GUIDES[st.to]) {
        solAirports.push({ city: st.to, guide: AIRPORT_GUIDES[st.to], role: st.to === to ? '目的地降落' : '中转枢纽' });
      }
    });
    const uniqueSolAirports = solAirports.filter((v, i, a) => a.findIndex(t => t.city === v.city) === i);

    let airportNotesHtml = '';
    if (uniqueSolAirports.length > 0) {
      airportNotesHtml = `
        <div class="transfer-card-airport-notes">
          <div class="tcan-header">
            <span>方案涉及机场交通与早班机特性:</span>
          </div>
          <div>
            ${uniqueSolAirports.map(item => {
              const g = item.guide;
              const transitBrief = g.transit && g.transit[0] ? `${g.transit[0].name} (${g.transit[0].detail})` : '';
              return `
                <div class="tcan-item">
                  <span class="tcan-city-tag">${item.city} · ${item.role}</span>
                  <div>
                    <strong>${g.airport}</strong> · 航站楼: ${g.terminal}
                    ${transitBrief ? `<div style="color:var(--accent-cyan); font-weight:600; font-size:0.76rem; margin-top:2px;">快捷接驳: ${transitBrief}</div>` : ''}
                    ${g.earlyFlightTip ? `<div style="color:var(--accent-amber); font-weight:600; font-size:0.76rem; margin-top:2px;">早班机避坑建议: ${g.earlyFlightTip}</div>` : ''}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    return `
      <div class="transfer-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:10px; margin-bottom:10px;">
          <div>
            <span class="tag-badge" style="margin-right:8px;">${sol.tag}</span>
            <strong style="font-size:1.05rem; color:var(--text-primary);">方案 ${idx + 1}: ${sol.title}</strong>
          </div>
          <div>
            <span style="font-size:0.84rem; color:var(--accent-emerald); font-weight:700;">预估耗时: ${sol.estimatedDuration}</span>
          </div>
        </div>

        <div class="transfer-steps-timeline">
          ${sol.steps.map((st, sIdx) => `
            <div class="timeline-step">
              <div class="step-type">
                ${st.mode === 'rail' ? ICONS.train : ICONS.plane}
                <span>${st.mode === 'rail' ? '高铁接驳' : (st.mode === 'self_flight' ? '自购特价前段' : '惠飞卡兑换')}</span>
              </div>
              <div class="step-route">${st.from} ➔ ${st.to}</div>
              <div class="step-meta">${st.carrier}</div>
              <div class="step-meta" style="color:var(--accent-cyan); margin-top:4px; font-weight:600;">${st.detail || (st.distance ? '航距 ' + st.distance + 'km' : '')}</div>
            </div>
            ${sIdx < sol.steps.length - 1 ? `<div class="timeline-arrow">${ICONS.arrowRight}</div>` : ''}
          `).join('')}
        </div>

        <!-- 方案内嵌机场交通特性 -->
        ${airportNotesHtml}

        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; font-size:0.84rem; color:var(--text-secondary); border-top:1px solid var(--border-subtle); padding-top:12px; margin-top:8px;">
          <span>综合费用预算: <strong style="color:var(--accent-cyan); font-weight:800; font-size:0.95rem;">${sol.costEstimate}</strong></span>
          <span style="font-size:0.78rem; color:var(--text-muted);">长龙畅飞卡可用航段优先</span>
        </div>
      </div>
    `;
  }).join('');

  // 3. 构建沿途机场小抄速查卡
  const relatedAirportsHtml = relatedCities.map(city => renderAirportCardHtml(city, AIRPORT_GUIDES[city])).join('');

  resultsArea.innerHTML = `
    <h4 style="font-size:1.05rem; font-weight:800; margin-bottom:14px; color:var(--text-primary);">为您规划了 ${solutions.length} 个出行方案:</h4>
    ${solutionsHtml}

    <!-- 方案下方直接整合展示机场小抄特性 -->
    <div style="margin-top: 32px; padding-top: 24px; border-top: 1.5px dashed var(--border-subtle);">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:12px;">
        <div>
          <h4 style="font-size:1.08rem; font-weight:800; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
            【${from} ➔ ${to}】行程关联机场小抄速览
          </h4>
          <p style="font-size:0.83rem; color:var(--text-secondary); margin-top:2px;">
            已自动锁定本行程涉及的机场：长龙航站楼、地铁/空铁接驳、打车预算及早班机避坑建议
          </p>
        </div>
        <button id="btnToggleAllAirports" type="button" class="btn-subtle" style="font-size:0.82rem; padding:6px 14px; border-radius:var(--radius-full); cursor:pointer; background:#ffffff; border:1px solid var(--border-subtle); font-weight:600; color:var(--accent-cyan);">
          查阅其他通航机场小抄 (48+座) ▾
        </button>
      </div>

      <!-- 本次行程涉及的机场卡片网格 -->
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:16px; margin-bottom:20px;">
        ${relatedAirportsHtml || '<p style="color:var(--text-muted); font-size:0.85rem;">本路线机场信息已在上方方案卡片中体现</p>'}
      </div>

      <!-- 可折叠展开的查阅全网 48+ 机场抽屉 -->
      <div id="drawerAllAirports" style="display:none; background:#f8fafc; border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:18px; margin-top:14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:14px;">
          <input type="text" id="drawerAirportSearchInput" class="custom-input" placeholder="输入城市、机场或三字码 (如: 银川 / HGH / 滑雪)..." style="max-width:320px; font-size:0.85rem;">
          <span id="drawerAirportCountBadge" style="font-size:0.8rem; color:var(--text-muted); font-weight:700;"></span>
        </div>
        <div id="drawerAirportsList" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:14px; max-height:480px; overflow-y:auto; padding-right:4px;"></div>
      </div>
    </div>
  `;

  // 绑定折叠按钮与抽屉内搜索事件
  initDrawerAirportEvents();
}

/**
 * 盲盒摇号
 */
function executeBlindboxRoll() {
  const origin = csBlindboxOriginInstance ? csBlindboxOriginInstance.getValue() : '杭州';
  const tag = csBlindboxTagInstance ? csBlindboxTagInstance.getValue() : '全部';
  const resultCard = document.getElementById('blindboxResult');

  const picked = rollRandomBlindbox(origin, tag);
  if (!picked) {
    resultCard.style.display = 'block';
    resultCard.innerHTML = `<p style="text-align:center; color:var(--text-secondary);">暂无匹配该主题的目的地，换个主题试试吧！</p>`;
    return;
  }

  resultCard.style.display = 'block';
  resultCard.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
      <span class="tag-badge">天命盲盒抽取结果</span>
      <span style="font-size:0.82rem; color:var(--accent-cyan); font-weight:700;">${picked.mode}</span>
    </div>
    <div style="display:flex; align-items:baseline; gap:12px; margin-bottom:8px;">
      <h3 style="font-size:1.8rem; font-weight:800; color:var(--text-primary);">${picked.destination}</h3>
      <span style="color:var(--text-muted); font-size:0.88rem;">${picked.airport}</span>
    </div>
    <p style="color:var(--text-secondary); font-size:0.9rem; margin-bottom:14px; line-height:1.5;">${picked.reason}</p>
    <div class="tag-list" style="margin-bottom:16px;">
      ${picked.tags.map(t => `<span class="mini-tag">${t}</span>`).join('')}
    </div>
    <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border-subtle); padding-top:14px; flex-wrap:wrap; gap:8px;">
      <span style="font-size:0.82rem; color:var(--text-muted);">从 <strong>${picked.from}</strong> 出发</span>
      <div style="display:flex; gap:8px;">
        <button class="btn-primary" style="padding:6px 14px; font-size:0.82rem;" onclick="window.selectForTransfer('${picked.from}', '${picked.destination}')">
          查看接驳与航线 ${ICONS.arrowRight}
        </button>
      </div>
    </div>
  `;
}

/**
 * 渲染 TAB 4: 季节指南
 */
function renderSeasonalGuide() {
  const container = document.getElementById('seasonCardsContainer');
  container.innerHTML = SEASONAL_GUIDE.map(season => `
    <div style="background:#ffffff; border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:20px; box-shadow:var(--shadow-subtle);">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:8px;">
        <div style="display:flex; align-items:center; gap:12px;">
          <h4 style="font-size:1.15rem; font-weight:800; color:var(--text-primary);">${season.name}</h4>
          <span class="tag-badge" style="background:var(--accent-emerald-light); color:var(--accent-emerald);">${season.tag}</span>
        </div>
        <span style="font-size:0.84rem; color:var(--accent-cyan); font-weight:700;">有效日期: ${season.dateRange}</span>
      </div>
      <p style="font-size:0.86rem; color:var(--text-secondary); margin-bottom:16px;">${season.description}</p>
      
      <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(240px, 1fr)); gap:12px;">
        ${season.destinations.map(d => `
          <div style="background:#f8fafc; border:1px solid var(--border-subtle); border-radius:var(--radius-sm); padding:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <strong style="font-size:0.95rem; color:var(--text-primary);">${d.city}</strong>
              <span style="font-size:0.72rem; color:var(--accent-amber); font-weight:700;">${d.highlight}</span>
            </div>
            <div style="font-size:0.78rem; color:var(--text-secondary); line-height:1.4;">${d.reason}</div>
          </div>
        `).join('')}
      </div>
    </div>
  `).join('');
}

/**
 * 渲染 TAB 5: 算账器
 */
function renderCalculator() {
  const flightCount = Number(document.getElementById('calcFlightCount').value) || 6;
  const marketPrice = Number(document.getElementById('calcMarketPrice').value) || 850;

  const result = simulateTripEconomy(flightCount, marketPrice, true);

  const summaryEl = document.getElementById('calcSummaryCard');
  summaryEl.innerHTML = `
    <div>
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <span class="tag-badge" style="background:var(--accent-emerald-light); color:var(--accent-emerald);">花费统计总览</span>
        <span style="font-size:0.82rem; color:var(--accent-cyan); font-weight:700;">计划乘机: ${result.plannedFlights} 次单程</span>
      </div>
      <div style="font-size:2rem; font-weight:800; color:var(--accent-emerald); margin-bottom:2px;">
        累计节省 ¥${result.savedMoney.toLocaleString()}
      </div>
      <div style="font-size:0.86rem; color:var(--text-secondary); margin-bottom:16px;">
        相比散客商旅票节省效益: <strong style="color:var(--accent-cyan);">+${result.roi}%</strong>
      </div>
    </div>

    <div style="border-top:1px solid var(--border-subtle); padding-top:14px; font-size:0.85rem; display:flex; flex-direction:column; gap:6px;">
      <div style="display:flex; justify-content:space-between;">
        <span style="color:var(--text-secondary);">惠飞卡固定卡费:</span>
        <span style="font-weight:600;">¥${result.cardCost}</span>
      </div>
      <div style="display:flex; justify-content:space-between;">
        <span style="color:var(--text-secondary);">累计兑换票价+税费:</span>
        <span style="font-weight:600;">¥${result.totalFlightCost.toLocaleString()}</span>
      </div>
      <div style="display:flex; justify-content:space-between;">
        <span style="color:var(--text-secondary);">总实际支出 (卡+票+税):</span>
        <strong style="color:var(--text-primary);">¥${result.grandTotal.toLocaleString()}</strong>
      </div>
      <div style="display:flex; justify-content:space-between;">
        <span style="color:var(--text-secondary);">折合每次单程全包均价:</span>
        <strong style="color:var(--accent-cyan);">约 ¥${result.avgCostPerFlight} / 次</strong>
      </div>
      <div style="display:flex; justify-content:space-between;">
        <span style="color:var(--text-secondary);">不买卡商业票总价:</span>
        <span style="text-decoration:line-through; color:var(--text-dim);">¥${result.marketTotal.toLocaleString()}</span>
      </div>
    </div>
  `;

  const tableEl = document.getElementById('calcBreakdownTable');
  tableEl.innerHTML = `
    <table style="width:100%; border-collapse:collapse; font-size:0.84rem; text-align:left;">
      <thead>
        <tr style="border-bottom:1px solid var(--border-subtle); color:var(--text-muted); background:#f8fafc;">
          <th style="padding:10px 14px;">次序</th>
          <th style="padding:10px 14px;">阶梯兑换承运价</th>
          <th style="padding:10px 14px;">动态税费 (机建+燃油)</th>
          <th style="padding:10px 14px;">单次全包花费</th>
          <th style="padding:10px 14px;">阶梯权益状态</th>
        </tr>
      </thead>
      <tbody>
        ${result.breakdown.map(item => `
          <tr style="border-bottom:1px solid var(--border-subtle);">
            <td style="padding:10px 14px; font-weight:700;">第 ${item.flightIndex} 次</td>
            <td style="padding:10px 14px; color:var(--accent-cyan); font-weight:600;">¥${item.redeemBase}</td>
            <td style="padding:10px 14px; color:var(--text-secondary);">¥${item.tax}</td>
            <td style="padding:10px 14px; font-weight:800; color:var(--text-primary);">¥${item.singleTotal}</td>
            <td style="padding:10px 14px;">
              ${item.tierUnlocked ? `<span class="tag-badge" style="background:var(--accent-amber-light); color:var(--accent-amber);">${item.tierUnlocked}</span>` : '<span style="color:var(--text-dim);">-</span>'}
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

/**
 * 渲染通用机场小抄卡片 HTML
 */
function renderAirportCardHtml(city, guide) {
  if (!guide) return '';
  return `
    <div class="airport-card">
      <div class="airport-card-header">
        <div>
          <span class="airport-city-title">${city}</span>
          <span class="airport-code-tag">${guide.code || ''}</span>
          <div style="font-size:0.82rem; color:var(--text-muted); margin-top:2px;">${guide.airport}</div>
        </div>
        <span class="airport-commute-score" title="航旅通勤综合便利评级">${guide.score || '9.0分'}</span>
      </div>

      <div class="airport-terminal-info">
        <strong>航站楼分布:</strong> ${guide.terminal}
      </div>
      
      <div class="airport-transit-list">
        ${(guide.transit || []).map(t => `
          <div>
            <strong style="color:var(--accent-cyan); font-weight:700;">• ${t.name}:</strong> ${t.detail}
          </div>
        `).join('')}
      </div>

      ${guide.earlyFlightTip ? `
        <div class="airport-early-tip">
          <strong>早班机避坑小贴士:</strong> ${guide.earlyFlightTip}
        </div>
      ` : ''}
    </div>
  `;
}

/**
 * 接驳规划内嵌：全网机场抽屉折叠与搜索过滤事件
 */
function initDrawerAirportEvents() {
  const btnToggle = document.getElementById('btnToggleAllAirports');
  const drawer = document.getElementById('drawerAllAirports');
  const searchInput = document.getElementById('drawerAirportSearchInput');
  const listContainer = document.getElementById('drawerAirportsList');
  const countBadge = document.getElementById('drawerAirportCountBadge');

  if (!btnToggle || !drawer) return;

  const renderDrawerList = (kw = '') => {
    if (!listContainer) return;
    const term = kw.trim().toLowerCase();
    const entries = Object.entries(AIRPORT_GUIDES);
    const filtered = entries.filter(([city, guide]) => {
      if (!term) return true;
      return (
        city.toLowerCase().includes(term) ||
        guide.airport.toLowerCase().includes(term) ||
        (guide.code || '').toLowerCase().includes(term) ||
        (guide.terminal || '').toLowerCase().includes(term) ||
        (guide.earlyFlightTip || '').toLowerCase().includes(term) ||
        guide.transit.some(t => t.name.toLowerCase().includes(term) || t.detail.toLowerCase().includes(term))
      );
    });

    if (countBadge) {
      countBadge.textContent = `展示 ${filtered.length} / 共收录 ${entries.length} 座机场`;
    }

    if (filtered.length === 0) {
      listContainer.innerHTML = `<div style="grid-column: 1 / -1; text-align:center; padding:24px; color:var(--text-muted); font-size:0.86rem;">未找到相关机场，请尝试其他城市名或三字码</div>`;
      return;
    }

    listContainer.innerHTML = filtered.map(([city, guide]) => renderAirportCardHtml(city, guide)).join('');
  };

  btnToggle.addEventListener('click', () => {
    const isHidden = drawer.style.display === 'none';
    drawer.style.display = isHidden ? 'block' : 'none';
    btnToggle.innerHTML = isHidden 
      ? '收起其他通航机场 ▴' 
      : '查阅其他通航机场小抄 (48+座) ▾';
    if (isHidden) {
      renderDrawerList(searchInput ? searchInput.value : '');
    }
  });

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      renderDrawerList(e.target.value);
    });
  }
}

/**
 * 展开/收起剩余可兑换日期
 */
window.toggleMoreDates = function(idx, btn) {
  const moreWrapper = document.getElementById(`more-dates-${idx}`);
  if (!moreWrapper) return;
  const isHidden = moreWrapper.style.display === 'none' || moreWrapper.style.display === '';
  if (isHidden) {
    moreWrapper.style.display = 'contents';
    if (btn) {
      if (!btn.dataset.origText) btn.dataset.origText = btn.textContent;
      btn.textContent = '收起 ▴';
    }
  } else {
    moreWrapper.style.display = 'none';
    if (btn && btn.dataset.origText) {
      btn.textContent = btn.dataset.origText;
    }
  }
};

/**
 * 即时向官方查验指定航线与具体日期的各航班真实剩余张数 (secCardLeft)
 */
window.checkLiveSeatCount = async function(fromCity, toCity, flightDate) {
  const eventTarget = window.event?.currentTarget;
  const originalHtml = eventTarget ? eventTarget.innerHTML : '';
  if (eventTarget) {
    eventTarget.style.opacity = '0.7';
    eventTarget.innerHTML = `查票中...`;
  }

  showToast(`正在向长龙官方查询【${fromCity} ➔ ${toCity} (${flightDate})】各班次实时余票...`);
  try {
    const res = await queryLiveFlights(fromCity, toCity, flightDate);
    if (res.ok && res.flights && res.flights.length > 0) {
      let totalSecCardLeft = 0;
      const flightDetails = res.flights.map(f => {
        const leftCount = Number(f.secCardLeft) || 0;
        totalSecCardLeft += leftCount;
        const leftBadge = leftCount > 0 
          ? `<span style="background:#ecfdf5; color:#047857; border:1px solid #a7f3d0; padding:2px 10px; border-radius:12px; font-weight:800; font-size:0.82rem;">畅飞卡余票: ${leftCount} 张</span>`
          : `<span style="background:#f1f5f9; color:#94a3b8; border:1px solid #e2e8f0; padding:2px 8px; border-radius:12px; font-weight:600; font-size:0.8rem;">已兑完</span>`;
        return `
          <div style="background:#f8fafc; border:1px solid var(--border-subtle); border-radius:10px; padding:14px 16px; margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <strong style="font-size:1.15rem; color:var(--accent-cyan); font-weight:800;">${f.flightNo}</strong>
              ${leftBadge}
            </div>
            <div style="font-size:0.9rem; color:var(--text-primary); margin-bottom:6px; font-weight:600;">
              计划起降: <strong style="color:var(--text-primary); font-size:1.02rem;">${f.depTime}</strong> ➔ <strong style="color:var(--text-primary); font-size:1.02rem;">${f.arrTime}</strong> · 机型: ${f.aircraft || 'A320'}
            </div>
            <div style="font-size:0.8rem; color:var(--text-secondary); display:flex; justify-content:space-between; padding-top:6px; border-top:1px dashed #e2e8f0;">
              <span>阶梯基础承运价: <strong style="color:var(--accent-rose); font-size:0.95rem;">¥${f.redeemPrice}</strong></span>
              <span>普通全价舱位剩余: ${f.normalLeft ?? '--'} 张</span>
            </div>
          </div>
        `;
      }).join('');

      // 记录查询时间戳（几月几日 几点几分）
      const now = new Date();
      const month = now.getMonth() + 1;
      const day = now.getDate();
      const hour = String(now.getHours()).padStart(2, '0');
      const min = String(now.getMinutes()).padStart(2, '0');
      const timeFormatted = `${month}月${day}日 ${hour}:${min}`;

      const cacheKey = `${fromCity}-${toCity}-${flightDate}`;
      const timestamp = now.getTime();
      window.LIVE_QUERY_CACHE = window.LIVE_QUERY_CACHE || {};
      window.LIVE_QUERY_CACHE[cacheKey] = {
        count: totalSecCardLeft,
        timeFormatted: timeFormatted,
        timestamp: timestamp
      };
      setSeatQueryCache(window.LIVE_QUERY_CACHE);

      const timeLabel = `${hour}:${min}查`;
      const badgeHtml = totalSecCardLeft > 0 
        ? `<span class="pill-check-tag pill-tag-success">余${totalSecCardLeft} · ${timeLabel}</span>`
        : `<span class="pill-check-tag pill-tag-empty">兑完 · ${timeLabel}</span>`;
      const newTitle = `查询时间：${timeFormatted} · 畅飞卡余 ${totalSecCardLeft} 张 (点击可重新查验)`;

      // 联动更新页面上所有显示该日期的胶囊按钮（列表卡片与地图抽屉完美实时双向同步）
      const matchingPills = document.querySelectorAll(`[data-check-key="${cacheKey}"]`);
      if (matchingPills && matchingPills.length > 0) {
        matchingPills.forEach(pill => {
          pill.style.opacity = '1';
          pill.classList.add('is-checked');
          const baseText = pill.getAttribute('data-base-text') || pill.textContent.replace(/(余\d+|已兑完|兑完|查票中\.\.\.|·|\d{1,2}:\d{2}查|\d{1,2}-\d{1,2}查)/g, '').trim();
          pill.innerHTML = `<span class="pill-date-txt">${baseText}</span>${badgeHtml}`;
          pill.title = newTitle;
        });
      } else if (eventTarget) {
        eventTarget.style.opacity = '1';
        eventTarget.classList.add('is-checked');
        const baseText = eventTarget.getAttribute('data-base-text') || eventTarget.textContent.replace(/(余\d+|已兑完|兑完|查票中\.\.\.|·|\d{1,2}:\d{2}查|\d{1,2}-\d{1,2}查)/g, '').trim();
        eventTarget.innerHTML = `<span class="pill-date-txt">${baseText}</span>${badgeHtml}`;
        eventTarget.title = newTitle;
      }

      // 如果抽屉正打开，联动更新抽屉顶部的查验统计
      const summaryEl = document.getElementById('drawerCheckSummary');
      if (summaryEl) {
        summaryEl.style.display = 'inline-flex';
        summaryEl.className = 'drawer-checked-summary';
        summaryEl.textContent = `最新查验 · ${timeLabel}`;
      }

      showSeatDetailModal(fromCity, toCity, flightDate, `
        <div style="margin-bottom:12px; font-size:0.85rem; color:var(--text-secondary); display:flex; justify-content:space-between; align-items:center;">
          <span>官方实时席位：共 <strong>${res.flights.length}</strong> 班直飞，畅飞卡累计余 <strong>${totalSecCardLeft}</strong> 张</span>
          <span style="font-size:0.75rem; color:var(--text-muted);">查询时间: ${timeFormatted}</span>
        </div>
        ${flightDetails}
      `);
    } else {
      if (eventTarget) {
        eventTarget.style.opacity = '1';
        eventTarget.innerHTML = originalHtml;
      }
      showSeatDetailModal(fromCity, toCity, flightDate, `
        <div style="text-align:center; padding:28px 16px; color:var(--text-secondary);">
          <p style="font-weight:700; color:var(--text-primary); margin-bottom:6px; font-size:1.05rem;">该日期官方大盘显示为有效放票日</p>
          <p style="font-size:0.86rem; line-height:1.6; max-width:360px; margin:0 auto;">但当前批次免费机位可能已被抢兑完毕，或当日航班排班微调。建议留意次日放票或选择临近日期！</p>
        </div>
      `);
    }
  } catch (err) {
    if (eventTarget) {
      eventTarget.style.opacity = '1';
      eventTarget.innerHTML = originalHtml;
    }
    showSeatDetailModal(fromCity, toCity, flightDate, `
      <div style="padding:16px; color:var(--text-secondary); line-height:1.6;">
        <p><strong>大盘已确认 ${flightDate} 为长龙畅飞卡有效可兑换日</strong>（非节假日黑飞禁兑期）。</p>
        <p style="margin-top:8px; font-size:0.84rem;">后台接口正在响应中，请稍候再试，或直接打开手机飞猪/长龙 App 预约出票！</p>
      </div>
    `);
  }
};

function showSeatDetailModal(from, to, date, contentHtml) {
  let modal = document.getElementById('modalSeatDetail');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'modalSeatDetail';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }
  modal.innerHTML = `
    <div class="modal-content" style="max-width: 500px; padding:22px 24px;">
      <div class="modal-header" style="margin-bottom:14px; border-bottom:1px solid var(--border-subtle); padding-bottom:10px;">
        <h3 style="font-size:1.1rem; font-weight:800; color:var(--text-primary); margin:0;">
          ${from} ➔ ${to} · ${date} 官方余票
        </h3>
        <button class="btn-close" onclick="document.getElementById('modalSeatDetail').style.display='none'">&times;</button>
      </div>
      <div style="max-height:65vh; overflow-y:auto; padding-right:2px;">
        ${contentHtml}
      </div>
      <div style="padding-top:14px; border-top:1px solid var(--border-subtle); display:flex; justify-content:flex-end; gap:10px; margin-top:8px;">
        <button class="btn-primary" style="padding:8px 20px;" onclick="document.getElementById('modalSeatDetail').style.display='none'">我知道了</button>
      </div>
    </div>
  `;
  modal.style.display = 'flex';
  modal.onclick = (e) => {
    if (e.target === modal) modal.style.display = 'none';
  };
}
