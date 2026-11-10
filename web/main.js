const EXAMPLES = {
  departments: `[
  {"id": 1, "department": "Support"},
  {"id": 2, "department": ""}
]`,
  jobs: `[
  {"id": 1, "job": "Analyst"},
  {"id": 2, "job": ""}
]`,
  hired_employees: `[
  {
    "id": "6",
    "name": " Ada Example ",
    "datetime": "2021-01-15T00:00:00Z",
    "department_id": "1",
    "job_id": 2
  }
]`,
};

const FILES = [
  "runtime.py",
  "fastavro/__init__.py",
  "app/__init__.py",
  "app/analytics.py",
  "app/avro_io.py",
  "app/database.py",
  "app/repository.py",
  "app/settings.py",
  "app/validation.py",
  "scripts/load_historical.py",
  "data/departments.csv",
  "data/jobs.csv",
  "data/hired_employees.csv",
];

const DIAGRAM = `flowchart TD
  csv["data/*.csv headerless"] --> loader["scripts/load_historical.py"]
  client["HTTP client"] --> api["FastAPI app.main:app"]
  loader --> ingest["repository.insert_records"]
  api --> ingest
  ingest --> rules["validation.validate_record"]
  rules -->|valid row| db["SQLite ingestion.db"]
  rules -->|rejected row| side["invalid_records table and invalid_records.jsonl"]
  db --> backup["POST /backup/{table}"]
  backup --> avro["backups/{table}_{timestamp}.avro"]
  avro --> restore["POST /restore/{table}"]
  restore --> ingest
  db --> reports["GET /analytics/hires-by-quarter and /analytics/departments-above-average"]`;

