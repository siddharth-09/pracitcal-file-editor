# PDF Enrollment Editor (static, runs fully in the browser)

PyMuPDF runs inside the browser via Pyodide (WebAssembly) in a Web Worker.
No backend, no uploads, no file-size limit from the host.

Files: `index.html` (UI), `worker.js` (loads Pyodide + PyMuPDF), `editor.py` (the PDF logic).

## Run locally
    python3 -m http.server 5070      # then open http://localhost:5070
(Opening index.html by double-click will NOT work: workers need http://.)

## Deploy to Vercel
1. Push this folder to a GitHub repo (index.html at the repo root), or use the CLI below.
2. vercel.com -> Add New -> Project -> import the repo.
3. Framework Preset: **Other**. Build Command: empty. Output Directory: empty (or `.`). Deploy.

CLI alternative:
    npm i -g vercel
    cd pdf-editor-web && vercel --prod

Needs internet on first visit: the ~20 MB Pyodide/PyMuPDF engine loads from the jsDelivr CDN, then the browser caches it.
