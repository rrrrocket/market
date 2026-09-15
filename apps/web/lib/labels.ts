const labels: Record<string, string> = {
  READY: "就绪", DATA_READY: "数据已就绪", TEST_DATA: "测试数据", DISABLED: "已停用",
  NOT_CONNECTED: "未接入", AUTH_REQUIRED: "需要授权", CONNECTOR_AVAILABLE: "连接器可用",
  SYNCED_EMPTY: "同步结果为空", AVAILABLE: "可用", LIMITED_ACCESS: "受限访问",
  COMPLETED: "已完成", PARTIAL: "部分完成", FAILED: "失败", PENDING: "等待中",
  RUNNING: "运行中", DOWNLOADED: "已下载", IMPORTED: "已导入", DOWNLOADING: "下载中",
  IMPORTING: "导入中", ANALYZING: "分析中", IDLE: "待运行", CURRENT: "当前",
  NOT_ANALYZED: "待分析", NO_DATA: "暂无数据", ACTIVE: "进行中", CLOSED: "已结束",
  CONNECTED: "已接入", NOT_ENOUGH_DATA: "数据不足", UNKNOWN: "未知", HIGH: "高",
  MEDIUM: "中", LOW: "低", FRESH: "最新", STALE: "已过期", REPORTED: "已报告",
  OBSERVED: "已观测", ESTIMATED: "估算", INFERRED: "推导", AI_GENERATED: "AI 生成",
  TRADE: "贸易", MACRO: "宏观", TARIFF: "关税", TENDER: "招标", SEARCH: "搜索",
  MARKETPLACE: "市场平台", SUPPLY: "供应", STRUCTURAL: "结构需求", DIGITAL: "数字需求",
  EXPLICIT: "显性需求", ACCESS: "市场准入",
  IMPORT_VALUE: "进口额", CAGR_3Y: "三年复合增长率", YOY_GROWTH: "同比增长",
  CHINA_SHARE: "中国进口份额", MARKET_ATTRACTIVENESS: "市场吸引力",
};

export function label(value: string | null | undefined) {
  if (!value) return "—";
  return labels[value] || value.replaceAll("_", " ");
}