const I18N = {
  es: {
    skip: "Saltar al validador",
    tag: "CSV a SQLite, fila por fila, respaldo AVRO",
    repo: "Repositorio",
    "lang-label": "Idioma",
    title: "Validar el lote",
    "lede-1": "Pyodide ejecuta",
    "lede-2": "de este repositorio y muestra el cuerpo de",
    request: "Solicitud",
    "table-label": "Tabla",
    "examples-label": "Ejemplos",
    "example-hint":
      "Cada botón escribe el ejemplo de esa tabla y lo valida. hired_employees depende de los padres que ya estén en la sesión.",
    "body-label": "Cuerpo JSON",
    "file-label": "Subir JSON o CSV sin cabecera",
    "file-button": "Elegir archivo",
    "file-hint":
      "Un JSON sale como un solo POST. Un CSV lo lee scripts/load_historical.py y lo parte en lotes de 1000.",
    validate: "Validar el lote",
    download: "Descargar el AVRO de la tabla",
    reset: "Vaciar la sesión",
    response: "Respuesta",
    "measure-title": "Medición de los CSV",
    "measure-copy":
      "El botón vacía la sesión, carga data/departments.csv, data/jobs.csv y data/hired_employees.csv en ese orden, y ejecuta hires_by_quarter y departments_above_average. tests/test_sample_data.py fija la medición del 2026-10-30. Esta sección la vuelve a calcular.",
    sample: "Cargar los CSV de data/ y medir los reportes",
    "rules-title": "Reglas de validate_record",
    "rules-caption": "Reglas por tabla",
    "rule-1":
      "Un campo es obligatorio cuando la clave falta, el valor es null o el valor es una cadena vacía. Si alguno falla, esa fila no pasa por las comprobaciones de tipo ni de clave foránea.",
    "rule-2":
      'id admite un entero de JSON, también 0 y los negativos, o un texto de dígitos con espacios alrededor, como "42" o " 7 ". Un booleano, un decimal, "-2" y "+2" se rechazan.',
    "rule-3":
      "El texto se recorta. Una cadena en blanco no se trata como ausente. Falla con must be a non-empty string.",
    "rule-4":
      "datetime se recorta y tiene que coincidir con YYYY-MM-DDTHH:MM:SSZ. Si la forma es correcta y el calendario no existe, el mensaje del parser detiene las claves foráneas de esa fila. Un ejemplo es day is out of range for month.",
    "rule-5":
      "En hired_employees, department_id y job_id tienen que existir ya en la sesión. Un id repetido hace INSERT OR REPLACE y la fila cuenta como insertada.",
    "rule-6":
      'La lista trae de 1 a 1000 objetos. Un nombre de tabla distinto de departments, jobs y hired_employees devuelve 404 y el cuerpo {"detail": "Unknown table"}.',
    "col-table": "Tabla",
    "col-rules": "Después del campo obligatorio",
    "rule-dept": "id entero, department texto no vacío",
    "rule-jobs": "id entero, job texto no vacío",
    "rule-hires":
      "id entero, name texto, datetime con esa forma, department_id y job_id enteros que ya existan",
    "arch-title": "Arquitectura",
    "arch-copy":
      "El servicio local sigue este recorrido. En esta página el navegador llama a insert_records y a backup_table.",
    "diagram-source": "Fuente Mermaid",
    "limits-title": "Límites de esta página",
    "limit-1":
      "La página es estática. La validación corre en Pyodide 0.27.7 (CPython 3.12) con los módulos de este sitio.",
    "limit-2":
      "Pyodide y Mermaid se descargan de jsDelivr. app/validation.py, app/repository.py, app/avro_io.py y app/analytics.py salen de este sitio.",
    "limit-3":
      "Pyodide no instala la rueda de fastavro 1.10.0 porque trae extensión en C. backup_table usa web/avro_container.py, montado como fastavro, con los esquemas de app/avro_io.py. tests/test_avro_container.py comprueba que fastavro.reader lee esos bytes. La API local sigue usando fastavro.",
    "limit-4": "La SQLite vive en el sistema de archivos de Pyodide. Recargar la página la borra.",
    "limit-5": "path en la respuesta de backup es esa ruta interna. El botón guarda los mismos bytes.",
    "limit-6":
      "Un JSON de más de 1000 filas devuelve 422. Un CSV largo se parte en lotes de 1000, como el cargador.",
    "limit-7":
      "No hay autenticación, igual que el servicio. El backup abre la tabla entera, ordenada por id.",
    "limit-8": "Los CSV de data/ son la muestra del repositorio. No son un extracto real de personal.",
    "colophon-font":
      "IBM Plex Sans, dibujada por Mike Abbink y Bold Monday para la interfaz y la documentación técnica de IBM. Aguanta tablas densas y nombres de campo largos. IBM Plex Mono solo en JSON, SQL y rutas. Licencia OFL.",
    "colophon-color":
      "El azul #1f4e79 es el de la segunda hoja de un formulario de copia, la que se archivaba. El AVRO es esa copia de la tabla.",
    loading: "Cargando Pyodide y los módulos del repositorio.",
    ready: "Pyodide {v}. Validación importada de app/validation.py.",
    "boot-fail": "No se pudo arrancar el entorno. Hace falta red para Pyodide en jsDelivr.",
    measuring: "Cargando los tres CSV y ejecutando las consultas.",
    measured: "Medición hecha sobre la SQLite de esta sesión.",
    "reset-done": "La sesión está vacía.",
    session: "En la sesión: {d} departments, {j} jobs, {h} hired_employees.",
    batches: "{n} lotes. Cada cuerpo es un POST /ingest de hasta 1000 filas.",
    "empty-csv": "El CSV no tiene filas. El cargador no llama a insert_records.",
    "script-prints": "scripts/load_historical.py imprime este resumen, sin el detalle de cada fila.",
    jsonl: "Líneas añadidas a invalid_records.jsonl",
    "backup-meta":
      "{size} bytes en {filename}. path es la ruta dentro de Pyodide. El archivo descargado son esos bytes.",
    "runtime-error": "El runtime de Python se detuvo.",
    "quarter-sum":
      "GET /analytics/hires-by-quarter devolvió {n} filas. Los totales de abajo suman esas filas.",
    "quarter-filter": "Filtrar por departamento o puesto",
    prev: "Anterior",
    next: "Siguiente",
    page: "Filas {a} a {b} de {n}",
    yes: "sí",
    "dept-title": "Contrataciones de 2021 por departamento",
    "reasons-title": "Conteos en invalid_records",
    "other-years":
      "Las contrataciones de otros años siguen en la tabla y quedan fuera de los dos reportes.",
    "above-note":
      "Un departamento entra en esa lista cuando hired es mayor que el AVG. Un valor igual a la media queda fuera.",
    "no-quarters": "La consulta de trimestres no devolvió filas.",
    mean: "AVG de SQLite sobre los {n} departamentos, incluidos los que tienen cero contrataciones en 2021: {mean}. El reporte trimestral suma {hired} contrataciones de 2021.",
    years: "Años guardados en hired_employees.",
    "rows-col": "filas",
    "endpoint-col": "En el endpoint",
  },
  en: {
    skip: "Skip to the validator",
    tag: "CSV into SQLite, one row at a time, AVRO backup",
    repo: "Repository",
    "lang-label": "Language",
    title: "Validate the batch",
    "lede-1": "Pyodide runs",
    "lede-2": "from this repository and shows the body of",
    request: "Request",
    "table-label": "Table",
    "examples-label": "Examples",
    "example-hint":
      "Each button writes that table's example and validates it. hired_employees depends on the parent rows already in the session.",
    "body-label": "JSON body",
    "file-label": "Upload a headerless JSON or CSV file",
    "file-button": "Choose a file",
    "file-hint":
      "A JSON file is one POST. A CSV file is read by scripts/load_historical.py and split into batches of 1000.",
    validate: "Validate the batch",
    download: "Download the table AVRO",
    reset: "Clear the session",
    response: "Response",
    "measure-title": "CSV measurement",
    "measure-copy":
      "The button clears the session, loads data/departments.csv, data/jobs.csv, and data/hired_employees.csv in that order, then runs hires_by_quarter and departments_above_average. tests/test_sample_data.py locks the 2026-10-30 measurement. This section calculates it again.",
    sample: "Load the data/ CSVs and measure the reports",
    "rules-title": "Rules in validate_record",
    "rules-caption": "Rules by table",
    "rule-1":
      "A field is required when the key is missing, the value is null, or the value is an empty string. If any required field fails, that row skips the type checks and the foreign key checks.",
    "rule-2":
      'id accepts a JSON integer, including 0 and negatives, or a digit string with surrounding spaces, such as "42" or " 7 ". A boolean, a decimal, "-2", and "+2" are rejected.',
    "rule-3":
      "Text is stripped. A whitespace-only string is not treated as missing. It fails with must be a non-empty string.",
    "rule-4":
      "datetime is stripped and must match YYYY-MM-DDTHH:MM:SSZ. When the shape matches and the calendar date does not exist, the parser message stops the foreign key checks for that row. One example is day is out of range for month.",
    "rule-5":
      "For hired_employees, department_id and job_id must already exist in the session. A repeated id does INSERT OR REPLACE and the row still counts as inserted.",
    "rule-6":
      'The list holds 1 to 1000 objects. A table name other than departments, jobs, or hired_employees returns 404 and the body {"detail": "Unknown table"}.',
    "col-table": "Table",
    "col-rules": "After the required-field check",
    "rule-dept": "integer id, non-empty department text",
    "rule-jobs": "integer id, non-empty job text",
    "rule-hires":
      "integer id, name text, datetime in that shape, department_id and job_id integers that already exist",
    "arch-title": "Architecture",
    "arch-copy":
      "The local service follows this path. On this page the browser calls insert_records and backup_table.",
    "diagram-source": "Mermaid source",
    "limits-title": "Limits of this page",
    "limit-1":
      "The page is static. Validation runs in Pyodide 0.27.7 (CPython 3.12) with the modules from this site.",
    "limit-2":
      "Pyodide and Mermaid download from jsDelivr. app/validation.py, app/repository.py, app/avro_io.py, and app/analytics.py come from this site.",
    "limit-3":
      "Pyodide does not install the fastavro 1.10.0 wheel because it ships a C extension. backup_table uses web/avro_container.py, mounted as fastavro, with the schemas in app/avro_io.py. tests/test_avro_container.py checks that fastavro.reader can read those bytes. The local API still uses fastavro.",
    "limit-4": "SQLite lives in the Pyodide filesystem. Reloading the page drops it.",
    "limit-5": "path in the backup response is that internal path. The button saves those same bytes.",
    "limit-6":
      "A JSON body longer than 1000 rows returns 422. A long CSV is split into batches of 1000, as the loader does.",
    "limit-7":
      "There is no authentication, same as the service. Backup reads the whole table, ordered by id.",
    "limit-8": "The CSVs in data/ are the repository sample. They are not a real personnel extract.",
    "colophon-font":
      "IBM Plex Sans, drawn by Mike Abbink with Bold Monday for IBM product UI and technical documentation. It holds dense tables and long field names. IBM Plex Mono is used only for JSON, SQL, and paths. OFL license.",
    "colophon-color":
      "Blue #1f4e79 is the blue of the file copy on a multipart form, the sheet that was kept. The AVRO file is that copy of the table.",
    loading: "Loading Pyodide and the repository modules.",
    ready: "Pyodide {v}. Validation imported from app/validation.py.",
    "boot-fail": "The environment did not start. Pyodide on jsDelivr needs a network.",
    measuring: "Loading the three CSVs and running the queries.",
    measured: "Measurement taken on this session's SQLite.",
    "reset-done": "The session is empty.",
    session: "In the session: {d} departments, {j} jobs, {h} hired_employees.",
    batches: "{n} batches. Each body is one POST /ingest of at most 1000 rows.",
    "empty-csv": "The CSV has no rows. The loader does not call insert_records.",
    "script-prints": "scripts/load_historical.py prints this summary, without each row's errors.",
    jsonl: "Lines appended to invalid_records.jsonl",
    "backup-meta":
      "{size} bytes in {filename}. path is the path inside Pyodide. The download is those bytes.",
    "runtime-error": "The Python runtime stopped.",
    "quarter-sum":
      "GET /analytics/hires-by-quarter returned {n} rows. The totals below add those rows.",
    "quarter-filter": "Filter by department or job",
    prev: "Previous",
    next: "Next",
    page: "Rows {a} to {b} of {n}",
    yes: "yes",
    "dept-title": "2021 hires by department",
    "reasons-title": "Counts in invalid_records",
    "other-years": "Hires from other years stay in the table and stay out of both reports.",
    "above-note":
      "A department is in that list when hired is greater than the AVG. A value equal to the mean stays out.",
    "no-quarters": "The quarter query returned no rows.",
    mean: "SQLite AVG over {n} departments, including departments with zero hires in 2021: {mean}. The quarter report sums to {hired} hires in 2021.",
    years: "Years stored in hired_employees.",
    "rows-col": "rows",
    "endpoint-col": "In the endpoint",
  },
};

