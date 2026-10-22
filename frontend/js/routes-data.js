/**
 * 长龙航空 71 城市与航网核心数据库
 * 包含：经纬度、区域、机场名称/代码、季节性标签、冬春/夏秋季执飞状态标注
 */
export const CITY_METADATA = {
  "杭州": { code: "HGH", airport: "萧山国际机场", province: "浙江", region: "华东", coords: [120.43, 30.23], hub: "tier1", tags: ["总部基地", "江南水乡", "四季皆宜", "美食"] },
  "银川": { code: "INC", airport: "河东国际机场", province: "宁夏", region: "西北", coords: [106.39, 38.32], hub: "tier1", tags: ["西北枢纽", "大漠风光", "枸杞之乡", "中转要地"] },
  "长春": { code: "CGQ", airport: "龙嘉国际机场", province: "吉林", region: "东北", coords: [125.68, 43.99], hub: "tier1", tags: ["东北枢纽", "冰雪天地", "长白山前哨", "滑雪"] },
  "宁波": { code: "NGB", airport: "栎社国际机场", province: "浙江", region: "华东", coords: [121.46, 29.82], hub: "tier2", tags: ["沿海基地", "海鲜之都", "江南古镇"] },
  "哈尔滨": { code: "HRB", airport: "太平国际机场", province: "黑龙江", region: "东北", coords: [126.25, 45.62], hub: "tier2", tags: ["冰雪大世界", "滑雪胜地", "俄式风情", "冬季极佳"] },
  "温州": { code: "WNZ", airport: "龙湾国际机场", province: "浙江", region: "华东", coords: [120.85, 27.91], hub: "tier2", tags: ["沿海重点", "雁荡奇秀", "经商名城"] },
  "广州": { code: "CAN", airport: "白云国际机场", province: "广东", region: "华南", coords: [113.30, 23.39], hub: "tier2", tags: ["大湾区门户", "粤菜之巅", "四季温暖"] },
  "成都": { code: "TFU", airport: "天府国际机场", province: "四川", region: "西南", coords: [104.44, 30.32], hub: "tier2", tags: ["天府之国", "大熊猫", "川味美食", "进川入藏"] },
  "武汉": { code: "WUH", airport: "天河国际机场", province: "湖北", region: "华中", coords: [114.21, 30.78], hub: "tier2", tags: ["江城九省通衢", "黄鹤楼", "春季樱花"] },
  "徐州": { code: "XUZ", airport: "观音国际机场", province: "江苏", region: "华东", coords: [117.55, 34.05], hub: "tier2", tags: ["淮海枢纽", "两汉文化", "烧烤胜地"] },
  "西双版纳": { code: "JHG", airport: "嘎洒国际机场", province: "云南", region: "西南", coords: [100.76, 21.97], hub: "dest", tags: ["冬日避寒", "热带雨林", "傣族风情", "野象谷"] },
  "丽江": { code: "LJG", airport: "三义国际机场", province: "云南", region: "西南", coords: [100.24, 26.68], hub: "dest", tags: ["玉龙雪山", "古城漫步", "浪漫之都", "春季绝美"] },
  "阿勒泰": { code: "AAT", airport: "雪都机场", province: "新疆", region: "西北", coords: [88.08, 47.75], hub: "dest", tags: ["滑雪粉雪天堂", "喀纳斯禾木", "初夏草原", "9月金秋"] },
  "喀什": { code: "KHG", airport: "徕宁国际机场", province: "新疆", region: "西北", coords: [75.98, 39.54], hub: "dest", tags: ["古丝路明珠", "喀什老城", "帕米尔高原", "西极风光"] },
  "克拉玛依": { code: "KRY", airport: "古海机场", province: "新疆", region: "西北", coords: [84.95, 45.46], hub: "dest", tags: ["魔鬼城", "石油之城", "北疆环线"] },
  "阿克苏": { code: "AKU", airport: "红旗坡机场", province: "新疆", region: "西北", coords: [80.29, 41.26], hub: "dest", tags: ["托木尔大峡谷", "阿克苏苹果", "南疆门户"] },
  "阿拉尔": { code: "AAL", airport: "塔里木机场", province: "新疆", region: "西北", coords: [81.33, 40.54], hub: "dest", tags: ["塔河之源", "沙漠胡杨林", "深秋金黄"] },
  "图木舒克": { code: "TWS", airport: "唐王城机场", province: "新疆", region: "西北", coords: [79.13, 39.87], hub: "dest", tags: ["丝路重镇", "沙漠绿洲", "南疆探索"] },
  "乌鲁木齐": { code: "URC", airport: "地窝堡国际机场", province: "新疆", region: "西北", coords: [87.47, 43.90], hub: "tier2", tags: ["新疆首府", "天山天池", "丝路大巴扎"] },
  "三亚": { code: "SYX", airport: "凤凰国际机场", province: "海南", region: "华南", coords: [109.41, 18.30], hub: "dest", tags: ["热带海岛", "冬季避寒", "阳光沙滩", "冲浪度假"] },
  "海口": { code: "HAK", airport: "美兰国际机场", province: "海南", region: "华南", coords: [110.46, 19.93], hub: "dest", tags: ["椰城海风", "免税购物", "冬日避寒"] },
  "珠海": { code: "ZUH", airport: "金湾机场", province: "广东", region: "华南", coords: [113.37, 22.01], hub: "dest", tags: ["海滨之城", "长隆海洋王国", "港珠澳大桥"] },
  "深圳": { code: "SZX", airport: "宝安国际机场", province: "广东", region: "华南", coords: [113.81, 22.64], hub: "tier2", tags: ["创新之都", "大湾区核心", "四季宜行"] },
  "太原": { code: "TYN", airport: "武宿国际机场", province: "山西", region: "华北", coords: [112.63, 37.75], hub: "feeder", tags: ["晋阳古城", "晋祠", "面食之都", "高铁辐射枢纽"] },
  "西安": { code: "XIY", airport: "咸阳国际机场", province: "陕西", region: "西北", coords: [108.75, 34.44], hub: "tier2", tags: ["十三朝古都", "兵马俑", "大唐不夜城"] },
  "郑州": { code: "CGO", airport: "新郑国际机场", province: "河南", region: "华中", coords: [113.84, 34.52], hub: "tier2", tags: ["中原铁路枢纽", "少林寺", "长龙新疆跳板"] },
  "北京": { code: "PEK", airport: "首都国际机场", province: "北京", region: "华北", coords: [116.59, 40.08], hub: "tier2", tags: ["首都", "长龙京杭快线", "故宫长城"] },
  "重庆": { code: "CKG", airport: "江北国际机场", province: "重庆", region: "西南", coords: [106.64, 29.72], hub: "tier2", tags: ["山城8D魔幻", "火锅之都", "洪崖洞夜景"] },
  "嘉兴": { code: "JXS", airport: "南湖机场", province: "浙江", region: "华东", coords: [120.68, 30.71], hub: "tier2", tags: ["长龙新基地", "乌镇西塘", "江南水乡"] },
  "恩施": { code: "ENH", airport: "许家坪机场", province: "湖北", region: "华中", coords: [109.49, 30.32], hub: "dest", tags: ["恩施大峡谷", "清江画廊", "土家风情", "夏季避暑"] },
  "遵义": { code: "ZYI", airport: "新舟机场", province: "贵州", region: "西南", coords: [107.25, 27.81], hub: "dest", tags: ["红色圣地", "茅台醇香", "茶海漫步"] },
  "贵阳": { code: "KWE", airport: "龙洞堡国际机场", province: "贵州", region: "西南", coords: [106.80, 26.54], hub: "tier2", tags: ["爽爽的贵阳", "黄果树前站", "酸汤丝娃娃"] },
  "西宁": { code: "XNN", airport: "曹家堡国际机场", province: "青海", region: "西北", coords: [102.04, 36.53], hub: "dest", tags: ["青海湖门户", "塔尔寺", "盛夏避暑胜地"] },
  "兰州": { code: "LHW", airport: "中川国际机场", province: "甘肃", region: "西北", coords: [103.62, 36.51], hub: "tier2", tags: ["黄河风情线", "牛肉拉面", "丝路枢纽"] },
  "昆明": { code: "KMG", airport: "长水国际机场", province: "云南", region: "西南", coords: [102.93, 25.10], hub: "tier2", tags: ["春城无处不飞花", "四季如春", "滇池海鸥"] },
  "芒市": { code: "LUM", airport: "德宏芒市机场", province: "云南", region: "西南", coords: [98.53, 24.40], hub: "dest", tags: ["边境小城", "东南亚异域风情", "手抓饭", "暖冬"] },
  "张家界": { code: "DYG", airport: "荷花国际机场", province: "湖南", region: "华中", coords: [110.45, 29.10], hub: "dest", tags: ["阿凡达哈利路亚山", "天门山玻璃栈道", "奇峰异石"] },
  "沈阳": { code: "SHE", airport: "桃仙国际机场", province: "辽宁", region: "东北", coords: [123.48, 41.64], hub: "tier2", tags: ["盛京故宫", "沈阳中街", "东北洗浴文化"] },
  "大连": { code: "DLC", airport: "周水子国际机场", province: "辽宁", region: "东北", coords: [121.54, 38.96], hub: "tier2", tags: ["浪漫海滨", "星海广场", "海鲜之城"] },
  "青岛": { code: "TAO", airport: "胶东国际机场", province: "山东", region: "华东", coords: [120.39, 36.27], hub: "dest", tags: ["红瓦绿树", "青岛啤酒", "海风拂面"] },
  "威海": { code: "WEH", airport: "大水泊国际机场", province: "山东", region: "华东", coords: [122.24, 37.19], hub: "dest", tags: ["千里海岸线", "雪窝威海", "刘公岛", "韩风美食"] },
  "烟台": { code: "YNT", airport: "蓬莱国际机场", province: "山东", region: "华东", coords: [120.98, 37.66], hub: "dest", tags: ["蓬莱仙阁", "葡萄酒城", "海边小酒馆"] },
  "潍坊": { code: "WEF", airport: "南苑机场", province: "山东", region: "华东", coords: [119.12, 36.65], hub: "dest", tags: ["世界风筝都", "齐鲁腹地", "传统非遗"] },
  "临沂": { code: "LYI", airport: "启阳机场", province: "山东", region: "华东", coords: [118.41, 35.05], hub: "dest", tags: ["商贸名城", "蒙山氧吧", "沂蒙风情"] },
  "菏泽": { code: "HZA", airport: "牡丹机场", province: "山东", region: "华东", coords: [115.54, 35.31], hub: "dest", tags: ["中国牡丹之都", "水浒故里", "黄河水乡"] },
  "济南": { code: "TNA", airport: "遥墙国际机场", province: "山东", region: "华东", coords: [117.22, 36.86], hub: "tier2", tags: ["泉城济南", "趵突泉", "大明湖畔"] },
  "呼和浩特": { code: "HET", airport: "白塔国际机场", province: "内蒙古", region: "华北", coords: [111.82, 40.86], hub: "tier2", tags: ["青城大草原", "蒙古特色", "大召寺"] },
  "海拉尔": { code: "HLD", airport: "东山国际机场", province: "内蒙古", region: "华北", coords: [119.83, 49.20], hub: "dest", tags: ["呼伦贝尔大草原", "冬日雪原那达慕", "森林驯鹿"] },
  "包头": { code: "BAV", airport: "东河机场", province: "内蒙古", region: "华北", coords: [110.00, 40.56], hub: "dest", tags: ["鹿城包头", "五当召", "塞外风光"] },
  "赤峰": { code: "CIF", airport: "玉龙机场", province: "内蒙古", region: "华北", coords: [118.84, 42.16], hub: "dest", tags: ["红山文化", "克什克腾石阵", "贡格尔草原"] },
  "通化": { code: "TNH", airport: "三源浦机场", province: "吉林", region: "东北", coords: [125.70, 42.04], hub: "dest", tags: ["长白山南麓", "万峰滑雪场", "葡萄酒之乡"] },
  "鸡西": { code: "JXA", airport: "兴凯湖机场", province: "黑龙江", region: "东北", coords: [131.19, 45.29], hub: "dest", tags: ["兴凯湖冰雪", "界江风光", "原生态冬捕"] },
  "荆州": { code: "SHS", airport: "沙市机场", province: "湖北", region: "华中", coords: [112.46, 30.33], hub: "dest", tags: ["楚国故都", "三国荆州古城", "水乡鱼米"] },
  "襄阳": { code: "XFN", airport: "刘集机场", province: "湖北", region: "华中", coords: [112.29, 32.15], hub: "dest", tags: ["侠义之城", "古隆中", "襄阳古城墙"] },
  "长沙": { code: "CSX", airport: "黄花国际机场", province: "湖南", region: "华中", coords: [113.22, 28.19], hub: "tier2", tags: ["星城长沙", "文和友茶颜悦色", "夜市烟火"] },
  "衡阳": { code: "HNY", airport: "南岳机场", province: "湖南", region: "华中", coords: [112.62, 26.72], hub: "dest", tags: ["南岳衡山", "石鼓书院", "湘江明珠"] },
  "南宁": { code: "NNG", airport: "吴圩国际机场", province: "广西", region: "华南", coords: [108.17, 22.61], hub: "tier2", tags: ["半城绿树半城楼", "老友粉", "东盟博览会"] },
  "柳州": { code: "LZH", airport: "白莲机场", province: "广西", region: "华南", coords: [109.40, 24.21], hub: "dest", tags: ["螺蛳粉原产地", "百里柳江", "工业喀斯特"] },
  "赣州": { code: "KOW", airport: "黄金机场", province: "江西", region: "华东", coords: [114.78, 25.85], hub: "dest", tags: ["江南宋城", "客家摇篮", "脐橙之乡"] },
  "泉州": { code: "JJN", airport: "晋江国际机场", province: "福建", region: "华东", coords: [118.59, 24.80], hub: "dest", tags: ["宋元中国的世界海洋商贸中心", "簪花围", "闽南古厝"] },
  "福州": { code: "FOC", airport: "长乐国际机场", province: "福建", region: "华东", coords: [119.66, 25.93], hub: "tier2", tags: ["有福之州", "三坊七巷", "闽菜之源"] },
  "常州": { code: "CZX", airport: "奔牛国际机场", province: "江苏", region: "华东", coords: [119.78, 31.91], hub: "feeder", tags: ["恐龙园", "江南名城", "毗邻太湖"] },
  "无锡": { code: "WUX", airport: "硕放国际机场", province: "江苏", region: "华东", coords: [120.43, 31.50], hub: "feeder", tags: ["太湖明珠", "鼋头渚春樱", "江南园林"] },
  "南京": { code: "NKG", airport: "禄口国际机场", province: "江苏", region: "华东", coords: [118.86, 31.74], hub: "tier2", tags: ["六朝古都", "秦淮河畔", "金陵风骨"] },
  "上海": { code: "SHA", airport: "虹桥/浦东机场", province: "上海", region: "华东", coords: [121.34, 31.20], hub: "tier2", tags: ["魔都上海", "外滩东方明珠", "迪士尼"] },
  "邯郸": { code: "HDG", airport: "机场", province: "河北", region: "华北", coords: [114.43, 36.53], hub: "dest", tags: ["成语之都", "赵国古都", "丛台公园"] },
  "东营": { code: "DOY", airport: "胜利机场", province: "山东", region: "华东", coords: [118.79, 37.51], hub: "dest", tags: ["黄河入海口", "胜利油田", "红地毯湿地"] },
  "泸州": { code: "LZO", airport: "云龙机场", province: "四川", region: "西南", coords: [105.47, 28.98], hub: "dest", tags: ["中国酒城", "泸州老窖", "长江之畔"] },
  "达州": { code: "DAX", airport: "金垭机场", province: "四川", region: "西南", coords: [107.43, 31.14], hub: "dest", tags: ["巴人故里", "中国气都", "川东门户"] },
  "巴中": { code: "BZX", airport: "恩阳机场", province: "四川", region: "西南", coords: [106.65, 31.79], hub: "dest", tags: ["光雾山红叶", "川陕苏区", "恩阳古镇"] },
  "茅台": { code: "WMT", airport: "茅台机场", province: "贵州", region: "西南", coords: [106.44, 27.70], hub: "dest", tags: ["国酒之乡", "赤水河畔", "酱香沉醉"] }
};

