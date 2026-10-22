/**
 * 航线规划核心引擎
 * 包含：直飞与双向闭环、自购/高铁接驳中转规划、周边辐射聚合、盲盒随机出行算法
 */
import { CITY_METADATA, HIGH_SPEED_RAIL_CONNECTIONS } from './routes-data.js';
import { DIRECT_MAP, REVERSE_MAP, ROUTES_NETWORK } from './routes-network.js';
import { calculateTaxes } from './cost-calculator.js';

/**
 * 查询指定出发城市的直飞航线与往返闭环状态
 */
export function queryDirectRoutes(originCity) {
  if (!originCity || !DIRECT_MAP[originCity]) {
    return { directList: [], totalCount: 0, roundTripCount: 0 };
  }

  const destinations = DIRECT_MAP[originCity];
  const list = destinations.map(dest => {
    const routeInfo = ROUTES_NETWORK.find(r => r.from === originCity && r.to === dest) || {};
    // 检查是否有返程直飞 dest -> originCity
    const hasReturn = (DIRECT_MAP[dest] || []).includes(originCity);
    const destMeta = CITY_METADATA[dest] || { tags: [], region: '未知' };
    const tax = calculateTaxes(routeInfo.distance || 1000);

    return {
      to: dest,
      distance: routeInfo.distance || 0,
      isOver800Km: Boolean(routeInfo.isOver800Km),
      seasonStatus: routeInfo.seasonStatus || '正常执飞',
      hasReturn,
      tags: destMeta.tags || [],
      region: destMeta.region || '',
      airport: destMeta.airport || '',
      tax: tax.totalTax
    };
  });

  // 排序：双向往返优先，其次距离
  list.sort((a, b) => {
    if (a.hasReturn !== b.hasReturn) return a.hasReturn ? -1 : 1;
    return b.distance - a.distance;
  });

  return {
    origin: originCity,
    directList: list,
    totalCount: list.length,
    roundTripCount: list.filter(item => item.hasReturn).length
  };
}

/**
 * 智能中转/接驳规划器（突破非基地城市航线限制）
 * 如：太原 -> 阿勒泰
 * 方案 1: 高铁到郑州/西安/北京 + 郑州/西安飞阿勒泰
 * 方案 2: 太原自购机票飞杭州大枢纽 + 杭州飞阿勒泰
 */
export function planMultiLegRoutes(originCity, targetCity) {
  const solutions = [];

  // 1. 如果已有直飞
  const directDestinations = DIRECT_MAP[originCity] || [];
  if (directDestinations.includes(targetCity)) {
    const route = ROUTES_NETWORK.find(r => r.from === originCity && r.to === targetCity);
    solutions.push({
      type: 'direct',
      title: `长龙直飞 ${originCity} ➔ ${targetCity}`,
      steps: [
        {
          mode: 'flight',
          carrier: '长龙航空（惠飞卡可兑）',
          from: originCity,
          to: targetCity,
          distance: route?.distance || 0,
          seasonStatus: route?.seasonStatus || '正常执飞'
        }
      ],
      estimatedDuration: '2h - 4.5h',
      costEstimate: '惠飞卡兑换价(¥99~266) + 机建燃油',
      tag: '直飞最便捷'
    });
  }

  // 2. 检查高铁直达周边的长龙强枢纽 (如太原 -> 郑州/西安/北京)
  const railHubs = HIGH_SPEED_RAIL_CONNECTIONS[originCity] || [];
  railHubs.forEach(hubInfo => {
    const hubCity = hubInfo.target;
    const hubDests = DIRECT_MAP[hubCity] || [];
    if (hubDests.includes(targetCity)) {
      const flightRoute = ROUTES_NETWORK.find(r => r.from === hubCity && r.to === targetCity);
      solutions.push({
        type: 'rail_flight',
        title: `高铁接驳: ${originCity} -(高铁)-➔ ${hubCity} -(长龙)-➔ ${targetCity}`,
        steps: [
          {
            mode: 'rail',
            carrier: '中国高铁',
            from: originCity,
            to: hubCity,
            duration: hubInfo.duration,
            price: hubInfo.priceRange,
            detail: hubInfo.advantage
          },
          {
            mode: 'flight',
            carrier: '长龙航空（惠飞卡兑换）',
            from: hubCity,
            to: targetCity,
            distance: flightRoute?.distance || 0,
            seasonStatus: flightRoute?.seasonStatus || '正常执飞'
          }
        ],
        estimatedDuration: `高铁 ${hubInfo.duration} + 飞行 ${Math.round((flightRoute?.distance || 1500) / 750)}h`,
        costEstimate: `高铁约 ${hubInfo.priceRange} + 惠飞卡兑换价(¥99~266) + 机建燃油`,
        tag: `推荐方案 · ${hubCity}枢纽转`
      });
    }
  });

  // 3. 检查自购前段低成本机票飞往三大超级大本营（杭州、银川、长春）中转
  const majorSuperHubs = ['杭州', '银川', '长春', '成都', '广州'];
  majorSuperHubs.forEach(superHub => {
    if (superHub === originCity) return;
    const superDests = DIRECT_MAP[superHub] || [];
    if (superDests.includes(targetCity)) {
      // 避免与高铁方案重复
      if (solutions.some(s => s.steps.some(st => st.to === superHub))) return;

      const flightRoute = ROUTES_NETWORK.find(r => r.from === superHub && r.to === targetCity);
      solutions.push({
        type: 'air_transfer',
        title: `空空联程: ${originCity} -(自购机票/特价)-➔ ${superHub} -(长龙)-➔ ${targetCity}`,
        steps: [
          {
            mode: 'self_flight',
            carrier: '自购商业特价客票 / 任意航司',
            from: originCity,
            to: superHub,
            estimatedPrice: '特价约 ¥200 - ¥400',
            detail: `飞往长龙核心基地 ${superHub}，无缝衔接`
          },
          {
            mode: 'flight',
            carrier: '长龙航空（惠飞卡兑换）',
            from: superHub,
            to: targetCity,
            distance: flightRoute?.distance || 0,
            seasonStatus: flightRoute?.seasonStatus || '正常执飞'
          }
        ],
        estimatedDuration: '半日中转 / 适合长线大旅行',
        costEstimate: `前段自购约¥200~400 + 惠飞卡后段兑换 + 税费`,
        tag: `${superHub}大本营中转`
      });
    }
  });

  return solutions;
}