const PAGE_SIZE = 20;
const CONTROLS = ["validate", "download", "reset", "sample", "file"];

let lang = "es";
let pyodide = null;
let pyodideVersion = "";
let ready = false;
let busy = false;
let statusBuilder = () => t("loading");
let lastIngest = null;
let lastBackup = null;
let lastMeasure = null;
let quarterQuery = "";
let quarterPage = 0;

try {
  const saved = localStorage.getItem("lang");
  if (saved === "en" || saved === "es") lang = saved;
} catch (_error) {
  lang = "es";
}

function t(key) {
  const pack = I18N[lang] || I18N.es;
  return pack[key] ?? I18N.es[key] ?? key;
}

function setStatus(builder) {
  statusBuilder = builder;
  document.getElementById("status").textContent = builder();
}

function applyLanguage(next) {
  lang = next;
  document.documentElement.lang = lang;
  document.title = t("title");
  document.getElementById("lang-es").setAttribute("aria-pressed", String(lang === "es"));
  document.getElementById("lang-en").setAttribute("aria-pressed", String(lang === "en"));
  for (const el of document.querySelectorAll("[data-i18n]")) {
    el.textContent = t(el.dataset.i18n);
  }
  for (const el of document.querySelectorAll("[data-i18n-aria]")) {
    el.setAttribute("aria-label", t(el.dataset.i18nAria));
  }
  try {
    localStorage.setItem("lang", lang);
  } catch (_error) {
    /* private mode */
  }
  refreshRoute();
  refreshRuntimeLine();
  document.getElementById("status").textContent = statusBuilder();
  if (lastIngest) renderIngest(lastIngest, false);
  if (lastBackup) renderBackup(lastBackup);
  if (lastMeasure) renderMeasure(lastMeasure, false);
  if (ready) refreshSession();
}