/**
 * 周边高铁/城际接驳枢纽关系网
 * 用于“出发地直飞较少时，智能推荐高铁接驳到周边大枢纽乘机”
 */
export const HIGH_SPEED_RAIL_CONNECTIONS = {
  "杭州": [
    { target: "上海", mode: "高铁", duration: "45min - 1h", priceRange: "¥50 - ¥75", advantage: "沪杭同城互补，航线极丰富" },
    { target: "宁波", mode: "高铁", duration: "50min", priceRange: "¥55 - ¥70", advantage: "长龙沿海基地联动" },
    { target: "嘉兴", mode: "高铁", duration: "25min", priceRange: "¥30 - ¥40", advantage: "长龙新基地联运" }
  ],
  "太原": [
    { target: "郑州", mode: "高铁", duration: "1.5h - 2h", priceRange: "¥140 - ¥160", advantage: "郑州飞新疆(阿克苏/阿拉尔/克拉玛依/喀什)长龙大线极密集，秒杀直飞" },
    { target: "西安", mode: "高铁", duration: "2.5h - 3h", priceRange: "¥178 - ¥198", advantage: "西安长龙直通西双版纳、喀什、恩施、哈尔滨、常州等" },
    { target: "北京", mode: "高铁", duration: "2h - 2.5h", priceRange: "¥150 - ¥180", advantage: "北京飞杭州长龙大本营，再从杭州通达全国 45+ 城市" },
    { target: "石家庄", mode: "高铁", duration: "1h", priceRange: "¥68 - ¥85", advantage: "华北近距换乘跳板" }
  ],
  "常州": [
    { target: "杭州", mode: "高铁", duration: "1h", priceRange: "¥70 - ¥90", advantage: "直达长龙超级大本营，45 条直飞任选" },
    { target: "嘉兴", mode: "高铁", duration: "45min", priceRange: "¥55 - ¥70", advantage: "嘉兴南湖机场直飞银川/兰州/海口/乌鲁木齐/哈尔滨" }
  ],
  "无锡": [
    { target: "杭州", mode: "高铁", duration: "50min", priceRange: "¥60 - ¥80", advantage: "直飞喀什/阿勒泰/三亚/丽江/版纳" },
    { target: "嘉兴", mode: "高铁", duration: "40min", priceRange: "¥45 - ¥60", advantage: "长龙基地快速出发" }
  ],
  "南宁": [
    { target: "广州", mode: "高铁", duration: "2.5h - 3h", priceRange: "¥170 - ¥190", advantage: "广州长龙飞阿勒泰、喀什、西双版纳、海拉尔等神仙航线" }
  ],
  "邯郸": [
    { target: "郑州", mode: "高铁", duration: "40min", priceRange: "¥60 - ¥75", advantage: "郑州飞长龙新疆全线" },
    { target: "北京", mode: "高铁", duration: "1.5h", priceRange: "¥110 - ¥130", advantage: "进京转长龙快线" }
  ],
  "赤峰": [
    { target: "北京", mode: "高铁", duration: "1.5h - 2h", priceRange: "¥120 - ¥145", advantage: "转机大本营" }
  ],
  "包头": [
    { target: "呼和浩特", mode: "动车", duration: "50min", priceRange: "¥30 - ¥45", advantage: "呼和浩特长龙航线更多" },
    { target: "西安", mode: "高铁/飞机", duration: "3h", priceRange: "¥200+", advantage: "西北主枢纽" }
  ]
};

