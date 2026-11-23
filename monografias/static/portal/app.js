import { request, all, download, errorMessages } from "./api.js";
import { motion } from "./motion.js";
import {
  escape as e,
  icon,
  labels,
  badge,
  date,
  datetimeLocal,
  heading,
  empty,
  button,
  options,
  tags,
  panel,
  details,
  countLabel,
} from "./ui.js";
const main = document.querySelector("#conteudo");
const modal = document.querySelector("#modal");
const state = {
  user: null,
  courses: [],
  advisors: [],
  externalToken: "",
  epoch: 0,
  busy: false,
};
const role = (name) => state.user?.grupos?.includes(name);
const admin = () => Boolean(state.user?.is_admin);
const courseName = (id) =>
  state.courses.find((x) => x.id === id)?.nome || `Curso ${id}`;
const advisorName = (id) => {
  const p = state.advisors.find((x) => x.id === id);
  return p
    ? [p.first_name, p.last_name].filter(Boolean).join(" ") || `Professor ${id}`
    : id
      ? `Professor ${id}`
      : "Ainda não definido";
};
const manage = (work) =>
  admin() ||
  (role("Professores") && work.orientador === state.user.id) ||
  (role("Coordenadores") &&
    state.courses.some(
      (c) => c.id === work.curso && c.coordenador === state.user.id,
    ));
const go = (path) => {
  if (location.hash === `#/${path}`) route();
  else location.hash = `#/${path}`;
};
const link = (path, text, cls = "btn btn-primary") =>
  `<a class="${cls}" href="#/${path}">${text}</a>`;
const errors = (error) =>
  `<div class="error-box" role="alert"><strong>Confira antes de continuar</strong><ul>${errorMessages(
    error,
  )
    .map((x) => `<li>${e(x)}</li>`)
    .join("")}</ul></div>`;
function toast(text, error = false) {
  const n = document.createElement("div");
  n.className = `toast${error ? " error" : ""}`;
  n.textContent = text;
  document.querySelector("#notificacoes").append(n);
  motion.aviso(n);
  setTimeout(() => motion.esconder(n).then(() => n.remove()), 6000);
}
function showError(error) {
  toast(errorMessages(error).join(" "), true);
}
function closeModal() {
  modal.close();
  modal.innerHTML = "";
}
function openModal(title, html, onSubmit, submitText = "Salvar") {
  modal.innerHTML = `<div class="modal-head"><h2 id="modal-titulo">${e(title)}</h2><button class="icon-button" aria-label="Fechar janela" data-action="fechar-modal">${icon("close")}</button></div><div class="modal-body"><form id="modal-form"><div class="form-errors"></div>${html}<div class="form-actions">${button("Cancelar", "fechar-modal")}<button class="btn btn-primary" type="submit">${e(submitText)}</button></div></form></div>`;
  modal.showModal();
  motion.modal(modal);
  modal.querySelector("form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    if (form.dataset.busy) return;
    form.dataset.busy = "1";
    const submit = form.querySelector("[type=submit]");
    submit.disabled = true;
    form.querySelector(".form-errors").innerHTML = "";
    try {
      await onSubmit(new FormData(form), form);
      if (modal.open && modal.querySelector("#modal-form") === form)
        closeModal();
    } catch (error) {
      if (modal.open) {
        form.querySelector(".form-errors").innerHTML = errors(error);
        form.querySelector(".error-box").scrollIntoView({ block: "nearest" });
      } else showError(error);
    } finally {
      delete form.dataset.busy;
      submit.disabled = false;
    }
  });
}
function confirm(title, text, onConfirm, label = "Confirmar") {
  openModal(title, `<p>${e(text)}</p>`, onConfirm, label);
}
async function lookup() {
  const [courses, advisors] = await Promise.all([
    all("cursos"),
    request("/api/orientadores/"),
  ]);
  state.courses = courses;
  state.advisors = advisors;
}
async function account() {
  const data = await request("/api/conta/");
  state.user = data.usuario;
}
function shell(section) {
  const nav = (path, text, symbol, selected) =>
    `<a href="#/${path}" class="nav-item ${selected ? "active" : ""}" ${selected ? 'aria-current="page"' : ""}>${icon(symbol)}${e(text)}</a>`;
  document.querySelector("#sidebar").innerHTML =
    `<a class="brand" href="#/acervo"><strong>Monografias</strong><small>Repositório acadêmico</small></a><div class="nav-section">Consulta pública</div>${nav("acervo", "Acervo público", "book", section === "acervo")}${nav("externo", "Acesso à banca", "users", section === "externo")}${state.user ? `<div class="nav-section">Minha área</div>${nav("painel", "Visão geral", "grid", section === "painel")}${nav("trabalhos", role("Alunos") ? "Minhas monografias" : "Monografias", "file", section === "trabalhos")}${nav("bancas", "Bancas e avaliações", "calendar", section === "bancas")}${nav("relatorios", "Relatórios", "chart", section === "relatorios")}${admin() ? `<div class="nav-section">Administração</div>${nav("cadastros", "Cadastros", "users", section === "cadastros")}${nav("operacao", "Auditoria e eventos", "lock", section === "operacao")}` : ""}` : ""}<div class="sidebar-bottom"><p class="side-note">Trabalhos publicados ficam abertos a qualquer visitante, sem cadastro.</p></div>`;
  document.querySelector("#topbar").innerHTML =
    `<div class="breadcrumbs"><button class="icon-button mobile-menu" data-action="menu" aria-label="Abrir navegação" aria-expanded="false" aria-controls="sidebar">${icon("menu")}</button><span>Repositório</span><span aria-hidden="true">/</span><span>${e({ acervo: "Acervo público", painel: "Visão geral", trabalhos: "Monografias", bancas: "Bancas e avaliações", relatorios: "Relatórios", login: "Acesso ao sistema", externo: "Acesso à banca", cadastros: "Cadastros", operacao: "Auditoria e eventos" }[section] || "Portal")}</span></div><div class="top-actions">${state.user ? `<span class="profile-text">${e(state.user.nome || state.user.username)}</span><span class="avatar" aria-hidden="true">${icon("user")}</span><button class="icon-button" data-action="logout" aria-label="Sair do sistema">${icon("logout")}</button>` : section === "login" ? "" : link("login", "Entrar no sistema", "btn btn-secondary btn-sm")}</div>`;
  document.title = `${document.querySelector(".breadcrumbs span:last-child")?.textContent || "Portal"} — Monografias`;
  let backdrop = document.querySelector(".mobile-backdrop");
  if (!backdrop) {
    backdrop = document.createElement("div");
    backdrop.className = "mobile-backdrop";
    backdrop.dataset.action = "menu";
    document.body.append(backdrop);
  }
}
async function route() {
  const epoch = ++state.epoch;
  if (modal.open) closeModal();
  const [pathname, search = ""] = (location.hash.slice(2) || "acervo").split(
    "?",
  );
  const [section, id, mode] = pathname.split("/");
  const query = new URLSearchParams(search);
  document.querySelector("#sidebar").classList.remove("open");
  document.querySelector(".mobile-backdrop")?.classList.remove("open");
  shell(section);
  main.setAttribute("aria-busy", "true");
  motion.sair();
  main.innerHTML = `<div class="loading"><span class="spinner"></span>Carregando…</div>`;
  try {
    if (!["acervo", "login", "externo"].includes(section) && !state.user) {
      go("login");
      return;
    }
    let page;
    if (section === "acervo")
      page = id ? await publicDetail(id) : await archive(query);
    else if (section === "login") page = login();
    else if (section === "painel") page = await dashboard();
    else if (section === "trabalhos")
      page =
        id === "novo"
          ? await draftForm()
          : id
            ? mode === "editar"
              ? await draftForm(id)
              : await workDetail(id)
            : await works(query);
    else if (section === "bancas")
      page = id ? await defenseDetail(id) : await defenses();
    else if (section === "relatorios") page = await reports();
    else if (section === "externo") page = await external();
    else if (section === "cadastros") page = await registries(query);
    else if (section === "operacao") page = await operation(query);
    else
      page = {
        html: empty(
          "Página não encontrada",
          "Volte ao acervo para continuar.",
          link("acervo", "Explorar acervo"),
        ),
      };
    if (epoch !== state.epoch) return;
    main.innerHTML = page.html;
    main.setAttribute("aria-busy", "false");
    page.bind?.();
    motion.entrar(main);
    main.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "instant" });
  } catch (error) {
    if (epoch !== state.epoch) return;
    main.setAttribute("aria-busy", "false");
    main.innerHTML =
      heading(
        "Não foi possível carregar",
        "Vamos tentar novamente?",
        error.status === 403
          ? "Seu perfil ou sua rede não permitem acessar esta área."
          : "Verifique a conexão ou tente atualizar a página.",
      ) +
      errors(error) +
      button("Tentar novamente", "atualizar", "btn-primary");
  }
}
const cards = (items, publicView = false) =>
  items
    .map(
      (w) =>
        // Registro de catálogo: número do registro, título, autoria/curso, resumo e assuntos.
        `<article class="result-card"><span class="record-no" title="Número do registro">Nº ${e(w.id)}</span><div class="result-body"><h3><a href="#/${publicView ? "acervo" : "trabalhos"}/${w.id}">${e(w.titulo)}</a></h3><p class="result-meta">${publicView ? `<span class="result-person">${e(w.autor_nome || "Autoria disponível no documento")}</span>` : ""}<span>${e(courseName(w.curso))}</span>${publicView ? "" : badge(w.status)}</p><p class="summary">${e(w.resumo || "Resumo não informado.")}</p>${tags(w.palavras_chave)}</div></article>`,
    )
    .join("");