function refreshRuntimeLine() {
  const line = document.getElementById("runtime-line");
  line.textContent = pyodideVersion ? t("ready").replace("{v}", pyodideVersion) : "";
}

function tableName() {
  return document.getElementById("table-name").value.trim();
}

function refreshRoute() {
  const name = tableName() || "{tabla}";
  document.getElementById("route").textContent = `POST /ingest/${name}`;
}

function setBusy(value) {
  busy = value;
  document.getElementById("banco").setAttribute("aria-busy", value ? "true" : "false");
  for (const id of CONTROLS) {
    document.getElementById(id).disabled = value || !ready;
  }
}

function clearCounts() {
  for (const id of ["n-received", "n-inserted", "n-rejected"]) {
    const el = document.getElementById(id);
    el.dataset.value = "";
    el.textContent = "";
  }
}

function setCount(id, value) {
  const el = document.getElementById(id);
  el.dataset.value = String(value);
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) {
    el.textContent = String(value);
    return;
  }
  const start = performance.now();
  function frame(now) {
    if (el.dataset.value !== String(value)) return;
    const progress = Math.min(1, (now - start) / 420);
    const eased = 1 - (1 - progress) ** 3;
    el.textContent = String(Math.round(value * eased));
    if (progress < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

function setCounts(body) {
  if (!body || typeof body.received !== "number") {
    clearCounts();
    return;
  }
  setCount("n-received", body.received);
  setCount("n-inserted", body.inserted);
  setCount("n-rejected", body.rejected);
}

function detailText(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join(" ");
  return "";
}

function httpStatus(payload) {
  let text = `HTTP ${payload.status}`;
  if (payload.status === 200 && payload.body && typeof payload.body.received === "number") {
    text += `. received ${payload.body.received}, inserted ${payload.body.inserted}, rejected ${payload.body.rejected}`;
  } else if (payload.body && payload.body.detail) {
    const detail = detailText(payload.body.detail);
    if (detail) text += `. ${detail}`;
  }
  return text;
}

function appendJsonl(extra, lines) {
  if (!lines || !lines.length) return;
  const label = document.createElement("p");
  label.textContent = t("jsonl");
  const pre = document.createElement("pre");
  pre.textContent = lines.join("\n");
  extra.append(label, pre);
}

function renderIngest(payload, fromUser) {
  lastIngest = payload;
  const httpLine = document.getElementById("http-line");
  const httpBody = document.getElementById("http-body");
  const extra = document.getElementById("extra");
  extra.replaceChildren();
  if (payload.mode === "loader") {
    const batches = payload.batches || [];
    if (batches.length === 1) {
      httpLine.textContent = `HTTP ${batches[0].status}`;
      httpBody.hidden = false;
      httpBody.textContent = batches[0].body_text;
      setStatus(() => httpStatus({ status: batches[0].status, body: batches[0].body }));
    } else if (batches.length === 0) {
      httpLine.textContent = t("empty-csv");
      httpBody.hidden = false;
      httpBody.textContent = payload.summary_text;
      setStatus(() => t("empty-csv"));
    } else {
      httpLine.textContent = t("batches").replace("{n}", String(batches.length));
      httpBody.hidden = true;
      httpBody.textContent = "";
      for (const batch of batches) {
        const label = document.createElement("p");
        label.textContent = `HTTP ${batch.status}  row_offset ${batch.row_offset}`;
        const pre = document.createElement("pre");
        pre.textContent = batch.body_text;
        extra.append(label, pre);
      }
      setStatus(() => t("batches").replace("{n}", String(batches.length)));
    }
    const scriptLabel = document.createElement("p");
    scriptLabel.className = "hint";
    scriptLabel.textContent = t("script-prints");
    const summary = document.createElement("pre");
    summary.textContent = payload.summary_text;
    extra.append(scriptLabel, summary);
    appendJsonl(extra, payload.jsonl);
    setCounts(payload.summary);
  } else {
    httpLine.textContent = `HTTP ${payload.status}`;
    httpBody.hidden = false;
    httpBody.textContent = payload.body_text;
    appendJsonl(extra, payload.jsonl);
    setCounts(payload.body);
    setStatus(() => httpStatus(payload));
  }
  if (fromUser && window.matchMedia("(max-width: 720px)").matches) {
    document.getElementById("response").scrollIntoView({ block: "start" });
  }
}

function renderBackup(payload) {
  lastBackup = payload;
  const block = document.getElementById("backup-block");
  block.hidden = false;
  document.getElementById("backup-route").textContent = `POST /backup/${tableName()}`;
  document.getElementById("backup-body").textContent = payload.body_text;
  const meta = document.getElementById("backup-meta");
  if (payload.status === 200) {
    meta.textContent = t("backup-meta")
      .replace("{size}", String(payload.size))
      .replace("{filename}", payload.filename);
  } else {
    meta.textContent = "";
  }
}

function heading(text) {
  const node = document.createElement("h3");
  node.textContent = text;
  return node;
}

function dataTable(headers, rows) {
  const wrap = document.createElement("div");
  wrap.className = "table-wrap";
  const table = document.createElement("table");
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const header of headers) {
    const cell = document.createElement("th");
    cell.textContent = header.label;
    if (header.num) cell.className = "num";
    headRow.append(cell);
  }
  head.append(headRow);
  const body = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const header of headers) {
      const cell = document.createElement("td");
      cell.textContent = header.cell(row);
      if (header.num) cell.className = "num";
      tr.append(cell);
    }
    body.append(tr);
  }
  table.append(head, body);
  wrap.append(table);
  return wrap;
}

