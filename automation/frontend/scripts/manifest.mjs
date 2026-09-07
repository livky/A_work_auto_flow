// 发布清单只含构建输出；源码指纹让使用机台可以核对源码/资源是否匹配。
import { readdir, readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
const hash = (b) => createHash("sha256").update(b).digest("hex");
async function list(dir) {
  const files = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    if (
      ["node_modules", "test-results", "playwright-report"].includes(entry.name)
    )
      continue;
    const path = `${dir}/${entry.name}`;
    if (entry.isDirectory()) files.push(...(await list(path)));
    else files.push(path);
  }
  return files.sort();
}
const output = "../ui/workbench-assets";
// Include all production transitive dependencies, not only the five entry packages.
const lock = JSON.parse(await readFile("package-lock.json", "utf8"));
const licenses = Object.entries(lock.packages)
  .filter(([path, meta]) => path.startsWith("node_modules/") && !meta.dev)
  .map(([path]) => path.slice("node_modules/".length));
let notice = "# Bundled third-party licenses\n";
for (const name of licenses) {
  const candidates = (await list(`node_modules/${name}`)).filter((p) =>
    /\/(LICENSE|LICENSE\.txt|LICENSE\.md)$/i.test(p),
  );
  for (const p of candidates)
    notice += `\n## ${name}\n${await readFile(p, "utf8")}\n`;
}
await writeFile(`${output}/THIRD_PARTY.txt`, notice);
const sources = {};
for (const p of await list(".")) sources[p.slice(2)] = hash(await readFile(p));
const files = {};
for (const p of await list(output))
  if (!p.endsWith("/asset-manifest.json"))
    files[p.slice(output.length + 1)] = hash(await readFile(p));
await writeFile(
  `${output}/asset-manifest.json`,
  JSON.stringify(
    {
      schema_version: 1,
      api_version: 1,
      sources,
      source_fingerprint: hash(JSON.stringify(sources)),
      files,
    },
    null,
    2,
  ) + "\n",
);
