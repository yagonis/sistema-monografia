import assert from "node:assert/strict";
import {
  escape,
  tags,
  badge,
  datetimeLocal,
  countLabel,
} from "../monografias/static/portal/ui.js";
import {
  request,
  all,
  setCsrf,
  errorMessages,
  ApiError,
} from "../monografias/static/portal/api.js";

assert.equal(escape('<script>"&'), "&lt;script&gt;&quot;&amp;");
assert(!tags("<img src=x onerror=alert(1)>").includes("<img"));
assert(badge("publicada").includes("Publicada"));
assert(!badge("<img>").includes("<img>"));
assert.equal(datetimeLocal(null), "");
assert.equal(countLabel(1, "registro", "registros"), "1 registro");
assert.equal(countLabel(70, "registro", "registros"), "70 registros");
assert.equal(countLabel(0, "trabalho", "trabalhos"), "0 trabalhos");
assert.deepEqual(
  errorMessages(
    new ApiError(400, { titulo: ["Obrigatório"], __all__: ["Revisar"] }),
  ),
  ["Título: Obrigatório", "Revisar"],
);
assert(errorMessages(new ApiError(429, {}))[0].includes("limite"));

globalThis.location = { origin: "http://localhost" };
class Multipart {}
globalThis.FormData = Multipart;
let calls = [];
globalThis.fetch = async (path, options) => {
  calls.push({ path, options });
  return {
    ok: true,
    status: 200,
    json: async () => ({ csrfToken: "renovado" }),
  };
};
setCsrf("inicial");
await request("/api/conta/", { method: "POST", body: { login: "teste" } });
assert.equal(calls[0].options.headers["X-CSRFToken"], "inicial");
assert.equal(calls[0].options.credentials, "same-origin");
await request("/api/monografias/", { method: "POST", body: new Multipart() });
assert.equal(calls[1].options.headers["Content-Type"], undefined);
assert.equal(calls[1].options.headers["X-CSRFToken"], "renovado");
await request("/api/externo/", {
  method: "POST",
  token: "temporario",
  body: { acao: "confirmar" },
});
assert.equal(calls[2].options.headers["X-Banca-Token"], "temporario");
assert.equal(calls[2].options.headers["X-CSRFToken"], undefined);
await assert.rejects(
  () => request("https://outro.example/api/"),
  /fora da API/,
);

globalThis.fetch = async () => ({
  ok: false,
  status: 403,
  json: async () => ({ detail: "Acesso negado" }),
});
await assert.rejects(
  () => request("/api/usuarios/"),
  (error) => error instanceof ApiError && error.status === 403,
);
let page = 0;
globalThis.fetch = async () => ({
  ok: true,
  status: 200,
  json: async () =>
    ++page === 1
      ? { results: [{ id: 1 }], next: "http://localhost/api/cursos/?page=2" }
      : { results: [{ id: 2 }], next: null },
});
assert.deepEqual(await all("cursos"), [{ id: 1 }, { id: 2 }]);
globalThis.fetch = async () => ({
  ok: true,
  status: 200,
  json: async () => ({ results: [], next: "https://outro.example/api/" }),
});
await assert.rejects(() => all("cursos"), /fora da origem/);
console.log(
  "Frontend: escape HTML, mensagens de erro, CSRF, sessão, multipart, tokens e paginação passaram.",
);