function renderMeasure(payload, resetView) {
  if (resetView) {
    quarterQuery = "";
    quarterPage = 0;
  }
  lastMeasure = payload;
  const measurement = payload.measurement;
  const root = document.getElementById("measure");
  const hadFocus = document.activeElement && document.activeElement.id === "quarter-filter";
  const caret = hadFocus ? document.activeElement.selectionStart : null;
  root.replaceChildren();

  root.append(heading("scripts/load_historical.py"));
  const summary = document.createElement("pre");
  summary.textContent = payload.summaries_text;
  root.append(summary);

  if (measurement.years.length) {
    const years = document.createElement("p");
    const bits = measurement.years.map((row) => `${row.year}: ${row.hired}`).join(". ");
    years.textContent = `${t("years")} ${bits}.`;
    root.append(years);
    const other = document.createElement("p");
    other.textContent = t("other-years");
    root.append(other);
  }

  const reasons = Object.entries(measurement.rejection_reasons).sort(
    (left, right) => right[1] - left[1] || left[0].localeCompare(right[0]),
  );
  if (reasons.length) {
    root.append(heading(t("reasons-title")));
    root.append(
      dataTable(
        [
          { label: "errors", cell: (row) => row[0] },
          { label: t("rows-col"), num: true, cell: (row) => String(row[1]) },
        ],
        reasons,
      ),
    );
  }

  const endpoint = document.createElement("p");
  const endpointCode = document.createElement("code");
  endpointCode.textContent = "GET /analytics/departments-above-average";
  endpoint.append(endpointCode);
  root.append(endpoint);
  const aboveNote = document.createElement("p");
  aboveNote.textContent = t("above-note");
  root.append(aboveNote);
  if (measurement.mean_2021 !== null) {
    const mean = document.createElement("p");
    mean.textContent = t("mean")
      .replace("{n}", String(measurement.department_count))
      .replace("{mean}", String(measurement.mean_2021))
      .replace("{hired}", String(measurement.hired_2021));
    root.append(mean);
  }
  const abovePre = document.createElement("pre");
  abovePre.textContent = measurement.above_text;
  root.append(abovePre);

  if (measurement.department_hires.length) {
    root.append(heading(t("dept-title")));
    const aboveIds = new Set(measurement.above.map((row) => row.id));
    root.append(
      dataTable(
        [
          { label: "id", num: true, cell: (row) => String(row.id) },
          { label: "department", cell: (row) => row.department },
          { label: "hired", num: true, cell: (row) => String(row.hired) },
          { label: t("endpoint-col"), cell: (row) => (aboveIds.has(row.id) ? t("yes") : "") },
        ],
        measurement.department_hires,
      ),
    );
  }

  const quarterLabel = document.createElement("p");
  const quarterCode = document.createElement("code");
  quarterCode.textContent = "GET /analytics/hires-by-quarter";
  quarterLabel.append(quarterCode);
  root.append(quarterLabel);
  const quarterNote = document.createElement("p");
  quarterNote.textContent = t("quarter-sum").replace("{n}", String(measurement.quarter_groups));
  root.append(quarterNote);
  if (!measurement.quarters.length) {
    const empty = document.createElement("p");
    empty.textContent = t("no-quarters");
    root.append(empty);
    return;
  }
  const totals = document.createElement("div");
  totals.className = "totals";
  let quarterSum = 0;
  for (const quarter of ["Q1", "Q2", "Q3", "Q4"]) {
    const block = document.createElement("div");
    const name = document.createElement("p");
    name.className = "q";
    name.textContent = quarter;
    const value = document.createElement("p");
    value.className = "q-n";
    value.textContent = String(measurement.quarter_totals[quarter]);
    quarterSum += measurement.quarter_totals[quarter];
    block.append(name, value);
    totals.append(block);
  }
  root.append(totals);
  const sumLine = document.createElement("p");
  sumLine.textContent = `Q1 + Q2 + Q3 + Q4 = ${quarterSum}`;
  root.append(sumLine);

  const filter = document.createElement("input");
  filter.id = "quarter-filter";
  filter.type = "text";
  filter.value = quarterQuery;
  filter.spellcheck = false;
  filter.setAttribute("aria-label", t("quarter-filter"));
  filter.placeholder = t("quarter-filter");
  filter.addEventListener("input", () => {
    quarterQuery = filter.value;
    quarterPage = 0;
    renderMeasure(lastMeasure, false);
  });
  root.append(filter);

  const query = quarterQuery.trim().toLowerCase();
  const filtered = measurement.quarters.filter((row) => {
    if (!query) return true;
    return (
      row.department.toLowerCase().includes(query) || row.job.toLowerCase().includes(query)
    );
  });
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  if (quarterPage >= pages) quarterPage = pages - 1;
  if (quarterPage < 0) quarterPage = 0;
  const start = quarterPage * PAGE_SIZE;
  const slice = filtered.slice(start, start + PAGE_SIZE);
  root.append(
    dataTable(
      [
        { label: "department", cell: (row) => row.department },
        { label: "job", cell: (row) => row.job },
        { label: "Q1", num: true, cell: (row) => String(row.Q1) },
        { label: "Q2", num: true, cell: (row) => String(row.Q2) },
        { label: "Q3", num: true, cell: (row) => String(row.Q3) },
        { label: "Q4", num: true, cell: (row) => String(row.Q4) },
      ],
      slice,
    ),
  );
  const pager = document.createElement("div");
  pager.className = "pager";
  const prev = document.createElement("button");
  prev.type = "button";
  prev.className = "secondary";
  prev.textContent = t("prev");
  prev.disabled = quarterPage === 0;
  prev.addEventListener("click", () => {
    quarterPage -= 1;
    renderMeasure(lastMeasure, false);
  });
  const next = document.createElement("button");
  next.type = "button";
  next.className = "secondary";
  next.textContent = t("next");
  next.disabled = quarterPage >= pages - 1;
  next.addEventListener("click", () => {
    quarterPage += 1;
    renderMeasure(lastMeasure, false);
  });
  const label = document.createElement("span");
  const end = filtered.length === 0 ? 0 : Math.min(filtered.length, start + PAGE_SIZE);
  label.textContent = t("page")
    .replace("{a}", String(filtered.length === 0 ? 0 : start + 1))
    .replace("{b}", String(end))
    .replace("{n}", String(filtered.length));
  pager.append(prev, next, label);
  root.append(pager);
  if (hadFocus) {
    const again = document.getElementById("quarter-filter");
    again.focus();
    if (caret !== null) again.setSelectionRange(caret, caret);
  }
}

