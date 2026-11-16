let csrfToken = "";
export class ApiError extends Error {
  constructor(status, data) {
    super("Não foi possível concluir a solicitação.");
    this.status = status;
    this.data = data;
  }
}
export function setCsrf(token) {
  csrfToken = token || "";
}
export async function request(
  path,
  { method = "GET", body, token, signal } = {},
) {
  if (!path.startsWith("/api/"))
    throw new Error("Acesso fora da API não permitido.");
  const headers = { Accept: "application/json" };
  const multipart = typeof FormData !== "undefined" && body instanceof FormData;
  if (body && !multipart) headers["Content-Type"] = "application/json";
  if (method !== "GET" && method !== "HEAD" && !token)
    headers["X-CSRFToken"] = csrfToken;
  if (token) headers["X-Banca-Token"] = token;
  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body ? (multipart ? body : JSON.stringify(body)) : undefined,
      credentials: "same-origin",
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError(0, {
      detail:
        "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.",
    });
  }
  const data =
    response.status === 204
      ? null
      : await response
          .json()
          .catch(() => ({
            detail:
              "O servidor retornou uma resposta inesperada. Tente novamente.",
          }));
  if (!response.ok) throw new ApiError(response.status, data);
  if (data?.csrfToken) setCsrf(data.csrfToken);
  return data;
}
export async function all(resource) {
  let next = `/api/${resource}/`,
    items = [];
  while (next) {
    const url = new URL(next, location.origin);
    if (url.origin !== location.origin)
      throw new Error("Paginação fora da origem.");
    const page = await request(url.pathname + url.search);
    if (Array.isArray(page)) return page;
    items.push(...page.results);
    next = page.next;
  }
  return items;
}
export async function download(path, filename, token) {
  if (!path.startsWith("/api/")) throw new Error("Download fora da API.");
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: token ? { "X-Banca-Token": token } : {},
  });
  if (!response.ok)
    throw new ApiError(
      response.status,
      await response
        .json()
        .catch(() => ({ detail: "O download não está disponível." })),
    );
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
export function errorMessages(error) {
  const labels = {
    titulo: "Título",
    resumo: "Resumo",
    curso: "Curso",
    orientador: "Orientador",
    arquivo: "Arquivo",
    data_hora: "Início da defesa",
    fim: "Fim da defesa",
    parecer: "Parecer",
    nota: "Nota",
    email: "E-mail",
    usuario: "Usuário",
    password: "Senha",
    login: "Usuário",
    matricula: "Matrícula",
    non_field_errors: "",
    __all__: "",
    detail: "",
  };
  const flatten = (value, prefix = "") => {
    if (Array.isArray(value)) return value.flatMap((x) => flatten(x, prefix));
    if (value && typeof value === "object")
      return Object.entries(value).flatMap(([key, val]) =>
        flatten(val, labels[key] ?? key.replaceAll("_", " ")),
      );
    return [prefix ? `${prefix}: ${String(value)}` : String(value)];
  };
  if (error.status === 429)
    return [
      "Você atingiu o limite de tentativas. Aguarde alguns minutos antes de tentar novamente.",
    ];
  if (error.status === 403 && !error.data)
    return [
      "Seu acesso não permite esta operação. Entre novamente ou verifique seu perfil e sua rede de acesso.",
    ];
  return flatten(
    error.data || {
      detail: error.message || "Não foi possível concluir a operação.",
    },
  );
}
