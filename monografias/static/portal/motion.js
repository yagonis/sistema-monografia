// Movimento do portal com GSAP (vendor/gsap.min.js, carregado antes do app).
// Sem GSAP ou com prefers-reduced-motion: reduce, todas as funções viram no-op
// e o conteúdo aparece imediatamente.
const gsap = window.gsap;
let reduzir = true;
let rota = null;

if (gsap) {
  gsap.defaults({ duration: 0.24, ease: "power2.out", overwrite: "auto" });
  gsap.matchMedia().add(
    {
      animar: "(prefers-reduced-motion: no-preference)",
      reduzir: "(prefers-reduced-motion: reduce)",
    },
    (contexto) => {
      reduzir = contexto.conditions.reduzir;
    },
  );
}

const ativo = () => Boolean(gsap) && !reduzir;
const LIMPAR = "transform,opacity,visibility";

// Um único momento por rota: a página entra como um bloco, a lista de registros
// desce em sequência curta e os números/barras chegam ao valor real.
export const motion = {
  // Encerra a animação da rota anterior antes de trocar o conteúdo.
  // progress(1) aplica o estado final (e clearProps) no <main>, que é reaproveitado entre rotas.
  sair() {
    rota?.progress(1).kill();
    rota = null;
  },

  entrar(raiz) {
    if (!ativo()) return;
    const registros = [...raiz.querySelectorAll(".result-card, .panel tbody tr, .panel .list-item")].slice(0, 8);
    const numeros = raiz.querySelectorAll(".ledger-item strong[data-count]");
    const barras = raiz.querySelectorAll(".bar-fill");
    rota = gsap
      .timeline({ defaults: { clearProps: LIMPAR } })
      .from(raiz, { autoAlpha: 0, y: 6, duration: 0.2 })
      .from(registros, { autoAlpha: 0, y: 8, duration: 0.22, stagger: 0.035 }, 0.08);
    numeros.forEach((el) => {
      const alvo = Number(el.dataset.count) || 0;
      if (!alvo) return;
      const contador = { v: 0 };
      el.textContent = "0";
      rota.to(contador, {
        v: alvo,
        duration: 0.6,
        ease: "power1.out",
        onUpdate: () => (el.textContent = Math.round(contador.v)),
        onComplete: () => (el.textContent = alvo),
      }, 0.05);
    });
    if (barras.length)
      rota.from(barras, { scaleX: 0, transformOrigin: "left center", duration: 0.45, ease: "power2.out", stagger: 0.04 }, 0.12);
  },

  modal(dialogo) {
    if (!ativo()) return;
    gsap.fromTo(
      dialogo,
      { autoAlpha: 0, y: 12, scale: 0.985 },
      { autoAlpha: 1, y: 0, scale: 1, duration: 0.22, clearProps: LIMPAR },
    );
  },

  aviso(el) {
    if (!ativo()) return;
    gsap.from(el, { autoAlpha: 0, x: 24, duration: 0.24, clearProps: LIMPAR });
  },

  // Resolve quando o aviso pode ser removido do DOM.
  esconder(el) {
    if (!ativo()) return Promise.resolve();
    return new Promise((fim) =>
      gsap.to(el, { autoAlpha: 0, y: 8, duration: 0.18, ease: "power1.in", onComplete: fim }),
    );
  },
};