function python(source) {
  return pyodide.runPython(source);
}

async function guard(fn) {
  if (!ready || busy) return;
  setBusy(true);
  try {
    await fn();
  } catch (error) {
    const message = String(error);
    setStatus(() => `${t("runtime-error")} ${message}`);
    document.getElementById("http-body").hidden = false;
    document.getElementById("http-body").textContent = message;
  } finally {
    setBusy(false);
  }
}

async function runIngest(raw, fromUser) {
  await guard(async () => {
    pyodide.globals.set("table_name", tableName());
    pyodide.globals.set("raw_body", raw);
    const payload = JSON.parse(python("runtime.ingest_text(table_name, raw_body)"));
    renderIngest(payload, fromUser);
    refreshSession();
  });
}

async function runCsv(raw) {
  await guard(async () => {
    pyodide.globals.set("table_name", tableName());
    pyodide.globals.set("raw_body", raw);
    const payload = JSON.parse(python("runtime.ingest_csv_text(table_name, raw_body)"));
    renderIngest(payload, true);
    refreshSession();
  });
}

function refreshSession() {
  if (!ready) return;
  const counts = JSON.parse(python("runtime.session_counts()"));
  document.getElementById("session-line").textContent = t("session")
    .replace("{d}", String(counts.departments))
    .replace("{j}", String(counts.jobs))
    .replace("{h}", String(counts.hired_employees));
}

