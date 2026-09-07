// 相对随机前缀访问，无第三方网络请求。错误始终作为纯文本渲染。
export async function api<T>(
  route: string,
  data?: unknown,
  legacy = false,
): Promise<T> {
  const response = await fetch(
    `api/${legacy ? "" : "v1/"}${route}`,
    data === undefined
      ? undefined
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        },
  );
  const value = await response.json();
  if (!response.ok)
    throw new Error(value.error || `请求失败 ${response.status}`);
  return value as T;
}
export function download(name: string, content: string) {
  const url = URL.createObjectURL(
    new Blob([content], { type: "text/plain;charset=utf-8" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const kindNames: Record<string, string> = {
  algorithm: "核心算法",
  run: "实验",
  claim: "结论",
  research: "研究",
  knowledge: "知识",
  report: "报告",
  data: "数据",
  tool: "工具",
  project: "项目",
  material: "材料",
};
export const relationNames: Record<string, string> = {
  supports: "引用支持依据",
  input: "使用输入",
  contradicts: "引用反证",
  background: "引用背景",
  belongs_to: "归属",
  contains: "包含",
  produces: "产出",
  depends_on: "使用上游结果",
  references: "引用",
  related: "关联",
  similar: "语义相似候选",
  keywords: "共享关键词",
};
export type Job = {
  id: string;
  kind: string;
  status: string;
  done: number;
  total: number;
  error: string | null;
  result: unknown;
};
export type Capabilities = {
  api_version: number;
  build: string;
  graph_ready: boolean;
  synthetic: boolean;
  semantic_configured: boolean;
};
