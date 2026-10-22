/**
 * 机建燃油动态配置中心 & 畅飞卡阶梯计费与花费统计引擎
 */

// 默认国内机建燃油配置（截至2026年10月15日最新民航执行标准：10月10日起上调）
export const DEFAULT_FEE_CONFIG = {
  airportBuildFee: 50,      // 民航发展基金(机建)，成人 50 元
  fuel800Below: 50,         // 800公里及以下燃油附加费：50元
  fuel800Above: 90          // 800公里以上燃油附加费：90元
};

const STORAGE_KEY = 'changlong_fee_config_v202610';

/**
 * 获取当前全局机建燃油配置（持久化至 LocalStorage）
 */
export function getFeeConfig() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      return { ...DEFAULT_FEE_CONFIG, ...JSON.parse(saved) };
    }
  } catch (e) {
    console.warn('读取本地燃油配置失败，使用默认值', e);
  }
  return { ...DEFAULT_FEE_CONFIG };
}

/**
 * 更新保存全局机建燃油配置
 */
export function saveFeeConfig(config) {
  try {
    const nextConfig = {
      airportBuildFee: Number(config.airportBuildFee) || 0,
      fuel800Below: Number(config.fuel800Below) || 0,
      fuel800Above: Number(config.fuel800Above) || 0
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextConfig));
    return nextConfig;
  } catch (e) {
    console.error('保存机建燃油配置失败', e);
    return getFeeConfig();
  }
}

/**
 * 根据航距计算单程税费（机建 + 燃油）
 */
export function calculateTaxes(distance = 1000) {
  const config = getFeeConfig();
  const fuel = distance >= 800 ? config.fuel800Above : config.fuel800Below;
  return {
    airportBuildFee: config.airportBuildFee,
    buildFee: config.airportBuildFee,
    fuelFee: fuel,
    totalTax: config.airportBuildFee + fuel
  };
}

/**
 * 畅飞卡阶梯兑换价规则（惠飞版）
 * 1-4 次: ¥266
 * 5-10 次: ¥199
 * 11-20 次: ¥129
 * 21+ 次: ¥99
 */
export function getRedeemPriceByTimes(completedFlightsCount) {
  if (completedFlightsCount < 4) return 266;
  if (completedFlightsCount < 10) return 199;
  if (completedFlightsCount < 20) return 129;
  return 99;
}

/**
 * 综合算账模拟器
 * @param {number} plannedFlights 计划飞行的总单程次数
 * @param {number} avgMarketPrice 预估平均单程市场售价（如 800 元）
 * @param {boolean} isLongDistance 是否大部分为长途（>=800km）
 */
export function simulateTripEconomy(plannedFlights = 6, avgMarketPrice = 850, isLongDistance = true) {
  const cardCost = 499; // 惠飞版
  let totalFlightCost = 0;
  const breakdown = [];
  const config = getFeeConfig();
  const singleTax = config.airportBuildFee + (isLongDistance ? config.fuel800Above : config.fuel800Below);

  for (let i = 0; i < plannedFlights; i++) {
    const redeemBase = getRedeemPriceByTimes(i);
    const flightTotal = redeemBase + singleTax;
    totalFlightCost += flightTotal;
    breakdown.push({
      flightIndex: i + 1,
      redeemBase,
      tax: singleTax,
      singleTotal: flightTotal,
      tierUnlocked: i === 4 ? '解锁199' : (i === 10 ? '解锁129' : (i === 20 ? '解锁99' : ''))
    });
  }

  const grandTotal = cardCost + totalFlightCost;
  const avgCostPerFlight = plannedFlights > 0 ? Math.round(grandTotal / plannedFlights) : 0;
  const marketTotal = plannedFlights * avgMarketPrice;
  const savedMoney = marketTotal - grandTotal;
  const roi = cardCost > 0 ? ((savedMoney / cardCost) * 100).toFixed(0) : 0;

  return {
    cardCost,
    plannedFlights,
    totalFlightCost,
    singleTax,
    grandTotal,
    avgCostPerFlight,
    marketTotal,
    savedMoney,
    roi,
    breakdown
  };
}
