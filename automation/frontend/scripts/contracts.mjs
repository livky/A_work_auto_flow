import { compileFromFile } from "json-schema-to-typescript";
import { mkdir, writeFile } from "node:fs/promises";
await mkdir("src/generated", { recursive: true });
await writeFile(
  "src/generated/contracts.ts",
  await compileFromFile("contracts/graph.schema.json"),
);
