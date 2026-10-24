import * as Arrow from "npm:apache-arrow";
import * as Parquet from "npm:parquet-wasm";

// Framework 1.13's FileAttachment.parquet() initialises parquet-wasm with a bare
// URL, which parquet-wasm 0.9 deprecates (it logs "using deprecated parameters
// for the initialization function" on every page). Same decoding, new-style init.
const ready = Parquet.default({module_or_path: import.meta.resolve("npm:parquet-wasm/esm/parquet_wasm_bg.wasm")});

/** Decode a Parquet FileAttachment to an Apache Arrow table. */
export async function parquet(file) {
  const [buffer] = await Promise.all([file.arrayBuffer(), ready]);
  return Arrow.tableFromIPC(Parquet.readParquet(new Uint8Array(buffer)).intoIPCStream());
}