/**
 * 季节性出行推荐表（契合长龙惠飞版 5 大出行时段）
 */
export const SEASONAL_GUIDE = [
  {
    id: "season-1",
    name: "秋冬初雪与温暖避寒",
    dateRange: "2026.10.25 - 2027.01.21",
    tag: "滑雪温泉 · 温暖越冬",
    bgGradient: "from-blue-600 to-indigo-900",
    description: "北国初雪封山，阿勒泰/吉林开启粉雪滑雪季；南方版纳/三亚进入温暖适宜过冬期。",
    destinations: [
      { city: "阿勒泰", reason: "可可托海/将军山粉雪初开，雪质极顶，体验人间仙境", highlight: "天然粉雪 / 禾木晨雾" },
      { city: "哈尔滨", reason: "12月冰雪大世界试开园，欧式雪景与马迭尔冰棍", highlight: "冰雪大世界 / 圣索菲亚" },
      { city: "西双版纳", reason: "全国绝佳避寒地，25℃恒温，热带水果与星光夜市", highlight: "避寒过冬 / 傣迪野象" },
      { city: "长春", reason: "长白山滑雪与长春净月潭雪雕，东北热炕头文化", highlight: "长白山前哨 / 温泉滑雪" },
      { city: "三亚", reason: "冬天潜水与椰梦长廊落日，免税购物天堂", highlight: "阳光海岸 / 避寒潜水" },
      { city: "通化", reason: "万峰滑雪场，专业雪道性价比极高", highlight: "小众滑雪宝地" }
    ]
  },
  {
    id: "season-2",
    name: "早春西南花海与水乡",
    dateRange: "2027.03.03 - 2027.04.27",
    tag: "春茶踏青 · 赏花避峰",
    bgGradient: "from-emerald-600 to-teal-900",
    description: "避开春运高峰，错峰踏春。贵州云南百花争艳，江南烟雨蒙蒙采明前茶。",
    destinations: [
      { city: "丽江", reason: "玉龙雪山融雪初春，樱花杜鹃绽放，错峰静谧", highlight: "束河古镇 / 蓝月谷" },
      { city: "遵义", reason: "万亩茶海碧波翻滚，气温回升，品尝茅台美酒", highlight: "湄潭茶海 / 红色之旅" },
      { city: "恩施", reason: "春季清江画廊水碧如翡翠，大峡谷云雾缭绕", highlight: "地缝绝壁 / 土家摔碗酒" },
      { city: "杭州", reason: "龙井新茶开采，西湖苏堤春晓，柳绿桃红", highlight: "西湖十景 / 龙井问茶" },
      { city: "芒市", reason: "德宏傣族泼水节前夕，金塔银塔异域风情，早春暖意", highlight: "异域美食 / 温泉养生" }
    ]
  },
  {
    id: "season-3",
    name: "初夏北疆草原天花板",
    dateRange: "2027.05.07 - 2027.06.30",
    tag: "草原花海 · 避峰长假",
    bgGradient: "from-green-600 to-sky-900",
    description: "【长龙航线王炸推荐时段】5月下旬至6月北疆草原野花铺地，雪山白顶，游客远少于7-8月，物价极为亲民！",
    destinations: [
      { city: "阿勒泰", reason: "5-6月禾木水草最青翠，喀纳斯湖水碧蓝，气候极舒适", highlight: "夏牧场花海 / 喀纳斯湖" },
      { city: "喀什", reason: "帕米尔高原杏花后夏牧场开草，喀什老城人少惬意", highlight: "白沙湖 / 慕士塔格峰" },
      { city: "西宁", reason: "盛夏避暑胜地，青海湖畔候鸟翱翔，油菜花初绽", highlight: "青海湖 / 茶卡盐湖" },
      { city: "克拉玛依", reason: "初夏前往乌尔禾魔鬼城，日落晚霞壮丽无双", highlight: "雅丹地貌 / 独库公路北起点" },
      { city: "银川", reason: "初夏贺兰山徒步与沙坡头大漠黄河，塞上江南好风光", highlight: "沙坡头 / 镇北堡影城" }
    ]
  },
  {
    id: "season-4",
    name: "金秋喀纳斯与胡杨林",
    dateRange: "2027.09.01 - 2027.09.26",
    tag: "金色秋景 · 错峰国庆",
    bgGradient: "from-amber-600 to-orange-900",
    description: "赶在国庆汹涌人潮之前！9月中下旬是阿勒泰、禾木金黄白桦林的颜值顶峰，秋季美景天花板。",
    destinations: [
      { city: "阿勒泰", reason: "9月禾木层林尽染，如同上帝打翻的调色盘，全球秋景天花板", highlight: "月亮湾晨雾 / 禾木秋色" },
      { city: "银川", reason: "初秋额济纳胡杨林前线，贺兰山下葡萄采摘季与葡萄酒庄", highlight: "大漠落日 / 西夏陵" },
      { city: "赤峰", reason: "克什克腾乌兰布统草原秋草金黄，白桦林摄影圣地", highlight: "乌兰布统秋色" },
      { city: "威海", reason: "初秋海风清爽，开海海鲜盛宴，海岸线自驾公路", highlight: "千里山海自驾 / 开海海鲜" }
    ]
  },
  {
    id: "season-5",
    name: "深秋南疆胡杨与海岛",
    dateRange: "2027.10.11 - 2027.10.30",
    tag: "大漠胡杨 · 晚秋漫步",
    bgGradient: "from-rose-600 to-purple-900",
    description: "国庆长假后人潮退去，塔里木河流域胡杨林迎来最金黄璀璨时刻；华南秋高气爽。",
    destinations: [
      { city: "阿拉尔", reason: "塔里木河畔原始胡杨林如金色燃烧，摄影师私藏地", highlight: "塔里木胡杨 / 沙漠公路" },
      { city: "图木舒克", reason: "唐王城古韵，南疆秋日阳光明媚，甜度超高红枣采摘", highlight: "古丝路遗迹 / 金秋采摘" },
      { city: "喀什", reason: "喀什老城秋日浓郁风情，手抓饭与无花果甜透心脾", highlight: "百年茶馆 / 塔县雪山" },
      { city: "海口", reason: "晚秋秋风微凉，避开酷暑与台风，老街慢生活", highlight: "骑楼老街 / 清补凉" }
    ]
  }
];
