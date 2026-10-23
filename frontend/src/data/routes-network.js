import { FLIGHTS_SCHEDULE } from './flights-schedule.js';
import { CITY_METADATA } from './city-meta.js';

function calculateDistance(lon1, lat1, lon2, lat2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c);
}

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
      isOver800Km: distance >= 800
    });
  }
});

export const ROUTES_NETWORK = routeList;
export const DIRECT_MAP = directMap;
export const REVERSE_MAP = reverseMap;
