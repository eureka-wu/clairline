/**
 * 长龙航空 71 城市与航网核心数据库
 * 包含：经纬度、区域、机场名称/代码、季节性标签、冬春/夏秋季执飞状态标注
 */
export const CITY_METADATA = {
  "杭州": { code: "HGH", airport: "萧山国际机场", province: "浙江", region: "华东", coords: [120.43, 30.23], hub: "tier1", pinyin: "hangzhou hz", tags: ["总部基地", "江南水乡", "四季皆宜", "美食"] },
  "银川": { code: "INC", airport: "河东国际机场", province: "宁夏", region: "西北", coords: [106.39, 38.32], hub: "tier1", pinyin: "yinchuan yc", tags: ["西北枢纽", "大漠风光", "枸杞之乡", "中转要地"] },
  "长春": { code: "CGQ", airport: "龙嘉国际机场", province: "吉林", region: "东北", coords: [125.68, 43.99], hub: "tier1", pinyin: "changchun cc", tags: ["东北枢纽", "冰雪天地", "长白山前哨", "滑雪"] },
  "宁波": { code: "NGB", airport: "栎社国际机场", province: "浙江", region: "华东", coords: [121.46, 29.82], hub: "tier2", pinyin: "ningbo nb", tags: ["沿海基地", "海鲜之都", "江南古镇"] },
  "哈尔滨": { code: "HRB", airport: "太平国际机场", province: "黑龙江", region: "东北", coords: [126.25, 45.62], hub: "tier2", pinyin: "haerbin heb hr", tags: ["冰雪大世界", "滑雪胜地", "俄式风情", "冬季极佳"] },
  "温州": { code: "WNZ", airport: "龙湾国际机场", province: "浙江", region: "华东", coords: [120.85, 27.91], hub: "tier2", pinyin: "wenzhou wz", tags: ["沿海重点", "雁荡奇秀", "经商名城"] },
  "广州": { code: "CAN", airport: "白云国际机场", province: "广东", region: "华南", coords: [113.30, 23.39], hub: "tier2", pinyin: "guangzhou gz", tags: ["大湾区门户", "粤菜之巅", "四季温暖"] },
  "成都": { code: "TFU", airport: "天府国际机场", province: "四川", region: "西南", coords: [104.44, 30.32], hub: "tier2", pinyin: "chengdu cd", tags: ["天府之国", "大熊猫", "川味美食", "进川入藏"] },
  "武汉": { code: "WUH", airport: "天河国际机场", province: "湖北", region: "华中", coords: [114.21, 30.78], hub: "tier2", pinyin: "wuhan wh", tags: ["江城九省通衢", "黄鹤楼", "春季樱花"] },
  "徐州": { code: "XUZ", airport: "观音国际机场", province: "江苏", region: "华东", coords: [117.55, 34.05], hub: "tier2", pinyin: "xuzhou xz", tags: ["淮海枢纽", "两汉文化", "烧烤胜地"] },
  "西双版纳": { code: "JHG", airport: "嘎洒国际机场", province: "云南", region: "西南", coords: [100.76, 21.97], hub: "dest", pinyin: "xishuangbanna xsbn bn", tags: ["冬日避寒", "热带雨林", "傣族风情", "野象谷"] },
  "丽江": { code: "LJG", airport: "三义国际机场", province: "云南", region: "西南", coords: [100.24, 26.68], hub: "dest", pinyin: "lijiang lj", tags: ["玉龙雪山", "古城漫步", "浪漫之都", "春季绝美"] },
  "阿勒泰": { code: "AAT", airport: "雪都机场", province: "新疆", region: "西北", coords: [88.08, 47.75], hub: "dest", pinyin: "aletai alt", tags: ["滑雪粉雪天堂", "喀纳斯禾木", "初夏草原", "9月金秋"] },
  "喀什": { code: "KHG", airport: "徕宁国际机场", province: "新疆", region: "西北", coords: [75.98, 39.54], hub: "dest", pinyin: "kashi ks", tags: ["古丝路明珠", "喀什老城", "帕米尔高原", "西极风光"] },
  "克拉玛依": { code: "KRY", airport: "古海机场", province: "新疆", region: "西北", coords: [84.95, 45.46], hub: "dest", pinyin: "kelamayi klmy", tags: ["魔鬼城", "石油之城", "北疆环线"] },
  "阿克苏": { code: "AKU", airport: "红旗坡机场", province: "新疆", region: "西北", coords: [80.29, 41.26], hub: "dest", pinyin: "akesu aks", tags: ["托木尔大峡谷", "阿克苏苹果", "南疆门户"] },
  "阿拉尔": { code: "AAL", airport: "塔里木机场", province: "新疆", region: "西北", coords: [81.33, 40.54], hub: "dest", pinyin: "alaer ale", tags: ["塔河之源", "沙漠胡杨林", "深秋金黄"] },
  "图木舒克": { code: "TWS", airport: "唐王城机场", province: "新疆", region: "西北", coords: [79.13, 39.87], hub: "dest", pinyin: "tumushuke tmsk", tags: ["丝路重镇", "沙漠绿洲", "南疆探索"] },
  "乌鲁木齐": { code: "URC", airport: "地窝堡国际机场", province: "新疆", region: "西北", coords: [87.47, 43.90], hub: "tier2", pinyin: "wulumuqi wlmq", tags: ["新疆首府", "天山天池", "丝路大巴扎"] },
  "三亚": { code: "SYX", airport: "凤凰国际机场", province: "海南", region: "华南", coords: [109.41, 18.30], hub: "dest", pinyin: "sanya sy", tags: ["热带海岛", "冬季避寒", "阳光沙滩", "冲浪度假"] },
  "海口": { code: "HAK", airport: "美兰国际机场", province: "海南", region: "华南", coords: [110.46, 19.93], hub: "dest", pinyin: "haikou hk", tags: ["椰城海风", "免税购物", "冬日避寒"] },
  "珠海": { code: "ZUH", airport: "金湾机场", province: "广东", region: "华南", coords: [113.37, 22.01], hub: "dest", pinyin: "zhuhai zh", tags: ["海滨之城", "长隆海洋王国", "港珠澳大桥"] },
  "深圳": { code: "SZX", airport: "宝安国际机场", province: "广东", region: "华南", coords: [113.81, 22.64], hub: "tier2", pinyin: "shenzhen sz", tags: ["创新之都", "大湾区核心", "四季宜行"] },
  "太原": { code: "TYN", airport: "武宿国际机场", province: "山西", region: "华北", coords: [112.63, 37.75], hub: "feeder", pinyin: "taiyuan ty", tags: ["晋阳古城", "晋祠", "面食之都", "高铁辐射枢纽"] },
  "西安": { code: "XIY", airport: "咸阳国际机场", province: "陕西", region: "西北", coords: [108.75, 34.44], hub: "tier2", pinyin: "xian xa", tags: ["十三朝古都", "兵马俑", "大唐不夜城"] },
  "郑州": { code: "CGO", airport: "新郑国际机场", province: "河南", region: "华中", coords: [113.84, 34.52], hub: "tier2", pinyin: "zhengzhou zz", tags: ["中原铁路枢纽", "少林寺", "长龙新疆跳板"] },
  "北京": { code: "PEK", airport: "首都国际机场", province: "北京", region: "华北", coords: [116.59, 40.08], hub: "tier2", pinyin: "beijing bj", tags: ["首都", "长龙京杭快线", "故宫长城"] },
  "重庆": { code: "CKG", airport: "江北国际机场", province: "重庆", region: "西南", coords: [106.64, 29.72], hub: "tier2", pinyin: "chongqing cq", tags: ["山城8D魔幻", "火锅之都", "洪崖洞夜景"] },
  "嘉兴": { code: "JXS", airport: "南湖机场", province: "浙江", region: "华东", coords: [120.68, 30.71], hub: "tier2", pinyin: "jiaxing jx", tags: ["长龙新基地", "乌镇西塘", "江南水乡"] },
  "恩施": { code: "ENH", airport: "许家坪机场", province: "湖北", region: "华中", coords: [109.49, 30.32], hub: "dest", pinyin: "enshi es", tags: ["恩施大峡谷", "清江画廊", "土家风情", "夏季避暑"] },
  "遵义": { code: "ZYI", airport: "新舟机场", province: "贵州", region: "西南", coords: [107.25, 27.81], hub: "dest", pinyin: "zunyi zy", tags: ["红色圣地", "茅台醇香", "茶海漫步"] },
  "贵阳": { code: "KWE", airport: "龙洞堡国际机场", province: "贵州", region: "西南", coords: [106.80, 26.54], hub: "tier2", pinyin: "guiyang gy", tags: ["爽爽的贵阳", "黄果树前站", "酸汤丝娃娃"] },
  "西宁": { code: "XNN", airport: "曹家堡国际机场", province: "青海", region: "西北", coords: [102.04, 36.53], hub: "dest", pinyin: "xining xn", tags: ["青海湖门户", "塔尔寺", "盛夏避暑胜地"] },
  "兰州": { code: "LHW", airport: "中川国际机场", province: "甘肃", region: "西北", coords: [103.62, 36.51], hub: "tier2", pinyin: "lanzhou lz", tags: ["黄河风情线", "牛肉拉面", "丝路枢纽"] },
  "昆明": { code: "KMG", airport: "长水国际机场", province: "云南", region: "西南", coords: [102.93, 25.10], hub: "tier2", pinyin: "kunming km", tags: ["春城无处不飞花", "四季如春", "滇池海鸥"] },
  "芒市": { code: "LUM", airport: "德宏芒市机场", province: "云南", region: "西南", coords: [98.53, 24.40], hub: "dest", pinyin: "mangshi ms", tags: ["边境小城", "东南亚异域风情", "手抓饭", "暖冬"] },
  "张家界": { code: "DYG", airport: "荷花国际机场", province: "湖南", region: "华中", coords: [110.45, 29.10], hub: "dest", pinyin: "zhangjiajie zjj", tags: ["阿凡达哈利路亚山", "天门山玻璃栈道", "奇峰异石"] },
  "沈阳": { code: "SHE", airport: "桃仙国际机场", province: "辽宁", region: "东北", coords: [123.48, 41.64], hub: "tier2", pinyin: "shenyang sy", tags: ["盛京故宫", "沈阳中街", "东北洗浴文化"] },
  "大连": { code: "DLC", airport: "周水子国际机场", province: "辽宁", region: "东北", coords: [121.54, 38.96], hub: "tier2", pinyin: "dalian dl", tags: ["浪漫海滨", "星海广场", "海鲜之城"] },
  "青岛": { code: "TAO", airport: "胶东国际机场", province: "山东", region: "华东", coords: [120.39, 36.27], hub: "dest", pinyin: "qingdao qd", tags: ["红瓦绿树", "青岛啤酒", "海风拂面"] },
  "威海": { code: "WEH", airport: "大水泊国际机场", province: "山东", region: "华东", coords: [122.24, 37.19], hub: "dest", pinyin: "weihai wh", tags: ["千里海岸线", "雪窝威海", "刘公岛", "韩风美食"] },
  "烟台": { code: "YNT", airport: "蓬莱国际机场", province: "山东", region: "华东", coords: [120.98, 37.66], hub: "dest", pinyin: "yantai yt", tags: ["蓬莱仙阁", "葡萄酒城", "海边小酒馆"] },
  "潍坊": { code: "WEF", airport: "南苑机场", province: "山东", region: "华东", coords: [119.12, 36.65], hub: "dest", pinyin: "weifang wf", tags: ["世界风筝都", "齐鲁腹地", "传统非遗"] },
  "临沂": { code: "LYI", airport: "启阳机场", province: "山东", region: "华东", coords: [118.41, 35.05], hub: "dest", pinyin: "linyi ly", tags: ["商贸名城", "蒙山氧吧", "沂蒙风情"] },
  "菏泽": { code: "HZA", airport: "牡丹机场", province: "山东", region: "华东", coords: [115.54, 35.31], hub: "dest", pinyin: "heze hz", tags: ["中国牡丹之都", "水浒故里", "黄河水乡"] },
  "济南": { code: "TNA", airport: "遥墙国际机场", province: "山东", region: "华东", coords: [117.22, 36.86], hub: "tier2", pinyin: "jinan jn", tags: ["泉城济南", "趵突泉", "大明湖畔"] },
  "呼和浩特": { code: "HET", airport: "白塔国际机场", province: "内蒙古", region: "华北", coords: [111.82, 40.86], hub: "tier2", pinyin: "huhehaote hhht", tags: ["青城大草原", "蒙古特色", "大召寺"] },
  "海拉尔": { code: "HLD", airport: "东山国际机场", province: "内蒙古", region: "华北", coords: [119.83, 49.20], hub: "dest", pinyin: "hailaer hle", tags: ["呼伦贝尔大草原", "冬日雪原那达慕", "森林驯鹿"] },
  "包头": { code: "BAV", airport: "东河机场", province: "内蒙古", region: "华北", coords: [110.00, 40.56], hub: "dest", pinyin: "baotou bt", tags: ["鹿城包头", "五当召", "塞外风光"] },
  "赤峰": { code: "CIF", airport: "玉龙机场", province: "内蒙古", region: "华北", coords: [118.84, 42.16], hub: "dest", pinyin: "chifeng cf", tags: ["红山文化", "克什克腾石阵", "贡格尔草原"] },
  "通化": { code: "TNH", airport: "三源浦机场", province: "吉林", region: "东北", coords: [125.70, 42.04], hub: "dest", pinyin: "tonghua th", tags: ["长白山南麓", "万峰滑雪场", "葡萄酒之乡"] },
  "鸡西": { code: "JXA", airport: "兴凯湖机场", province: "黑龙江", region: "东北", coords: [131.19, 45.29], hub: "dest", pinyin: "jixi jx", tags: ["兴凯湖冰雪", "界江风光", "原生态冬捕"] },
  "荆州": { code: "SHS", airport: "沙市机场", province: "湖北", region: "华中", coords: [112.46, 30.33], hub: "dest", pinyin: "jingzhou jz", tags: ["楚国故都", "三国荆州古城", "水乡鱼米"] },
  "襄阳": { code: "XFN", airport: "刘集机场", province: "湖北", region: "华中", coords: [112.29, 32.15], hub: "dest", pinyin: "xiangyang xy", tags: ["侠义之城", "古隆中", "襄阳古城墙"] },
  "长沙": { code: "CSX", airport: "黄花国际机场", province: "湖南", region: "华中", coords: [113.22, 28.19], hub: "tier2", pinyin: "changsha cs", tags: ["星城长沙", "文和友茶颜悦色", "夜市烟火"] },
  "衡阳": { code: "HNY", airport: "南岳机场", province: "湖南", region: "华中", coords: [112.62, 26.72], hub: "dest", pinyin: "hengyang hy", tags: ["南岳衡山", "石鼓书院", "湘江明珠"] },
  "南宁": { code: "NNG", airport: "吴圩国际机场", province: "广西", region: "华南", coords: [108.17, 22.61], hub: "tier2", pinyin: "nanning nn", tags: ["半城绿树半城楼", "老友粉", "东盟博览会"] },
  "柳州": { code: "LZH", airport: "白莲机场", province: "广西", region: "华南", coords: [109.40, 24.21], hub: "dest", pinyin: "liuzhou lz", tags: ["螺蛳粉原产地", "百里柳江", "工业喀斯特"] },
  "赣州": { code: "KOW", airport: "黄金机场", province: "江西", region: "华东", coords: [114.78, 25.85], hub: "dest", pinyin: "ganzhou gz", tags: ["江南宋城", "客家摇篮", "脐橙之乡"] },
  "泉州": { code: "JJN", airport: "晋江国际机场", province: "福建", region: "华东", coords: [118.59, 24.80], hub: "dest", pinyin: "quanzhou qz", tags: ["宋元中国的世界海洋商贸中心", "簪花围", "闽南古厝"] },
  "福州": { code: "FOC", airport: "长乐国际机场", province: "福建", region: "华东", coords: [119.66, 25.93], hub: "tier2", pinyin: "fuzhou fz", tags: ["有福之州", "三坊七巷", "闽菜之源"] },
  "常州": { code: "CZX", airport: "奔牛国际机场", province: "江苏", region: "华东", coords: [119.78, 31.91], hub: "feeder", pinyin: "changzhou cz", tags: ["恐龙园", "江南名城", "毗邻太湖"] },
  "无锡": { code: "WUX", airport: "硕放国际机场", province: "江苏", region: "华东", coords: [120.43, 31.50], hub: "feeder", pinyin: "wuxi wx", tags: ["太湖明珠", "鼋头渚春樱", "江南园林"] },
  "南京": { code: "NKG", airport: "禄口国际机场", province: "江苏", region: "华东", coords: [118.86, 31.74], hub: "tier2", pinyin: "nanjing nj", tags: ["六朝古都", "秦淮河畔", "金陵风骨"] },
  "上海": { code: "SHA", airport: "虹桥/浦东机场", province: "上海", region: "华东", coords: [121.34, 31.20], hub: "tier2", pinyin: "shanghai sh", tags: ["魔都上海", "外滩东方明珠", "迪士尼"] },
  "邯郸": { code: "HDG", airport: "机场", province: "河北", region: "华北", coords: [114.43, 36.53], hub: "dest", pinyin: "handan hd", tags: ["成语之都", "赵国古都", "丛台公园"] },
  "东营": { code: "DOY", airport: "胜利机场", province: "山东", region: "华东", coords: [118.79, 37.51], hub: "dest", pinyin: "dongying dy", tags: ["黄河入海口", "胜利油田", "红地毯湿地"] },
  "泸州": { code: "LZO", airport: "云龙机场", province: "四川", region: "西南", coords: [105.47, 28.98], hub: "dest", pinyin: "luzhou lz", tags: ["中国酒城", "泸州老窖", "长江之畔"] },
  "达州": { code: "DAX", airport: "金垭机场", province: "四川", region: "西南", coords: [107.43, 31.14], hub: "dest", pinyin: "dazhou dz", tags: ["巴人故里", "中国气都", "川东门户"] },
  "巴中": { code: "BZX", airport: "恩阳机场", province: "四川", region: "西南", coords: [106.65, 31.79], hub: "dest", pinyin: "bazhong bz", tags: ["光雾山红叶", "川陕苏区", "恩阳古镇"] },
  "茅台": { code: "WMT", airport: "茅台机场", province: "贵州", region: "西南", coords: [106.44, 27.70], hub: "dest", pinyin: "maotai mt", tags: ["国酒之乡", "赤水河畔", "酱香沉醉"] }
};

