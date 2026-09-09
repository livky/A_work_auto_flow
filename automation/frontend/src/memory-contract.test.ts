import { describe, expect, it } from "vitest";
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";
import { readFileSync } from "node:fs";
import { validateMemoryShape } from "./memory-contract";
import { memorySchema } from "./generated/memory-schema";

describe("C08 Python / frontend structural memory contract parity", () => {
  it("executes every registered kind and positive/negative variant in both runtimes", () => {
    // The installed offline runtime is reused; no pip/npm/network fallback.
    const root = resolve("../..");
    expect(memorySchema).toEqual(
      JSON.parse(
        readFileSync(
          resolve(root, "automation/schemas/memory-v3.schema.json"),
          "utf8",
        ),
      ),
    );
    const python =
      process.env.MEMORY_TEST_PYTHON ??
      resolve(root, "services/qdrant/runtime/python.exe");
    const result = spawnSync(
      python,
      [resolve(root, "automation/tests/memory_contract_matrix.py")],
      { encoding: "utf8", windowsHide: true },
    );
    expect(result.status, result.stderr).toBe(0);
    const matrix = JSON.parse(result.stdout) as {
      name: string;
      definition: string;
      value: unknown;
      valid: boolean;
    }[];
    expect(matrix).toHaveLength(188);
    expect(matrix.filter((row) => row.name.endsWith(":valid"))).toHaveLength(
      15,
    );
    expect(matrix.some((row) => row.valid)).toBe(true);
    expect(matrix.some((row) => !row.valid)).toBe(true);
    for (const row of matrix)
      expect(validateMemoryShape(row.value, row.definition), row.name).toBe(
        row.valid,
      );
  });

  it("rejects non-finite browser values before JSON can coerce them to null", () => {
    for (const value of [NaN, Infinity, -Infinity, undefined]) {
      expect(
        validateMemoryShape(
          { value, reason: "unknown", note: "SYNTHETIC ONLY" },
          "UnknownValue",
        ),
      ).toBe(false);
    }
    expect(() => validateMemoryShape({}, "https://invalid/schema")).toThrow();
  });
});
