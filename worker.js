// Runs Python (PyMuPDF via Pyodide) off the main thread. Nothing here talks to a server.
import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide.mjs";

const API = `
import io, json, zipfile, pymupdf, editor
from pyodide.ffi import to_js

def _b(buf):
    return buf.to_py().tobytes()

def detect(buf):
    try:
        doc = pymupdf.open(stream=_b(buf), filetype="pdf")
    except Exception:
        return json.dumps({"error": "Not a valid PDF"})
    return json.dumps({"enrollment": editor.detect_enrollment(doc), "pages": len(doc)})

def process(buf, old, new):
    out, n = editor.replace_text(_b(buf), old, new)
    pages = len(pymupdf.open(stream=out, filetype="pdf")) if n else 0
    return json.dumps({"count": n, "pages": pages}), to_js(out)

def proof(buf):
    p = pymupdf.open(stream=_b(buf), filetype="pdf")[0]
    clip = pymupdf.Rect(30, p.rect.height - 62, 330, p.rect.height - 32)
    return to_js(p.get_pixmap(dpi=260, clip=clip).tobytes("png"))

_zip_buf = _zip = None
def zip_start():
    global _zip_buf, _zip
    _zip_buf = io.BytesIO(); _zip = zipfile.ZipFile(_zip_buf, "w", zipfile.ZIP_DEFLATED)

def zip_add(name, buf):
    _zip.writestr(name, _b(buf))

def zip_finish():
    _zip.close()
    return to_js(_zip_buf.getvalue())
`;

let py;
const ready = (async () => {
  postMessage({ type: "status", text: "Loading PDF engine (first visit downloads ~20 MB, then it is cached)…" });
  py = await loadPyodide({ indexURL: "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/" });
  await py.loadPackage("pymupdf");
  py.FS.writeFile("editor.py", await (await fetch("editor.py")).text());
  py.runPython(API);
  postMessage({ type: "ready" });
})().catch(e => postMessage({ type: "status", text: "Could not load the PDF engine — check your internet connection and reload. (" + e.message + ")" }));

onmessage = async ({ data: { id, op, args } }) => {
  try {
    await ready;
    const f = py.globals.get(op);
    const res = f(...args);
    f.destroy();
    let out = res, transfer = [];
    if (res && res.toJs) { out = res.toJs(); res.destroy(); }
    const collect = v => { if (v instanceof Uint8Array) transfer.push(v.buffer); else if (Array.isArray(v)) v.forEach(collect); };
    collect(out);
    postMessage({ id, result: out }, transfer);
  } catch (e) {
    postMessage({ id, error: String(e.message || e) });
  }
};