export const HIGH_SPEED_RAIL_CONNECTIONS = {
  "杭州": [
    { target: "上海", mode: "高铁", duration: "45min - 1h", priceRange: "¥50 - ¥75", advantage: "沪杭同城互补，航线极丰富" },
    { target: "宁波", mode: "高铁", duration: "50min", priceRange: "¥55 - ¥70", advantage: "长龙沿海基地联动" },
    { target: "嘉兴", mode: "高铁", duration: "25min", priceRange: "¥30 - ¥40", advantage: "长龙新基地联运" }
  ],
  "太原": [
    { target: "郑州", mode: "高铁", duration: "1.5h - 2h", priceRange: "¥140 - ¥160", advantage: "郑州飞新疆长龙大线极密集，秒杀直飞" },
    { target: "西安", mode: "高铁", duration: "2.5h - 3h", priceRange: "¥178 - ¥198", advantage: "西安长龙直通西双版纳、喀什、恩施、哈尔滨等" },
    { target: "北京", mode: "高铁", duration: "2h - 2.5h", priceRange: "¥150 - ¥180", advantage: "北京飞杭州大本营，再通达全国" }
  ],
  "常州": [
    { target: "杭州", mode: "高铁", duration: "1h", priceRange: "¥70 - ¥90", advantage: "直达长龙超级大本营，45 条直飞任选" }
  ],
  "无锡": [
    { target: "杭州", mode: "高铁", duration: "50min", priceRange: "¥60 - ¥80", advantage: "直飞喀什/阿勒泰/三亚/丽江/版纳" }
  ],
  "南宁": [
    { target: "广州", mode: "高铁", duration: "2.5h - 3h", priceRange: "¥170 - ¥190", advantage: "广州长龙飞阿勒泰、喀什、西双版纳、海拉尔等" }
  ]
};

export const DEST_ONWARD_TIPS = {
  '图木舒克': '唐王城机场出口乘车或城际铁路，1.5h 直抵【喀什古城/徕宁】、2h 直通【阿克苏托木尔峰大峡谷】。',
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
