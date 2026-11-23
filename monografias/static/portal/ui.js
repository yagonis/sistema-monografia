export const escape = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const paths = {
  book: "M4 4h6a3 3 0 0 1 3 3v14a4 4 0 0 0-4-3H4zm18 0h-5a4 4 0 0 0-4 3v14a4 4 0 0 1 4-3h5z",
  search: "m21 21-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0",
  grid: "M3 3h7v7H3zm11 0h7v7h-7zM3 14h7v7H3zm11 0h7v7h-7z",
  file: "M14 2H5v20h14V7zm0 0v6h5M8 12h8M8 16h6",
  calendar: "M4 5h16v16H4zM8 2v6m8-6v6M4 11h16",
  chart: "M4 3v18h17M9 16v-5m5 5V6m5 10V9",
  arrow: "M4 12h15m-6-6 6 6-6 6",
  user: "M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0M4 21v-2a8 8 0 0 1 16 0v2",
  download: "M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5",
  plus: "M12 5v14M5 12h14",
  check: "m5 12 4 4L20 5",
  close: "m6 6 12 12M6 18 18 6",
  menu: "M4 6h16M4 12h16M4 18h16",
  logout: "M10 3H4v18h6m4-14 5 5-5 5m-6-5h11",
  chevron: "m9 5 7 7-7 7",
  lock: "M5 10h14v12H5zm3 0V6a4 4 0 0 1 8 0v4",
  users:
    "M16 21v-2a6 6 0 0 0-12 0v2M14 8a4 4 0 1 1-8 0 4 4 0 0 1 8 0m6-4a4 4 0 0 1 0 8m0 3a6 6 0 0 1 2 6",
  info: "M12 11v6m0-10v1M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
  leaf: "M20 3C8 2 1 8 5 16c8 5 16-3 15-13M5 20 16 8",
};
export const icon = (name) =>
  `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[name] || paths.file}"/></svg>`;
export const labels = {
  rascunho: "Rascunho",
  em_avaliacao: "Aguardando orientador",
  aprovada_orientador: "Aprovada pelo orientador",
  aprovada: "Aprovada em defesa",
  ressalvas: "Correções pendentes",
  reprovada: "Reprovada",
  publicada: "Publicada",
  em_preparacao: "Em preparação",
  agendada: "Agendada",
  realizada: "Realizada",
  cancelada: "Cancelada",
};
export const badge = (status) =>
  `<span class="badge ${["publicada", "aprovada", "aprovada_orientador", "realizada"].includes(status) ? "green" : ["rascunho", "em_preparacao"].includes(status) ? "" : ["reprovada", "cancelada"].includes(status) ? "red" : status === "ressalvas" ? "amber" : "blue"}">${escape(labels[status] || status)}</span>`;
export function date(value, time = false) {
  return value
    ? new Intl.DateTimeFormat("pt-BR", {
        dateStyle: "medium",
        ...(time ? { timeStyle: "short" } : {}),
      }).format(new Date(value))
    : "Não informado";
}
export function datetimeLocal(value) {
  if (!value) return "";
  const d = new Date(value);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}
// O primeiro argumento (contexto da seção) fica só no breadcrumb da barra superior;
// repeti-lo como rótulo acima do título não acrescenta informação.
export const heading = (_context, title, subtitle, actions = "") =>
  `<div class="page-heading"><div><h1>${escape(title)}</h1><p>${escape(subtitle)}</p></div>${actions ? `<div class="actions">${actions}</div>` : ""}</div>`;
export const empty = (title, text, action = "") =>
  `<div class="empty"><h3>${escape(title)}</h3><p>${escape(text)}</p>${action}</div>`;
export const button = (text, action, cls = "btn-secondary", attrs = "") =>
  `<button type="button" class="btn ${cls}" data-action="${escape(action)}" ${attrs}>${escape(text)}</button>`;
export const options = (items, value, label, current, blank = "Selecione") =>
  `<option value="">${escape(blank)}</option>` +
  items
    .map(
      (x) =>
        `<option value="${escape(x[value])}" ${String(x[value]) === String(current) ? "selected" : ""}>${escape(label(x))}</option>`,
    )
    .join("");
export const tags = (value) =>
  `<div class="tags">${String(value || "")
    .split(/[,;]/)
    .map((x) => x.trim())
    .filter(Boolean)
    .slice(0, 6)
    .map((x) => `<span class="tag">${escape(x)}</span>`)
    .join("")}</div>`;
export const panel = (title, body, actions = "") =>
  `<section class="panel"><div class="panel-head"><h2>${escape(title)}</h2>${actions}</div>${body}</section>`;
export const details = (rows) =>
  `<dl class="details">${rows.map(([key, val]) => `<div><dt>${escape(key)}</dt><dd>${escape(val)}</dd></div>`).join("")}</dl>`;
export const countLabel = (count, singular, plural) =>
  `${count} ${count === 1 ? singular : plural}`;
