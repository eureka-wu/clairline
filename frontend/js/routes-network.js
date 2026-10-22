/**
 * 长龙航空全量航网拓扑与直飞关系字典
 * 自动从 FLIGHTS_SCHEDULE（由 flight-routes.json 驱动）动态派生
 * 杜绝静态冗余，保证排班数据与航网拓扑 100% 实时同步
 */
import { FLIGHTS_SCHEDULE } from './flights-schedule.js';
import { CITY_METADATA } from './routes-data.js';

// 计算两城市间的大圆球面距离 (Haversine Formula)
function calculateDistance(lon1, lat1, lon2, lat2) {
  const R = 6371; // 地球平均半径 (km)
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c);
}

// 季节性与重点航线标签
const SEASONAL_FLAGS = {
  '太原-深圳': '待换季复核/夏秋执飞多',
  '深圳-太原': '待换季复核/夏秋执飞多',
  '通化-烟台': '季节性执飞',
  '烟台-通化': '季节性执飞',
  '大连-常州': '冬春季班期微调',
  '哈尔滨-三亚': '冬季大热门/冬春加密',
  '杭州-阿勒泰': '滑雪季与夏秋草原重点'
};

const routeList = [];
const directMap = {};
const reverseMap = {};
const seenRoutes = new Set();

FLIGHTS_SCHEDULE.forEach(f => {
  const key = `${f.from}-${f.to}`;
  if (!seenRoutes.has(key)) {
    seenRoutes.add(key);

    if (!directMap[f.from]) directMap[f.from] = [];
    directMap[f.from].push(f.to);

    if (!reverseMap[f.to]) reverseMap[f.to] = [];
    reverseMap[f.to].push(f.from);

    const metaFrom = CITY_METADATA[f.from];
    const metaTo = CITY_METADATA[f.to];
    let distance = 0;
    if (metaFrom?.coords && metaTo?.coords) {
      distance = calculateDistance(metaFrom.coords[0], metaFrom.coords[1], metaTo.coords[0], metaTo.coords[1]);
    }

    routeList.push({
      from: f.from,
      to: f.to,
      distance,
      isOver800Km: distance >= 800,
      seasonStatus: SEASONAL_FLAGS[key] || '常态班期/以实际放票为准'
    });
  }
});

// 导出与原有接口 100% 兼容的三个核心航网对象
export const ROUTES_NETWORK = routeList;
export const DIRECT_MAP = directMap;
export const REVERSE_MAP = reverseMap;
