export interface GeoDimension {
  key: string
  label: string
  description: string
  weight: number
}

export interface EngineScore {
  kim: number
  deepSeek: number
}

export interface BrandGeoProfile {
  id: string
  name: string
  industry: string
  logo: string
  overallScore: number
  maturityLevel: '萌芽' | '起步' | '成长' | '成熟' | '领先'
  dimensions: Record<string, EngineScore>
  metrics: {
    aiVisibility: number
    top1Rate: number
    citationCount: number
    contentFreshness: number
    schemaCoverage: number
    entityConsistency: number
  }
  trend: number
  lastUpdated: string
}

export const GEO_DIMENSIONS: GeoDimension[] = [
  { key: 'schema', label: 'Schema结构化', description: 'JSON-LD / 实体标记覆盖率', weight: 0.2 },
  { key: 'engineAdapt', label: '双引擎适配', description: 'Kimi vs DeepSeek 差异化策略', weight: 0.15 },
  { key: 'automation', label: '自动化能力', description: '内容生成与监测自动化程度', weight: 0.1 },
  { key: 'entityTrust', label: '实体一致性', description: '跨平台 NAP / 知识图谱一致性', weight: 0.15 },
  { key: 'eeat', label: 'E-E-A-T权威', description: '经验·专业·权威·可信度', weight: 0.15 },
  { key: 'freshness', label: '内容新鲜度', description: '近90天内内容更新占比', weight: 0.1 },
  { key: 'compliance', label: '合规安全', description: '事实核查与来源标注', weight: 0.08 },
  { key: 'promptCov', label: 'Prompt覆盖', description: '高频Query内容占位率', weight: 0.07 },
]

export const MATURITY_COLORS: Record<string, string> = {
  萌芽: '#94a3b8',
  起步: '#fbbf24',
  成长: '#f59e0b',
  成熟: '#d97706',
  领先: '#b45309',
}