function saveBase64(b64, filename) {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  const url = URL.createObjectURL(new Blob([bytes], { type: "application/octet-stream" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function mkdirp(path) {
  const parts = path.split("/").filter(Boolean);
  let current = "";
  for (const part of parts) {
    current += `/${part}`;
    try {
      pyodide.FS.mkdir(current);
    } catch (_error) {
      /* already created */
    }
  }
}

async function mount(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path} HTTP ${response.status}`);
  const bytes = new Uint8Array(await response.arrayBuffer());
  const full = `/work/${path}`;
  mkdirp(full.slice(0, full.lastIndexOf("/")));
  pyodide.FS.writeFile(full, bytes);
}

function loadDiagram() {
  document.getElementById("diagram-source").textContent = DIAGRAM;
  const script = document.createElement("script");
  script.src = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js";
  script.onload = async () => {
    window.mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme: "base",
      fontFamily: '"IBM Plex Sans", sans-serif',
      themeVariables: {
        fontFamily: '"IBM Plex Sans", sans-serif',
        primaryColor: "#f6f8fa",
        primaryTextColor: "#15202b",
        primaryBorderColor: "#1f4e79",
        lineColor: "#1f4e79",
        secondaryColor: "#e6edf3",
        tertiaryColor: "#f6f8fa",
        background: "#f6f8fa",
        mainBkg: "#f6f8fa",
        nodeBorder: "#1f4e79",
        clusterBkg: "#f6f8fa",
        titleColor: "#15202b",
        edgeLabelBackground: "#f6f8fa",
        nodeTextColor: "#15202b",
      },
    });
    try {
      const rendered = await window.mermaid.render("architecture", DIAGRAM);
      document.getElementById("diagram").innerHTML = rendered.svg;
    } catch (error) {
      document.getElementById("diagram").textContent = String(error);
    }
  };
  document.head.append(script);
}

async function boot() {
  applyLanguage(lang);
  loadDiagram();
  setStatus(() => t("loading"));
  try {
    pyodide = await window.loadPyodide({
      indexURL: "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/",
    });
    try {
      await pyodide.runPythonAsync("import sqlite3");
    } catch (_error) {
      await pyodide.loadPackage("sqlite3");
    }
    for (const file of FILES) {
      await mount(file);
    }
    await pyodide.runPythonAsync(`
import sys
sys.path.insert(0, "/work")
import runtime
runtime.ensure_db()
`);
    ready = true;
    setBusy(false);
    pyodideVersion = pyodide.version;
    refreshRuntimeLine();
    document.getElementById("body").value = EXAMPLES.departments;
    document.getElementById("table-name").value = "departments";
    refreshRoute();
    await runIngest(EXAMPLES.departments, false);
    document.body.dataset.ready = "true";
  } catch (error) {
    document.body.dataset.ready = "error";
    const message = String(error);
    setStatus(() => `${t("boot-fail")} ${message}`);
  }
}

document.getElementById("lang-es").addEventListener("click", () => applyLanguage("es"));
document.getElementById("lang-en").addEventListener("click", () => applyLanguage("en"));
document.getElementById("table-name").addEventListener("input", refreshRoute);
document.getElementById("request-form").addEventListener("submit", (event) => {
  event.preventDefault();
  runIngest(document.getElementById("body").value, true);
});
for (const button of document.querySelectorAll("[data-example]")) {
  button.addEventListener("click", () => {
    const name = button.dataset.example;
    document.getElementById("table-name").value = name;
    document.getElementById("body").value = EXAMPLES[name];
    refreshRoute();
    if (ready) runIngest(EXAMPLES[name], true);
  });
}
document.getElementById("file").addEventListener("change", () => {
  const input = document.getElementById("file");
  const file = input.files && input.files[0];
  document.getElementById("file-name").textContent = file ? file.name : "";
  if (!file || !ready) return;
  const reader = new FileReader();
  reader.onload = () => {
    const text = String(reader.result);
    if (file.name.toLowerCase().endsWith(".csv")) {
      runCsv(text);
    } else {
      document.getElementById("body").value = text;
      runIngest(text, true);
    }
  };
  reader.readAsText(file, "UTF-8");
});
document.getElementById("download").addEventListener("click", () => {
  guard(async () => {
    pyodide.globals.set("table_name", tableName());
    const payload = JSON.parse(python("runtime.backup(table_name)"));
    renderBackup(payload);
    if (payload.status === 200) saveBase64(payload.avro_b64, payload.filename);
  });
});
document.getElementById("reset").addEventListener("click", () => {
  guard(async () => {
    python("runtime.reset_session()");
    lastIngest = null;
    lastBackup = null;
    lastMeasure = null;
    clearCounts();
    document.getElementById("http-line").textContent = "";
    document.getElementById("http-body").textContent = "";
    document.getElementById("extra").replaceChildren();
    document.getElementById("backup-block").hidden = true;
    document.getElementById("measure").replaceChildren();
    refreshSession();
    setStatus(() => t("reset-done"));
  });
});
document.getElementById("sample").addEventListener("click", () => {
  guard(async () => {
    setStatus(() => t("measuring"));
    await new Promise((resolve) => setTimeout(resolve, 30));
    const payload = JSON.parse(python("runtime.load_sample()"));
    lastIngest = null;
    lastBackup = null;
    clearCounts();
    document.getElementById("http-line").textContent = "";
    document.getElementById("http-body").textContent = "";
    document.getElementById("extra").replaceChildren();
    document.getElementById("backup-block").hidden = true;
    renderMeasure(payload, true);
    refreshSession();
    setStatus(() => t("measured"));
    document.getElementById("medicion").scrollIntoView({ block: "start" });
  });
});

boot();
