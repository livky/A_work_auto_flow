/** Structural validation of the fixed memory contract used by the workbench.
 *
 * This only checks the schema shipped with this build. Source authorization,
 * fixed-reference resolution and review transitions still require the public
 * backend preflight; a valid shape never grants permission to save or review.
 */
import { memorySchema } from "./generated/memory-schema";

type Schema = {
  type?: string | string[];
  const?: unknown;
  enum?: unknown[];
  required?: string[];
  properties?: Record<string, Schema>;
  additionalProperties?: boolean | Schema;
  items?: Schema;
  minLength?: number;
  minItems?: number;
  oneOf?: Schema[];
  $ref?: string;
};
const definitions = (memorySchema as { $defs: Record<string, Schema> }).$defs;

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

/** Reject values JSON would silently drop/coerce before checking field types. */
function finiteJson(value: unknown): boolean {
  if (value === null || typeof value === "string" || typeof value === "boolean")
    return true;
  if (typeof value === "number") return Number.isFinite(value);
  if (Array.isArray(value)) return value.every(finiteJson);
  return object(value) && Object.values(value).every(finiteJson);
}

function equal(left: unknown, right: unknown): boolean {
  if (typeof left !== typeof right) return false;
  if (Array.isArray(left))
    return (
      Array.isArray(right) &&
      left.length === right.length &&
      left.every((v, i) => equal(v, right[i]))
    );
  if (object(left))
    return (
      object(right) &&
      Object.keys(left).length === Object.keys(right).length &&
      Object.keys(left).every(
        (k) => Object.hasOwn(right, k) && equal(left[k], right[k]),
      )
    );
  return left === right;
}

function typeMatches(value: unknown, type: string): boolean {
  switch (type) {
    case "null":
      return value === null;
    case "boolean":
      return typeof value === "boolean";
    case "string":
      return typeof value === "string";
    case "number":
      return typeof value === "number" && Number.isFinite(value);
    case "integer":
      return typeof value === "number" && Number.isInteger(value);
    case "array":
      return Array.isArray(value);
    case "object":
      return object(value);
    default:
      throw Error("Unsupported memory schema type: " + type);
  }
}

function matches(value: unknown, schema: Schema): boolean {
  // Composition checks accumulate: neither a $ref nor a matching oneOf may
  // erase sibling constraints. References never fetch external resources.
  if (schema.$ref) {
    if (!schema.$ref.startsWith("#/$defs/"))
      throw Error("Only local memory schema references are supported");
    const referenced = definitions[schema.$ref.slice(8)];
    if (!referenced) throw Error("Unknown memory schema definition");
    if (!matches(value, referenced)) return false;
  }
  if (
    schema.oneOf &&
    schema.oneOf.filter((branch) => matches(value, branch)).length !== 1
  )
    return false;
  const types = typeof schema.type === "string" ? [schema.type] : schema.type;
  if (types && !types.some((type) => typeMatches(value, type))) return false;
  if (Object.hasOwn(schema, "const") && !equal(value, schema.const))
    return false;
  if (schema.enum && !schema.enum.some((item) => equal(value, item)))
    return false;
  // Count Unicode code points like Python len(), not UTF-16 code units.
  if (
    typeof value === "string" &&
    Array.from(value).length < (schema.minLength ?? 0)
  )
    return false;
  if (Array.isArray(value)) {
    if (value.length < (schema.minItems ?? 0)) return false;
    if (schema.items && !value.every((item) => matches(item, schema.items!)))
      return false;
  }
  if (object(value)) {
    if (schema.required?.some((key) => !Object.hasOwn(value, key)))
      return false;
    for (const [key, item] of Object.entries(value)) {
      if (schema.properties && Object.hasOwn(schema.properties, key)) {
        if (!matches(item, schema.properties[key])) return false;
      } else if (schema.additionalProperties === false) return false;
      else if (
        object(schema.additionalProperties) &&
        !matches(item, schema.additionalProperties as Schema)
      )
        return false;
    }
  }
  return true;
}

/** A definition name is explicit: drafts and persisted records differ. */
export function validateMemoryShape(
  value: unknown,
  definition: string,
): boolean {
  if (!Object.hasOwn(definitions, definition))
    throw Error("Unknown memory schema definition: " + definition);
  return finiteJson(value) && matches(value, definitions[definition]);
}
