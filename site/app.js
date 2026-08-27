const menuToggle = document.querySelector(".menu-toggle");
const siteNav = document.querySelector(".site-nav");

function closeMenu({ restoreFocus = false } = {}) {
  if (!menuToggle || !siteNav) return;
  menuToggle.setAttribute("aria-expanded", "false");
  siteNav.classList.remove("is-open");
  if (restoreFocus) menuToggle.focus();
}

if (menuToggle && siteNav) {
  menuToggle.addEventListener("click", () => {
    const expanded = menuToggle.getAttribute("aria-expanded") === "true";
    menuToggle.setAttribute("aria-expanded", String(!expanded));
    siteNav.classList.toggle("is-open", !expanded);
  });

  siteNav.addEventListener("click", (event) => {
    if (event.target.closest("a")) closeMenu();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && siteNav.classList.contains("is-open")) {
      closeMenu({ restoreFocus: true });
    }
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 920) closeMenu();
  });
}

const policyLab = document.querySelector("[data-policy-lab]");

if (policyLab) {
  const commandButtons = [...policyLab.querySelectorAll(".lab-command")];
  const decisionPanel = policyLab.querySelector(".lab-decision");
  const riskSegments = [...policyLab.querySelectorAll(".risk-meter span")];

  const riskLevels = {
    "LOW RISK": 1,
    "MEDIUM RISK": 2,
    BLOCKED: 4,
  };

  function setText(selector, value) {
    const target = policyLab.querySelector(selector);
    if (target) target.textContent = value;
  }

  function updateDecision(button) {
    commandButtons.forEach((item) => {
      const selected = item === button;
      item.classList.toggle("is-active", selected);
      item.setAttribute("aria-pressed", String(selected));
    });

    setText("[data-output-decision]", button.dataset.decision);
    setText("[data-output-command]", `$ ${button.dataset.command}`);
    setText("[data-output-risk]", button.dataset.risk);
    setText("[data-output-mode]", button.dataset.mode);
    setText("[data-output-network]", button.dataset.network);
    setText("[data-output-approval]", button.dataset.approval);
    setText("[data-output-reason]", button.dataset.reason);

    const litSegments = riskLevels[button.dataset.risk] || 1;
    riskSegments.forEach((segment, index) => {
      segment.classList.toggle("is-lit", index < litSegments);
    });

    if (decisionPanel) {
      decisionPanel.dataset.state =
        button.dataset.risk === "BLOCKED"
          ? "blocked"
          : button.dataset.risk === "MEDIUM RISK"
            ? "planned"
            : "allowed";
    }
  }

  commandButtons.forEach((button) => {
    button.addEventListener("click", () => updateDecision(button));
  });
}

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

document.querySelectorAll("[data-copy-target]").forEach((button) => {
  button.addEventListener("click", async () => {
    const target = document.getElementById(button.dataset.copyTarget);
    const label = button.querySelector("[data-copy-label]");
    if (!target || !label) return;

    const original = label.textContent;
    try {
      await copyText(target.textContent.trim());
      label.textContent = "Copied";
    } catch {
      label.textContent = "Select text";
    }
    window.setTimeout(() => {
      label.textContent = original;
    }, 1800);
  });
});

const docSections = [...document.querySelectorAll(".docs-block[id]")];
const docLinks = [...document.querySelectorAll(".docs-sidebar a[href^='#']")];

if (docSections.length && docLinks.length && "IntersectionObserver" in window) {
  const sectionObserver = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;
      docLinks.forEach((link) => {
        link.setAttribute("aria-current", String(link.hash === `#${visible.target.id}`));
      });
    },
    { rootMargin: "-15% 0px -70%", threshold: [0, 0.2, 0.5] },
  );
  docSections.forEach((section) => sectionObserver.observe(section));
}