function pagination(
  data,
  base,
  query,
  noun = ["trabalho encontrado", "trabalhos encontrados"],
) {
  const page = Number(query.get("page") || 1);
  const target = (value) => {
    const q = new URLSearchParams(query);
    q.set("page", value);
    return `${base}?${q}`;
  };
  return `<div class="pagination"><span>${countLabel(data.count, ...noun)}</span><div class="actions">${data.previous ? link(target(page - 1), "Anterior", "btn btn-secondary btn-sm") : ""}<span>Página ${page}</span>${data.next ? link(target(page + 1), "Próxima", "btn btn-secondary btn-sm") : ""}</div></div>`;
}
async function archive(query) {
  const data = await request(`/api/publicadas/?${query}`);
  return {
    html: `<section class="catalog-head"><h1>Monografias defendidas e publicadas</h1><p>Consulte e baixe os trabalhos de conclusão aprovados em banca e autorizados para publicação pelos autores.</p></section><section class="search-panel"><form id="search-form" role="search"><div class="search-input-row"><label class="search-field"><span class="sr-only">Pesquisar no acervo</span>${icon("search")}<input name="busca" value="${e(query.get("busca"))}" placeholder="Título, autor, orientador ou assunto" maxlength="200"></label><button class="btn btn-primary" type="submit">Pesquisar</button></div><div class="filters"><label>Curso<select name="curso">${options(state.courses, "id", (x) => x.nome, query.get("curso"), "Todos os cursos")}</select></label><label>Orientador<select name="orientador">${options(state.advisors, "id", (x) => advisorName(x.id), query.get("orientador"), "Todos os orientadores")}</select></label><label>Ano da defesa<input type="number" name="ano_defesa" min="1900" max="9999" value="${e(query.get("ano_defesa"))}" placeholder="Todos os anos"></label><label>Palavras-chave<input name="palavras_chave" value="${e(query.get("palavras_chave"))}" placeholder="Ex.: educação, redes"></label></div><div class="filter-bottom"><span>${icon("lock")} Somente trabalhos publicados e autorizados</span>${query.size || query.toString() ? link("acervo", "Limpar filtros", "text-link") : ""}</div></form></section><div class="result-heading"><h2>${query.toString() ? "Resultados da pesquisa" : "Publicados recentemente"}</h2><span class="count">${data.count} ${data.count === 1 ? "trabalho" : "trabalhos"}</span></div>${data.results.length ? cards(data.results, true) : empty(query.toString() ? "Nenhum trabalho encontrado" : "O acervo está sendo construído", query.toString() ? "Experimente outros termos ou remova alguns filtros." : "Os trabalhos aparecerão aqui após a defesa e a autorização de publicação.")}${data.count ? pagination(data, "acervo", query) : ""}`,
    bind: () =>
      document
        .querySelector("#search-form")
        .addEventListener("submit", (event) => {
          event.preventDefault();
          const q = new URLSearchParams();
          for (const [k, v] of new FormData(event.currentTarget))
            if (v.trim()) q.set(k, v.trim());
          go(`acervo?${q}`);
        }),
  };
}
async function publicDetail(id) {
  const w = await request(`/api/publicadas/${id}/`);
  return {
    html: `${link("acervo", "Voltar ao acervo", "text-link back-link")}<div class="split-detail work-record"><article class="work-text"><h1 class="detail-title">${e(w.titulo)}</h1><p class="work-author">${e(w.autor_nome || "Autoria disponível no documento")}</p><h2>Resumo</h2><p class="detail-text">${e(w.resumo || "Resumo não informado.")}</p><h2>Assuntos</h2>${tags(w.palavras_chave)}</article><aside class="record-card" aria-label="Ficha do trabalho"><h2>Ficha do trabalho</h2>${details(
      [
        ["Registro", `Nº ${w.id}`],
        ["Autoria", w.autor_nome || "Disponível no documento"],
        ["Orientação", w.orientador_nome || "Não informada"],
        ["Curso", courseName(w.curso)],
        ["Publicado em", date(w.publicada_em)],
      ],
    )}<button class="btn btn-primary full-width" data-action="download" data-path="/api/publicadas/${w.id}/pdf/" data-name="monografia-${w.id}.pdf">${icon("download")}Baixar PDF</button><p class="notice-inline">Versão autorizada pelo autor. Quando houve correções após a defesa, o arquivo é a versão corrigida.</p></aside></div>`,
  };
}
function login() {
  return {
    html: `<section class="login-layout"><div class="login-story"><h1>Área de alunos, orientadores e coordenação</h1><ol class="login-steps"><li>O aluno envia o rascunho em PDF e submete ao orientador.</li><li>O orientador aprova e a banca é agendada.</li><li>Depois da defesa e do termo de autorização, o trabalho entra no acervo público.</li></ol></div><div class="login-form"><h2>Entrar</h2><p>Use a conta fornecida pela coordenação do seu curso.</p><form id="login-form"><div class="form-errors"></div><label>Usuário<input name="login" required autocomplete="username" placeholder="Seu nome de usuário"></label><label>Senha<div class="password-field"><input name="password" type="password" aria-label="Senha" required autocomplete="current-password" placeholder="Sua senha"><button type="button" class="password-toggle" data-action="mostrar-senha" aria-label="Mostrar senha">Mostrar</button></div></label><button type="submit" class="btn btn-primary">Entrar no sistema</button></form><p class="notice-inline section-space">Precisa de uma conta ou esqueceu a senha? Entre em contato com a administração do seu curso.</p><a href="#/acervo" class="text-link">Consultar o acervo sem entrar</a></div></section>`,
    bind: () =>
      document
        .querySelector("#login-form")
        .addEventListener("submit", async (event) => {
          event.preventDefault();
          await submitForm(event.currentTarget, async (fd) => {
            await request("/api/conta/", {
              method: "POST",
              body: Object.fromEntries(fd),
            });
            await account();
            go("painel");
          });
        }),
  };
}
async function submitForm(form, action) {
  if (form.dataset.busy) return;
  form.dataset.busy = "1";
  const b = form.querySelector("[type=submit]");
  b.disabled = true;
  const old = b.innerHTML;
  b.textContent = "Aguarde…";
  form.querySelector(".form-errors").innerHTML = "";
  try {
    await action(new FormData(form));
  } catch (error) {
    form.querySelector(".form-errors").innerHTML = errors(error);
    form.querySelector(".error-box").scrollIntoView({ block: "center" });
  } finally {
    delete form.dataset.busy;
    b.disabled = false;
    b.innerHTML = old;
  }
}
async function dashboard() {
  const [works, bancas] = await Promise.all([
    all("monografias"),
    all("bancas"),
  ]);
  const drafts = works.filter((x) => x.status === "rascunho").length,
    pending = works.filter((x) => x.status === "em_avaliacao").length,
    published = works.filter((x) => x.status === "publicada").length;
  return {
    html:
      heading(
        "Visão geral",
        `Olá, ${state.user.nome || state.user.username}`,
        role("Alunos")
          ? "Seus trabalhos, do rascunho à publicação, e as defesas marcadas."
          : role("Coordenadores")
            ? "Trabalhos dos cursos sob sua responsabilidade e as próximas defesas."
            : "Suas orientações e as bancas das quais você participa.",
        `${link("trabalhos", "Acompanhar monografias", "btn btn-secondary")}${
          role("Alunos")
            ? link("trabalhos/novo", `${icon("plus")} Novo rascunho`)
            : ""
        }`,
      ) +
      `<div class="ledger" role="list" aria-label="Resumo das monografias">${[
        [works.length, "Monografias na sua área"],
        [drafts, "Em rascunho"],
        [pending, "Aguardando orientação"],
        [published, "Publicadas"],
      ]
        .map(
          ([n, label]) =>
            `<div class="ledger-item" role="listitem"><strong data-count="${n}">${n}</strong><span>${label}</span></div>`,
        )
        .join("")}</div><div class="grid-2">${panel(
        "Monografias em acompanhamento",
        works.length
          ? works
              .slice(0, 5)
              .map(
                (w) =>
                  `<a class="list-item" href="#/trabalhos/${w.id}"><span class="list-symbol">${icon("file")}</span><span><strong>${e(w.titulo)}</strong><small>${e(courseName(w.curso))}</small></span>${badge(w.status)}</a>`,
              )
              .join("")
          : empty(
              "Seu próximo trabalho começa aqui",
              "As monografias vinculadas à sua conta aparecerão nesta área.",
              role("Alunos") ? link("trabalhos/novo", "Criar rascunho") : "",
            ),
        link("trabalhos", "Ver todas", "text-link"),
      )}${panel(
        "Agenda de bancas",
        bancas
          .filter((b) => ["em_preparacao", "agendada"].includes(b.status))
          .slice(0, 5)
          .map(
            (b) =>
              `<a class="list-item" href="#/bancas/${b.id}"><span class="list-symbol">${icon("calendar")}</span><span><strong>${e(b.monografia_titulo)}</strong><small>${date(b.data_hora, true)}</small></span>${badge(b.status)}</a>`,
          )
          .join("") ||
          empty(
            "Nenhum compromisso por enquanto",
            "Bancas agendadas e convites aparecerão aqui.",
          ),
        link("bancas", "Ver agenda", "text-link"),
      )}</div>`,
  };
}
async function works(query) {
  const items = await all("monografias");
  let filtered = items;
  if (query.get("status"))
    filtered = items.filter((x) => x.status === query.get("status"));
  if (query.get("busca"))
    filtered = filtered.filter((x) =>
      x.titulo
        .toLocaleLowerCase()
        .includes(query.get("busca").toLocaleLowerCase()),
    );
  return {
    html:
      heading(
        "Acompanhamento",
        role("Alunos") ? "Minhas monografias" : "Monografias",
        "Do rascunho à publicação, acompanhe o andamento de cada trabalho.",
        role("Alunos")
          ? link("trabalhos/novo", `${icon("plus")} Novo rascunho`)
          : "",
      ) +
      `<form id="work-filter" class="panel inline-form"><label>Buscar por título<input name="busca" value="${e(query.get("busca"))}" placeholder="Digite o título"></label><label>Status<select name="status">${options(
        Object.entries(labels)
          .slice(0, 7)
          .map(([id, nome]) => ({ id, nome })),
        "id",
        (x) => x.nome,
        query.get("status"),
        "Todos os status",
      )}</select></label><button class="btn btn-primary">Filtrar</button></form><div class="result-heading"><h2>Trabalhos vinculados a você</h2><span class="count">${filtered.length} resultados</span></div>${filtered.length ? cards(filtered) : empty("Nenhuma monografia nesta seleção", "Novos trabalhos aparecerão conforme seus vínculos acadêmicos.", role("Alunos") ? link("trabalhos/novo", "Criar rascunho") : "")}`,
    bind: () =>
      document
        .querySelector("#work-filter")
        .addEventListener("submit", (ev) => {
          ev.preventDefault();
          const q = new URLSearchParams();
          for (const [k, v] of new FormData(ev.currentTarget))
            if (v) q.set(k, v);
          go(`trabalhos?${q}`);
        }),
  };
}
async function draftForm(id) {
  if (!role("Alunos"))
    throw {
      status: 403,
      data: { detail: "Esta área é reservada aos alunos." },
    };
  const w = id ? await request(`/api/monografias/${id}/`) : {};
  if (id && (w.autor !== state.user.id || w.status !== "rascunho"))
    throw {
      status: 403,
      data: { detail: "Somente o autor pode editar um rascunho." },
    };
  return {
    html:
      heading(
        "Submissão",
        id ? "Editar rascunho" : "Novo rascunho",
        "Salve seu trabalho e revise os dados antes de submeter ao orientador.",
      ) +
      `<div class="split-detail"><section class="panel"><form id="draft-form"><div class="form-errors"></div><div class="form-grid"><label class="full">Título da monografia<input name="titulo" value="${e(w.titulo)}" required maxlength="250" placeholder="Dê um título ao seu trabalho"></label><label class="full">Resumo<textarea name="resumo" rows="6" placeholder="Apresente os objetivos, a abordagem e as principais contribuições.">${e(w.resumo)}</textarea></label><label>Curso<select name="curso" required>${options(state.courses, "id", (x) => x.nome, w.curso, "Selecione o curso")}</select></label><label>Orientador<select name="orientador">${options(state.advisors, "id", (x) => advisorName(x.id), w.orientador, "Definir depois")}</select></label><label class="full">Palavras-chave<input name="palavras_chave" value="${e(w.palavras_chave)}" maxlength="500" placeholder="Separe as palavras-chave por vírgulas"></label><label class="full">Arquivo da monografia<input name="arquivo" type="file" accept="application/pdf,.pdf" ${id ? "" : "required"}><small class="help">PDF sem senha, até 50 MiB.${id ? " Deixe vazio para manter o arquivo atual." : ""}</small></label></div><div class="form-actions">${link(id ? `trabalhos/${id}` : "trabalhos", "Cancelar", "btn btn-secondary")}<button class="btn btn-primary" type="submit">${icon("check")} Salvar rascunho</button></div></form></section><aside>${panel("Antes de enviar", `<ol class="step-list"><li class="done">Preencha os dados<small>Título, curso e informações do trabalho.</small></li><li>Envie seu PDF<small>Você pode substituí-lo enquanto for rascunho.</small></li><li>Escolha o orientador<small>Obrigatório para realizar a submissão.</small></li><li>Revise e submeta<small>Após submeter, a edição será bloqueada.</small></li></ol>`)}</aside></div>`,
    bind: () =>
      document.querySelector("#draft-form").addEventListener("submit", (ev) => {
        ev.preventDefault();
        submitForm(ev.currentTarget, async (fd) => {
          const file = fd.get("arquivo");
          if (file?.size > 50 * 1024 * 1024)
            throw { data: { arquivo: ["O PDF deve ter no máximo 50 MiB."] } };
          if (!file?.size) fd.delete("arquivo");
          const result = await request(
            `/api/monografias/${id ? `${id}/` : ""}`,
            { method: id ? "PATCH" : "POST", body: fd },
          );
          toast("Rascunho salvo.");
          go(`trabalhos/${result.id}`);
        });
      }),
  };
}
async function workDetail(id) {
  const [w, docs, bancas] = await Promise.all([
    request(`/api/monografias/${id}/`),
    all("documentos"),
    all("bancas"),
  ]);
  const mine = role("Alunos") && w.autor === state.user.id,
    manager = manage(w),
    documents = docs.filter((d) => d.monografia === w.id),
    defenses = bancas.filter((b) => b.monografia === w.id);
  const steps = [
    "rascunho",
    "em_avaliacao",
    "aprovada_orientador",
    "aprovada",
    "publicada",
  ];
  let current = steps.indexOf(w.status);
  if (w.status === "ressalvas") current = 3;
  const actions = `${mine && w.status === "rascunho" ? `${link(`trabalhos/${w.id}/editar`, "Editar", "btn btn-secondary")}${button("Submeter ao orientador", "submeter", "btn-primary", `data-id="${w.id}"`)}${button("Excluir rascunho", "excluir-trabalho", "btn-danger", `data-id="${w.id}"`)}` : ""}${role("Professores") && w.orientador === state.user.id && w.status === "em_avaliacao" ? button("Aprovar submissão", "aprovar", "btn-primary", `data-id="${w.id}"`) : ""}${manager && w.status === "aprovada_orientador" && !defenses.some((b) => b.status !== "cancelada") ? button("Preparar banca", "nova-banca", "btn-primary", `data-id="${w.id}"`) : ""}`;
  return {
    html:
      link("trabalhos", "Voltar às monografias", "text-link back-link") +
      `<div class="section-space page-heading"><div>${badge(w.status)}<h1 class="detail-title">${e(w.titulo)}</h1><p>${e(courseName(w.curso))}. Orientação: ${e(advisorName(w.orientador))}</p></div><div class="actions">${actions}</div></div><div class="split-detail"><div>${panel("Resumo", `<p class="detail-text">${e(w.resumo || "Resumo não informado.")}</p><div class="section-space">${tags(w.palavras_chave)}</div>`)}${panel("Documentos", `<p class="notice-inline">Envie atas, termo de autorização, comprovantes e a versão corrigida. A publicação depende das validações exigidas.</p>${documents.length ? `<div class="table-wrap"><table><thead><tr><th>Documento</th><th>Conferência</th><th>Ações</th></tr></thead><tbody>${documents.map((d) => `<tr><td>${e({ ata: "Ata de defesa", termo: "Termo de autorização", ortografia: "Revisão ortográfica", corrigida: "Versão corrigida" }[d.tipo])}</td><td>${d.validado_em ? `<span class="badge green">Validado</span><small class="block">${date(d.validado_em)}</small>` : '<span class="badge amber">Aguardando validação</span>'}</td><td><div class="actions">${button("Baixar", "download", "btn-secondary btn-sm", `data-path="/api/documentos/${d.id}/pdf/" data-name="documento-${d.id}.pdf"`)}${manager && !d.validado_em && w.status !== "publicada" ? button("Validar", "validar-documento", "btn-primary btn-sm", `data-id="${d.id}"`) : ""}</div></td></tr>`).join("")}</tbody></table></div>` : empty("Nenhum documento enviado", "Adicione os documentos desta monografia quando estiverem disponíveis.")}`, (mine || manager) && w.status !== "publicada" ? button("Enviar documento", "enviar-documento", "btn-secondary btn-sm", `data-id="${w.id}"`) : "")}${panel("Bancas vinculadas", defenses.length ? defenses.map((b) => `<a class="list-item" href="#/bancas/${b.id}"><span class="list-symbol">${icon("calendar")}</span><span><strong>${date(b.data_hora, true)}</strong><small>${e(b.local || "Defesa remota")}</small></span>${badge(b.status)}</a>`).join("") : empty("A defesa ainda não foi preparada", "O orientador ou coordenador poderá preparar a banca após a aprovação da submissão."))}</div><aside>${panel(
        "Arquivo da monografia",
        `<div class="actions">${button("Baixar PDF", "download", "btn-primary", `data-path="/api/monografias/${w.id}/pdf/" data-name="monografia-${w.id}.pdf"`)}</div>${details(
          [
            ["Versão do arquivo", w.versao],
            ["Submetida em", date(w.submetida_em)],
            ["Aprovação do orientador", date(w.aprovado_em)],
            ["Publicado em", date(w.publicada_em)],
          ],
        )}`,
      )}${panel("Caminho do trabalho", `<ol class="step-list">${["Rascunho", "Submissão ao orientador", "Aprovação da orientação", "Resultado da defesa", "Publicação"].map((x, i) => `<li class="${i <= current ? "done" : ""}">${e(x)}</li>`).join("")}</ol>${w.status === "ressalvas" ? '<div class="info-box">Envie a versão corrigida para concluir a publicação.</div>' : ""}${w.status === "reprovada" ? '<div class="error-box">O resultado da defesa foi de reprovação.</div>' : ""}`)}</aside></div>`,
  };
}
function defenseForm(workId, existing) {
  openModal(
    existing ? "Editar banca" : "Preparar banca",
    `<div class="info-box">Defina o intervalo da defesa. Depois convide os membros e aguarde a confirmação de todos antes de agendar.</div><div class="form-grid"><label>Início<input name="data_hora" type="datetime-local" required value="${datetimeLocal(existing?.data_hora)}"></label><label>Fim<input name="fim" type="datetime-local" required value="${datetimeLocal(existing?.fim)}"></label><label class="full">Local presencial<input name="local" maxlength="250" value="${e(existing?.local)}" placeholder="Ex.: Auditório, sala 12"></label><label class="full">Link de videoconferência<input name="link" type="url" value="${e(existing?.link)}" placeholder="https://…"><small class="help">Informe ao menos o local ou o link.</small></label></div>`,
    async (fd) => {
      const data = Object.fromEntries(fd);
      if (!data.local && !data.link)
        throw { data: { detail: "Informe o local ou o link da defesa." } };
      data.data_hora = new Date(data.data_hora).toISOString();
      data.fim = new Date(data.fim).toISOString();
      if (!existing) data.monografia = Number(workId);
      const b = await request(
        `/api/bancas/${existing ? `${existing.id}/` : ""}`,
        { method: existing ? "PATCH" : "POST", body: data },
      );
      toast(
        existing
          ? "Banca atualizada. Os membros precisarão confirmar novamente."
          : "Proposta de banca salva.",
      );
      go(`bancas/${b.id}`);
    },
  );
}
async function defenses() {
  const bancas = await all("bancas");
  return {
    html:
      heading(
        "Agenda acadêmica",
        "Bancas e avaliações",
        "Prepare defesas, acompanhe convites e registre suas avaliações.",
      ) +
      panel(
        "Agenda de defesas",
        bancas.length
          ? `<div class="table-wrap"><table><thead><tr><th>Monografia</th><th>Data e hora</th><th>Status</th><th></th></tr></thead><tbody>${bancas.map((b) => `<tr><td><strong>${e(b.monografia_titulo)}</strong><small class="block">${e(b.local || "Defesa remota")}</small></td><td>${date(b.data_hora, true)}</td><td>${badge(b.status)}</td><td>${link(`bancas/${b.id}`, "Acompanhar", "text-link")}</td></tr>`).join("")}</tbody></table></div>`
          : empty(
              "Nenhuma banca por enquanto",
              "As propostas de defesa e os convites para você aparecerão aqui.",
              link("trabalhos", "Ver monografias", "btn btn-secondary"),
            ),
      ),
  };
}
async function defenseDetail(id) {
  const [b, members, grades] = await Promise.all([
    request(`/api/bancas/${id}/`),
    all("membros"),
    all("avaliacoes"),
  ]);
  let work;
  try {
    work = await request(`/api/monografias/${b.monografia}/`);
  } catch (error) {
    if (error.status !== 404 && error.status !== 403) throw error;
  }
  const manager = work ? manage(work) : false,
    list = members.filter((m) => m.banca === b.id),
    my = list.find((m) => m.usuario === state.user.id),
    ended = b.fim && new Date(b.fim) <= new Date();
  return {
    html:
      link("bancas", "Voltar à agenda", "text-link back-link") +
      `<div class="section-space page-heading"><div><h1 class="detail-title">${e(b.monografia_titulo)}</h1><div class="actions">${badge(b.status)}${b.nota_final !== null ? `<span>Média final: <strong>${e(b.nota_final)}</strong></span>` : ""}</div></div><div class="actions">${my && ended && b.status === "agendada" && !b.encerrada_em ? button("Registrar avaliação", "avaliar", "btn-primary", `data-id="${my.id}"`) : ""}${manager && ["em_preparacao", "agendada"].includes(b.status) && !b.encerrada_em ? `${button("Editar banca", "editar-banca", "btn-secondary", `data-id="${b.id}"`)}${b.status === "em_preparacao" ? button("Agendar defesa", "agendar", "btn-primary", `data-id="${b.id}"`) : ""}${button("Cancelar banca", "cancelar-banca", "btn-danger", `data-id="${b.id}"`)}` : ""}</div></div><div class="grid-2">${panel(
        "Informações da defesa",
        details([
          ["Início", date(b.data_hora, true)],
          ["Fim", date(b.fim, true)],
          ["Local", b.local || "Defesa remota"],
        ]) +
          `${b.link ? `<p class="section-space"><a class="btn btn-secondary" href="${e(safeHttp(b.link))}" target="_blank" rel="noopener noreferrer">Abrir videoconferência</a></p>` : ""}${work ? `<p class="section-space">${link(`trabalhos/${b.monografia}`, "Ver monografia", "text-link")}</p>` : ""}`,
      )}${panel("Próxima etapa", b.status === "em_preparacao" ? `<div class="info-box">A defesa só poderá ser agendada após a confirmação de todos os membros. Qualquer alteração de horário ou local exige novas confirmações.</div>${my && !my.confirmado ? button("Confirmar minha disponibilidade", "confirmar-membro", "btn-primary", `data-id="${my.id}"`) : my?.confirmado ? '<span class="badge green">Sua disponibilidade foi confirmada</span>' : '<p class="subtle">Aguardando composição e confirmações da banca.</p>'}` : b.status === "agendada" ? `<p class="subtle">${ended ? "A defesa terminou. Os membros podem registrar suas avaliações." : "A avaliação ficará disponível após o horário de término da defesa."}</p>${my && ended && !b.encerrada_em ? button(grades.some((a) => a.membro === my.id) ? "Editar minha avaliação" : "Registrar avaliação", "avaliar", "btn-primary section-space", `data-id="${my.id}"`) : ""}` : b.status === "realizada" ? `<div class="info-box">O resultado foi fechado em ${date(b.encerrada_em, true)}. As avaliações não podem mais ser alteradas.</div>` : '<p class="subtle">Esta banca foi cancelada. Os convites foram revogados.</p>')}</div>${panel("Membros da banca", list.length ? `<div class="table-wrap"><table><thead><tr><th>Membro</th><th>Participação</th><th>Disponibilidade</th><th>Ações</th></tr></thead><tbody>${list.map((m) => `<tr><td><strong>${e(m.usuario ? advisorName(m.usuario) : m.nome)}</strong><small class="block">${m.usuario ? "Membro interno" : e(m.email)}</small></td><td>${m.usuario ? "Professor" : "Convidado externo"}</td><td>${m.revogado ? '<span class="badge red">Revogado</span>' : m.confirmado ? '<span class="badge green">Confirmada</span>' : '<span class="badge amber">Pendente</span>'}</td><td><div class="actions">${m.usuario === state.user.id && !m.confirmado && b.status === "em_preparacao" ? button("Confirmar", "confirmar-membro", "btn-primary btn-sm", `data-id="${m.id}"`) : ""}${manager && !m.usuario && ["em_preparacao", "agendada"].includes(b.status) ? button("Renovar acesso", "renovar-token", "btn-secondary btn-sm", `data-id="${m.id}"`) : ""}${manager && b.status === "em_preparacao" ? button("Remover", "remover-membro", "btn-danger btn-sm", `data-id="${m.id}"`) : ""}${manager && !m.usuario && !m.revogado && b.status === "agendada" ? button("Revogar acesso", "revogar-token", "btn-danger btn-sm", `data-id="${m.id}"`) : ""}</div></td></tr>`).join("")}</tbody></table></div>` : empty("A banca ainda não tem membros", "Convide professores ou membros externos para compor a banca."), manager && b.status === "em_preparacao" ? button("Convidar membro", "convidar", "btn-secondary btn-sm", `data-id="${b.id}"`) : "")}${panel(
        "Avaliações",
        list.some((m) => grades.some((a) => a.membro === m.id))
          ? list
              .map((m) => {
                const a = grades.find((a) => a.membro === m.id);
                return a
                  ? `<article class="evaluation"><div class="panel-head"><strong>${e(m.usuario ? advisorName(m.usuario) : m.nome)}</strong><span class="badge green">Nota ${e(a.nota)}</span></div><p class="detail-text">${e(a.parecer)}</p><p class="notice-inline">${e({ aprovado: "Aprovado sem ressalvas", ressalvas: "Aprovado com ressalvas", reprovado: "Reprovado" }[a.recomendacao])}</p>${m.usuario === state.user.id && !b.encerrada_em ? button("Editar minha avaliação", "avaliar", "btn-secondary btn-sm", `data-id="${m.id}"`) : ""}</article>`
                  : "";
              })
              .join("")
          : empty(
              "Avaliações ainda não disponíveis",
              "Cada membro acessa seu próprio parecer. O conjunto fica disponível após o fechamento do resultado.",
            ),
      )}`,
    bind: () => {
      state.currentDefense = { b, work, list, grades };
    },
  };
}
function safeHttp(value) {
  try {
    const u = new URL(value);
    return ["https:", "http:"].includes(u.protocol) ? u.href : "#";
  } catch {
    return "#";
  }
}
function inviteForm(id) {
  openModal(
    "Convidar membro",
    `<div class="form-grid"><label class="full">Tipo de participação<select name="tipo" id="invite-type"><option value="interno">Professor da instituição</option><option value="externo">Convidado externo</option></select></label><label class="full" id="invite-internal">Professor<select name="usuario">${options(state.advisors, "id", (x) => advisorName(x.id), null, "Selecione um professor")}</select></label><div id="invite-external" class="full form-grid" hidden><label class="full">Nome do convidado<input name="nome" maxlength="200"></label><label class="full">E-mail<input name="email" type="email"></label></div></div>`,
    async (fd) => {
      const data = { banca: Number(id) };
      if (fd.get("tipo") === "interno") {
        if (!fd.get("usuario"))
          throw { data: { usuario: "Selecione um professor." } };
        data.usuario = Number(fd.get("usuario"));
      } else {
        data.nome = fd.get("nome");
        data.email = fd.get("email");
      }
      const result = await request("/api/membros/", {
        method: "POST",
        body: data,
      });
      if (result.token_temporario) {
        closeModal();
        showToken(result.token_temporario, result.membro.expira_em);
        await refreshBehindModal();
      } else {
        toast("Convite registrado.");
        route();
      }
    },
    "Enviar convite",
  );
  document.querySelector("#invite-type").addEventListener("change", (ev) => {
    const external = ev.target.value === "externo";
    document.querySelector("#invite-internal").hidden = external;
    document.querySelector("#invite-external").hidden = !external;
  });
}
function showToken(token, expires) {
  modal.innerHTML = `<div class="modal-head"><h2 id="modal-titulo">Acesso temporário à banca</h2><button class="icon-button" data-action="fechar-modal" aria-label="Fechar janela">${icon("close")}</button></div><div class="modal-body"><p>Compartilhe este código privadamente com o convidado. Ele será informado na opção <strong>Acesso à banca</strong> do portal.</p><div class="token-box" id="generated-token">${e(token)}</div><p class="notice-inline">Válido até ${date(expires, true)}. O código não será exibido novamente após fechar esta janela.</p><div class="actions">${button("Copiar código", "copiar-token", "btn-primary")}${button("Concluir", "fechar-modal")}</div></div>`;
  modal.showModal();
  motion.modal(modal);
}
async function refreshBehindModal() {
  /* A lista será atualizada após fechar a janela, sem descartar o token. */ state.refreshOnClose = true;
}
function evaluationForm(memberId, externalMode = false) {
  const current = externalMode
    ? state.externalData?.avaliacao
    : state.currentDefense?.grades.find((a) => a.membro === Number(memberId));
  openModal(
    current ? "Editar avaliação" : "Registrar avaliação",
    `<div class="info-box">Revise antes de salvar. Após todas as avaliações, o resultado será fechado automaticamente e não poderá mais ser alterado.</div><div class="form-grid"><label>Nota (0 a 10)<input name="nota" type="number" min="0" max="10" step="0.01" required value="${e(current?.nota)}"></label><label>Recomendação<select name="recomendacao" required>${options(
      [
        { id: "aprovado", nome: "Aprovado sem ressalvas" },
        { id: "ressalvas", nome: "Aprovado com ressalvas" },
        { id: "reprovado", nome: "Reprovado" },
      ],
      "id",
      (x) => x.nome,
      current?.recomendacao,
      "Selecione",
    )}</select></label><label class="full">Parecer<textarea name="parecer" required rows="5">${e(current?.parecer)}</textarea></label></div>`,
    async (fd) => {
      const data = Object.fromEntries(fd);
      data.membro = Number(memberId);
      await request(
        externalMode
          ? "/api/externo/"
          : `/api/avaliacoes/${current ? `${current.id}/` : ""}`,
        {
          method: externalMode ? "POST" : current ? "PATCH" : "POST",
          body: data,
          token: externalMode ? state.externalToken : undefined,
        },
      );
      toast("Avaliação registrada.");
      route();
    },
    "Salvar avaliação",
  );
}
function uploadDocument(id) {
  openModal(
    "Enviar documento",
    `<div class="form-grid"><label class="full">Tipo de documento<select name="tipo" required><option value="termo">Termo de autorização de publicação</option><option value="ata">Ata de defesa</option><option value="ortografia">Comprovante de revisão ortográfica</option><option value="corrigida">Versão corrigida da monografia</option></select></label><label class="full">Arquivo PDF<input type="file" name="arquivo" accept="application/pdf,.pdf" required><small class="help">Até 50 MiB, sem senha. O responsável deverá conferir o documento antes da validação.</small></label></div>`,
    async (fd) => {
      if (fd.get("arquivo").size > 50 * 1024 * 1024)
        throw { data: { arquivo: "O PDF deve ter até 50 MiB." } };
      fd.set("monografia", id);
      await request("/api/documentos/", { method: "POST", body: fd });
      toast("Documento enviado para conferência.");
      route();
    },
    "Enviar documento",
  );
}
async function external() {
  if (!state.externalToken)
    return {
      html:
        heading(
          "Participação na defesa",
          "Acesso de membro externo",
          "Um convite temporário, sem necessidade de criar uma conta.",
        ) +
        `<section class="panel external-card"><h2>Informe seu código de acesso</h2><p class="subtle">Use o código compartilhado pelo responsável pela banca.</p><form id="external-form" class="section-space"><div class="form-errors"></div><label>Código do convite<input name="token" type="password" required maxlength="200" autocomplete="off" spellcheck="false"></label><div class="form-actions"><button class="btn btn-primary" type="submit">Acessar banca ${icon("arrow")}</button></div></form><p class="notice-inline">Seu código é temporário e fica somente na memória desta página. Não o compartilhe publicamente.</p></section>`,
      bind: () =>
        document
          .querySelector("#external-form")
          .addEventListener("submit", (ev) => {
            ev.preventDefault();
            submitForm(ev.currentTarget, async (fd) => {
              const token = fd.get("token").trim();
              try {
                await request("/api/externo/", { token });
              } catch (error) {
                if (error.status === 403)
                  throw {
                    data: {
                      detail:
                        "O código é inválido, expirou ou foi revogado. Solicite um novo acesso ao responsável pela banca.",
                    },
                  };
                throw error;
              }
              state.externalToken = token;
              route();
            });
          }),
    };
  let data;
  try {
    data = await request("/api/externo/", { token: state.externalToken });
  } catch (error) {
    state.externalToken = "";
    throw error;
  }
  state.externalData = data;
  return {
    html:
      heading(
        "Membro convidado",
        "Sua participação faz a diferença.",
        "Consulte a defesa e registre sua contribuição.",
      ) +
      `<section class="panel external-card"><h2 class="detail-title">${e(data.titulo)}</h2>${details(
        [
          ["Início", date(data.data_hora, true)],
          ["Fim", date(data.fim, true)],
          ["Local", data.local || "Defesa remota"],
        ],
      )}${data.link ? `<p class="section-space"><a class="text-link" href="${e(safeHttp(data.link))}" target="_blank" rel="noopener noreferrer">Abrir videoconferência</a></p>` : ""}<div class="section-space">${badge(data.status)}${data.confirmado ? '<span class="badge green">Disponibilidade confirmada</span>' : ""}</div><div class="actions section-space">${data.status === "em_preparacao" && !data.confirmado ? button("Confirmar disponibilidade", "confirmar-externo", "btn-primary") : ""}${["agendada", "realizada"].includes(data.status) ? button("Baixar PDF", "pdf-externo") : ""}${data.status === "agendada" && data.fim && new Date(data.fim) <= new Date() && !data.encerrada_em ? button(data.avaliacao ? "Editar minha avaliação" : "Registrar avaliação", "avaliar-externo", "btn-primary", `data-id="${data.membro}"`) : ""}</div><p class="notice-inline">${data.encerrada_em ? "O resultado foi fechado. As avaliações não podem mais ser alteradas." : data.status === "agendada" ? "A avaliação fica disponível após o término da defesa e antes do fechamento do resultado." : "Confirme sua disponibilidade para que o responsável possa concluir o agendamento."}</p>${button("Atualizar situação", "atualizar", "btn-ghost")}<div class="section-space">${button("Encerrar acesso temporário", "sair-externo", "btn-ghost")}</div></section>`,
  };
}
async function reports() {
  const data = await request("/api/relatorios/");
  const chart = (items, key, name) => {
    const max = Math.max(...items.map((x) => x.total), 1);
    return items.length
      ? `<div class="bar-chart">${items.map((x) => `<div><div class="bar-label"><span>${e(name(x[key]))}</span><strong>${x.total}</strong></div><div class="bar-track"><div class="bar-fill" style="width:${Math.max(2, (Number(x.total) / max) * 100)}%"></div></div></div>`).join("")}</div>`
      : empty(
          "Ainda sem dados",
          "As estatísticas aparecem conforme os trabalhos avançam.",
        );
  };
  return {
    html:
      heading(
        "Relatórios",
        "Indicadores das monografias",
        "Dados limitados aos trabalhos que você tem permissão para consultar.",
      ) +
      `<div class="ledger ledger-2" role="list" aria-label="Indicadores"><div class="ledger-item" role="listitem"><strong>${data.taxa_aprovacao === null ? "—" : new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 1 }).format(data.taxa_aprovacao)}</strong><span>Taxa de aprovação entre resultados fechados</span></div><div class="ledger-item" role="listitem"><strong>${data.tempo_medio_dias === null ? "—" : Number(data.tempo_medio_dias).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}</strong><span>Dias em média entre submissão e defesa${data.tempo_medio_dias === null ? " (ainda sem defesas com data de submissão)" : ""}</span></div></div><div class="grid-2">${panel("Monografias por curso", chart(data.por_curso, "curso_id", courseName))}${panel("Monografias por orientador", chart(data.por_orientador, "orientador_id", advisorName))}</div>${panel(
        "Defesas realizadas por ano",
        chart(data.por_ano_defesa, "data_hora__year", (x) => x),
      )}`,
  };
}
async function registries(query) {
  if (!admin())
    throw {
      status: 403,
      data: { detail: "Esta área é reservada à administração." },
    };
  const type = ["cursos", "usuarios", "alunos", "professores"].includes(
    query.get("tipo"),
  )
    ? query.get("tipo")
    : "cursos";
  const [items, users, groups] = await Promise.all([
    all(type),
    type === "usuarios" ? Promise.resolve([]) : all("usuarios"),
    request("/api/grupos/"),
  ]);
  const people = type === "usuarios" ? items : users;
  state.registry = { type, items, users: people, groups };
  const name = (id) => {
    const u = people.find((x) => x.id === id);
    return u
      ? [u.first_name, u.last_name].filter(Boolean).join(" ") || u.username
      : `Usuário ${id}`;
  };
  const columns =
    type === "cursos"
      ? ["Curso", "Código", "Coordenação"]
      : type === "usuarios"
        ? ["Usuário", "Nome", "E-mail", "Perfis"]
        : type === "alunos"
          ? ["Aluno", "Matrícula", "Curso"]
          : ["Professor", "Departamento", "Área de pesquisa"];
  const cells = (x) =>
    type === "cursos"
      ? [x.nome, x.codigo, x.coordenador ? name(x.coordenador) : "Não definida"]
      : type === "usuarios"
        ? [
            x.username,
            [x.first_name, x.last_name].filter(Boolean).join(" ") || "—",
            x.email || "—",
            x.groups
              .map((id) => groups.find((g) => g.id === id)?.name || id)
              .join(", ") || "Sem perfil",
          ]
        : type === "alunos"
          ? [name(x.usuario), x.matricula, courseName(x.curso)]
          : [name(x.usuario), x.departamento || "—", x.area_pesquisa || "—"];
  return {
    html:
      heading(
        "Administração",
        "Cadastros acadêmicos",
        "Mantenha os vínculos e os acessos da comunidade acadêmica.",
        button("Novo cadastro", "novo-cadastro", "btn-primary"),
      ) +
      `<nav class="pill-tabs" aria-label="Tipos de cadastro">${["cursos", "usuarios", "alunos", "professores"].map((x) => link(`cadastros?tipo=${x}`, { cursos: "Cursos", usuarios: "Usuários", alunos: "Alunos", professores: "Professores" }[x], x === type ? "active" : "")).join("")}</nav>` +
      panel(
        {
          cursos: "Cursos",
          usuarios: "Contas de usuário",
          alunos: "Perfis de aluno",
          professores: "Perfis de professor",
        }[type],
        items.length
          ? `<div class="table-wrap"><table><thead><tr>${columns.map((x) => `<th>${e(x)}</th>`).join("")}<th>Ações</th></tr></thead><tbody>${items
              .map(
                (x) =>
                  `<tr>${cells(x)
                    .map((v) => `<td>${e(v)}</td>`)
                    .join(
                      "",
                    )}<td><div class="actions">${button("Editar", "editar-cadastro", "btn-secondary btn-sm", `data-id="${x.id}"`)}${button("Excluir", "excluir-cadastro", "btn-danger btn-sm", `data-id="${x.id}"`)}</div></td></tr>`,
              )
              .join("")}</tbody></table></div>`
          : empty(
              "Nenhum cadastro encontrado",
              "Use o botão acima para cadastrar o primeiro registro.",
            ),
      ),
  };
}
function registryForm(id) {
  const { type, items, users, groups } = state.registry;
  const item = id ? items.find((x) => x.id === Number(id)) : {};
  const userLabel = (x) =>
    [x.first_name, x.last_name].filter(Boolean).join(" ") || x.username;
  const selectUser = (name, current, filtered = users) =>
    `<select name="${name}" ${name === "usuario" ? "required" : ""}>${options(filtered, "id", userLabel, current, name === "usuario" ? "Selecione a conta" : "Não definido")}</select>`;
  let html = "";
  if (type === "cursos")
    html = `<label class="full">Nome do curso<input name="nome" required maxlength="150" value="${e(item.nome)}"></label><label>Código<input name="codigo" required maxlength="20" value="${e(item.codigo)}"></label><label>Coordenador${selectUser(
      "coordenador",
      item.coordenador,
      users.filter(
        (u) =>
          u.is_active &&
          u.groups.some(
            (g) => groups.find((x) => x.id === g)?.name === "Coordenadores",
          ),
      ),
    )}</label>`;
  if (type === "usuarios")
    html = `<label>Nome de usuário<input name="username" required maxlength="150" value="${e(item.username)}" autocomplete="off"></label><label>E-mail<input name="email" type="email" value="${e(item.email)}"></label><label>Nome<input name="first_name" maxlength="150" value="${e(item.first_name)}"></label><label>Sobrenome<input name="last_name" maxlength="150" value="${e(item.last_name)}"></label><label class="full">${id ? "Nova senha (opcional)" : "Senha inicial"}<input name="password" type="password" ${id ? "" : "required"} autocomplete="new-password"><small class="help">Use uma senha longa, evitando dados pessoais e sequências simples.</small></label><label class="full">Perfis de acesso<select name="groups" multiple size="3">${groups.map((g) => `<option value="${g.id}" ${item.groups?.includes(g.id) ? "selected" : ""}>${e(g.name)}</option>`).join("")}</select><small class="help">É possível atribuir mais de um perfil.</small></label><label class="full"><input name="is_active" type="checkbox" ${item.is_active !== false ? "checked" : ""}> Conta ativa</label>`;
  if (type === "alunos")
    html = `<label class="full">Conta do aluno${selectUser("usuario", item.usuario)}</label><label>Matrícula<input name="matricula" maxlength="50" required value="${e(item.matricula)}"></label><label>Curso<select name="curso" required>${options(state.courses, "id", (x) => x.nome, item.curso, "Selecione")}</select></label><label class="full">Orientador atual<select name="orientador_atual">${options(state.advisors, "id", (x) => advisorName(x.id), item.orientador_atual, "Não definido")}</select></label>`;
  if (type === "professores")
    html = `<label class="full">Conta do professor${selectUser("usuario", item.usuario)}</label><label class="full">Departamento<input name="departamento" maxlength="150" value="${e(item.departamento)}"></label><label class="full">Área de pesquisa<input name="area_pesquisa" maxlength="250" value="${e(item.area_pesquisa)}"></label>`;
  openModal(
    id ? "Editar cadastro" : "Novo cadastro",
    `<div class="form-grid">${html}</div>`,
    async (fd) => {
      const data = Object.fromEntries(fd);
      if (type === "usuarios") {
        data.groups = fd.getAll("groups").map(Number);
        data.is_active = fd.has("is_active");
        if (!data.password) delete data.password;
      }
      for (const key of ["coordenador", "usuario", "curso", "orientador_atual"])
        if (key in data) data[key] = data[key] ? Number(data[key]) : null;
      await request(`/api/${type}/${id ? `${id}/` : ""}`, {
        method: id ? "PATCH" : "POST",
        body: data,
      });
      await lookup();
      toast("Cadastro salvo.");
      route();
    },
  );
}
async function operation(query) {
  if (!admin())
    throw { status: 403, data: { detail: "Área reservada à administração." } };
  const type = query.get("tipo") === "eventos" ? "eventos" : "auditoria";
  const page = Number(query.get("page") || 1);
  const data = await request(`/api/${type}/?page=${page}`);
  const html =
    type === "eventos"
      ? `<table><thead><tr><th>Evento</th><th>Criado em</th><th>Situação</th><th>Ações</th></tr></thead><tbody>${data.results.map((x) => `<tr><td>${e(x.tipo.replaceAll("_", " "))}<small class="block">#${x.id} · ${x.tentativas} tentativas</small></td><td>${date(x.criado_em, true)}</td><td>${x.processado_em ? '<span class="badge green">Concluído</span>' : x.erro ? `<span class="badge red">Falha: ${e(x.erro)}</span>` : '<span class="badge amber">Pendente</span>'}</td><td>${!x.processado_em ? button("Tentar novamente", "repetir-evento", "btn-secondary btn-sm", `data-id="${x.id}"`) : ""}</td></tr>`).join("")}</tbody></table>`
      : `<table><thead><tr><th>Ação</th><th>Registro</th><th>Data e hora</th><th>Detalhes</th></tr></thead><tbody>${data.results.map((x) => `<tr><td>${e(x.acao.replaceAll("_", " "))}<small class="block">${x.ator ? `Responsável: ${e(x.ator_nome || `#${x.ator}`)}` : "Sistema"}</small></td><td>${e(x.entidade)} #${x.registro_id}</td><td>${date(x.criado_em, true)}</td><td><details><summary>Ver alterações</summary><pre class="audit-data">${e(JSON.stringify(x.detalhes, null, 2))}</pre></details></td></tr>`).join("")}</tbody></table>`;
  return {
    html:
      heading(
        "Acompanhamento operacional",
        "Histórico e processamento",
        "Consulte alterações e acompanhe o processamento das tarefas.",
      ) +
      `<nav class="pill-tabs" aria-label="Acompanhamento">${link("operacao?tipo=auditoria", "Histórico de alterações", type === "auditoria" ? "active" : "")}${link("operacao?tipo=eventos", "Eventos e tarefas", type === "eventos" ? "active" : "")}</nav>` +
      panel(
        type === "auditoria" ? "Auditoria" : "Eventos",
        data.results.length
          ? `<div class="table-wrap">${html}</div>`
          : empty(
              "Nenhum registro nesta página",
              "Os registros de acompanhamento aparecerão aqui.",
            ),
      ) +
      pagination(data, "operacao", new URLSearchParams({ tipo: type, page }), [
        "registro encontrado",
        "registros encontrados",
      ]),
  };
}
const actions = {
  menu: () => {
    const sidebar = document.querySelector("#sidebar");
    const open = sidebar.classList.toggle("open");
    document.querySelector(".mobile-backdrop")?.classList.toggle("open", open);
    document
      .querySelector(".mobile-menu")
      ?.setAttribute("aria-expanded", String(open));
  },
  atualizar: () => (state.ready ? route() : start()),
  "fechar-modal": () => closeModal(),
  logout: () =>
    confirm(
      "Sair do sistema?",
      "Você poderá continuar explorando o acervo público.",
      async () => {
        await request("/api/conta/", { method: "DELETE" });
        state.user = null;
        state.externalToken = "";
        state.currentDefense = null;
        state.registry = null;
        go("acervo");
      },
      "Sair",
    ),
  "mostrar-senha": (button) => {
    const input = button.parentElement.querySelector("input");
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    button.textContent = show ? "Ocultar" : "Mostrar";
    button.setAttribute("aria-label", show ? "Ocultar senha" : "Mostrar senha");
  },
  download: async (button) => {
    await download(button.dataset.path, button.dataset.name);
  },
  submeter: (button) =>
    confirm(
      "Submeter ao orientador?",
      "Confira o título, o PDF e a orientação. Após a submissão, o rascunho não poderá mais ser editado.",
      async () => {
        await request(`/api/monografias/${button.dataset.id}/submeter/`, {
          method: "POST",
          body: {},
        });
        toast("Monografia submetida ao orientador.");
        route();
      },
      "Submeter monografia",
    ),
  aprovar: (button) =>
    confirm(
      "Aprovar submissão?",
      "Esta aprovação permite preparar a banca. Ela não representa aprovação final em defesa nem autorização de publicação.",
      async () => {
        await request(`/api/monografias/${button.dataset.id}/aprovar/`, {
          method: "POST",
          body: {},
        });
        toast("Submissão aprovada.");
        route();
      },
      "Aprovar submissão",
    ),
  "excluir-trabalho": (button) =>
    confirm(
      "Excluir rascunho?",
      "Esta ação remove o rascunho do sistema e não pode ser desfeita.",
      async () => {
        await request(`/api/monografias/${button.dataset.id}/`, {
          method: "DELETE",
        });
        toast("Rascunho excluído.");
        go("trabalhos");
      },
      "Excluir rascunho",
    ),
  "nova-banca": (button) => defenseForm(button.dataset.id),
  "editar-banca": () =>
    defenseForm(state.currentDefense.b.monografia, state.currentDefense.b),
  agendar: (button) =>
    confirm(
      "Confirmar o agendamento?",
      "Todos os membros devem ter confirmado disponibilidade. O sistema verificará o intervalo e possíveis conflitos antes de agendar.",
      async () => {
        await request(`/api/bancas/${button.dataset.id}/agendar/`, {
          method: "POST",
          body: {},
        });
        toast("Banca agendada. As notificações serão processadas.");
        route();
      },
      "Agendar defesa",
    ),
  "cancelar-banca": (button) =>
    confirm(
      "Cancelar esta banca?",
      "Os convites de acesso serão revogados. Bancas com avaliações registradas não podem ser canceladas.",
      async () => {
        await request(`/api/bancas/${button.dataset.id}/cancelar/`, {
          method: "POST",
          body: {},
        });
        toast("Banca cancelada.");
        route();
      },
      "Cancelar banca",
    ),
  convidar: (button) => inviteForm(button.dataset.id),
  "confirmar-membro": (button) =>
    confirm(
      "Confirmar disponibilidade?",
      "Confirme que você pode participar no intervalo informado na banca.",
      async () => {
        await request(`/api/membros/${button.dataset.id}/confirmar/`, {
          method: "POST",
          body: {},
        });
        toast("Disponibilidade confirmada.");
        route();
      },
      "Confirmar disponibilidade",
    ),
  "remover-membro": (button) =>
    confirm(
      "Remover este convite?",
      "A pessoa deixará de integrar esta proposta de banca.",
      async () => {
        await request(`/api/membros/${button.dataset.id}/`, {
          method: "DELETE",
        });
        toast("Convite removido.");
        route();
      },
      "Remover convite",
    ),
  "revogar-token": (button) =>
    confirm(
      "Revogar acesso temporário?",
      "O convidado não poderá mais usar o código de acesso atual.",
      async () => {
        await request(`/api/membros/${button.dataset.id}/revogar/`, {
          method: "POST",
          body: {},
        });
        toast("Acesso revogado.");
        route();
      },
      "Revogar acesso",
    ),
  "renovar-token": async (button) => {
    const result = await request(`/api/membros/${button.dataset.id}/renovar/`, {
      method: "POST",
      body: {},
    });
    showToken(result.token_temporario, result.expira_em);
    state.refreshOnClose = true;
  },
  "copiar-token": async () => {
    const text = document.querySelector("#generated-token")?.textContent;
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      toast("Código copiado.");
    } else toast("Selecione o código exibido e copie manualmente.");
  },
  avaliar: (button) => evaluationForm(button.dataset.id),
  "enviar-documento": (button) => uploadDocument(button.dataset.id),
  "validar-documento": (button) =>
    confirm(
      "Validar este documento?",
      "Confirme que você abriu e conferiu o arquivo. No termo, verifique a autorização e a assinatura. A validação pode concluir a publicação automaticamente.",
      async () => {
        await request(`/api/documentos/${button.dataset.id}/validar/`, {
          method: "POST",
          body: {},
        });
        toast("Documento validado.");
        route();
      },
      "Validar documento",
    ),
  "confirmar-externo": () =>
    confirm(
      "Confirmar disponibilidade?",
      "Confirme que pode participar no intervalo informado.",
      async () => {
        await request("/api/externo/", {
          method: "POST",
          body: { acao: "confirmar" },
          token: state.externalToken,
        });
        toast("Disponibilidade confirmada.");
      },
    ),
  "pdf-externo": async () =>
    download("/api/externo/pdf/", "monografia.pdf", state.externalToken),
  "avaliar-externo": (button) => evaluationForm(button.dataset.id, true),
  "sair-externo": () => {
    state.externalToken = "";
    state.externalData = null;
    route();
  },
  "novo-cadastro": () => registryForm(),
  "editar-cadastro": (button) => registryForm(button.dataset.id),
  "excluir-cadastro": (button) =>
    confirm(
      "Excluir este cadastro?",
      "Registros com vínculos acadêmicos poderão ter a exclusão bloqueada para preservar o histórico.",
      async () => {
        await request(`/api/${state.registry.type}/${button.dataset.id}/`, {
          method: "DELETE",
        });
        await lookup();
        toast("Cadastro excluído.");
        route();
      },
      "Excluir cadastro",
    ),
  "repetir-evento": (button) =>
    confirm(
      "Liberar nova tentativa?",
      "Verifique a causa da falha antes de tentar novamente. O processamento será retomado em segundo plano.",
      async () => {
        await request(`/api/eventos/${button.dataset.id}/repetir/`, {
          method: "POST",
          body: {},
        });
        toast("Nova tentativa liberada.");
        route();
      },
      "Liberar tentativa",
    ),
};
document.addEventListener("click", async (event) => {
  const target = event.target.closest("[data-action]");
  if (!target || !actions[target.dataset.action]) return;
  event.preventDefault();
  if (target.disabled || target.dataset.busy) return;
  target.dataset.busy = "1";
  if (target.tagName === "BUTTON") target.disabled = true;
  try {
    await actions[target.dataset.action](target);
  } catch (error) {
    showError(error);
  } finally {
    delete target.dataset.busy;
    if (target.tagName === "BUTTON") target.disabled = false;
  }
});
document.addEventListener("change", (event) => {
  if (event.target.id === "invite-type") {
    const external = event.target.value === "externo";
    document.querySelector("#invite-internal").hidden = external;
    document.querySelector("#invite-external").hidden = !external;
    const form = event.target.form;
    form.elements.usuario.required = !external;
    form.elements.usuario.disabled = external;
    form.elements.nome.required = external;
    form.elements.nome.disabled = !external;
    form.elements.email.required = external;
    form.elements.email.disabled = !external;
  }
});
modal.addEventListener("close", () => {
  if (state.refreshOnClose && !modal.open) {
    state.refreshOnClose = false;
    route();
  }
});
window.addEventListener("hashchange", () => {
  if (modal.open) closeModal();
  document.querySelector("#sidebar").classList.remove("open");
  document.querySelector(".mobile-backdrop")?.classList.remove("open");
  route();
});
async function start() {
  try {
    await Promise.all([account(), lookup()]);
  } catch (error) {
    shell("acervo");
    main.innerHTML =
      errors(error) + button("Tentar novamente", "atualizar", "btn-primary");
    main.setAttribute("aria-busy", "false");
    return;
  }
  state.ready = true;
  await route();
}
// Segredos de acesso externo ficam apenas na memória desta aba.
document.querySelector(".skip-link").addEventListener("click", (event) => {
  event.preventDefault();
  main.focus();
});
start();

document.addEventListener("keydown", (event) => {
  if (
    event.key === "Escape" &&
    !modal.open &&
    document.querySelector("#sidebar").classList.contains("open")
  )
    actions.menu();
});