/**
 * 就近辐射出发方案（如太原出发，聚合太原自身 + 郑州/西安/石家庄的高铁圈长龙可用航线）
 */
export function getNearbyRadiationHubs(originCity) {
  const localDirect = DIRECT_MAP[originCity] || [];
  const railHubs = HIGH_SPEED_RAIL_CONNECTIONS[originCity] || [];

  const radiationList = [
    {
      city: originCity,
      relation: '本场出发',
      timeCost: '0h',
      directCount: localDirect.length,
      destinations: localDirect
    }
  ];

  railHubs.forEach(hub => {
    const hubDirect = DIRECT_MAP[hub.target] || [];
    radiationList.push({
      city: hub.target,
      hub: hub.target,
      relation: `高铁 ${hub.duration} (${hub.priceRange})`,
      timeCost: hub.duration,
      duration: hub.duration,
      priceRange: hub.priceRange,
      directCount: hubDirect.length,
      destinations: hubDirect,
      advantage: hub.advantage
    });
  });

  return radiationList;
}

/**
 * 盲盒随机出行（随便去哪摇号）
 * @param {string} originCity 出发城市
 * @param {string} preferredTag 偏好标签（可选：全部/滑雪/避寒/草原/美食等）
 */
export function rollRandomBlindbox(originCity = '杭州', preferredTag = '全部') {
  let candidateCities = [];

  // 获取该城市直飞或其周边辐射能到达的所有目的地
  const directList = DIRECT_MAP[originCity] || [];
  candidateCities.push(...directList.map(dest => ({ city: dest, from: originCity, mode: '直飞' })));

  // 如果直飞较少（如太原只有4个），自动扩充周边高铁大枢纽的辐射航点
  if (directList.length < 10 && HIGH_SPEED_RAIL_CONNECTIONS[originCity]) {
    HIGH_SPEED_RAIL_CONNECTIONS[originCity].slice(0, 2).forEach(hub => {
      const hubDests = DIRECT_MAP[hub.target] || [];
      hubDests.forEach(dest => {
        if (!candidateCities.some(c => c.city === dest)) {
          candidateCities.push({
            city: dest,
            from: originCity,
            viaHub: hub.target,
            mode: `高铁经${hub.target}`
          });
        }
      });
    });
  }

  // 标签过滤
  if (preferredTag && preferredTag !== '全部') {
    candidateCities = candidateCities.filter(item => {
      const meta = CITY_METADATA[item.city];
      return meta && meta.tags && meta.tags.some(t => t.includes(preferredTag));
    });
  }

  if (candidateCities.length === 0) {
    return null;
  }

  // 随机挑选一个
  const picked = candidateCities[Math.floor(Math.random() * candidateCities.length)];
  const meta = CITY_METADATA[picked.city] || { tags: ['探索未知'], airport: '本场机场' };

  return {
    destination: picked.city,
    from: picked.from,
    mode: picked.mode,
    viaHub: picked.viaHub || null,
    meta,
    tags: meta.tags || [],
    airport: meta.airport,
    reason: `长龙精选航线，畅游${meta.province || ''}${picked.city}！`
  };
}
