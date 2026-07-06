(function (window, document) {
  "use strict";

  const upgradeButtons = Array.from(document.querySelectorAll(".btn-upgrade")).filter((button) =>
    /upgrade to pro/i.test(button.textContent || "")
  );

  if (!upgradeButtons.length || document.getElementById("pro-upgrade-modal")) return;

  const benefits = [
    {
      icon: "VIP",
      title: "VIP Morning Brief",
      body: "Receive a pre-market briefing every day to catch the latest hotspots and opportunities.",
    },
    {
      icon: "AI",
      title: "Advanced Model Analysis",
      body: "Use higher-tier models for analysis, including GPT-5.5 and Fable 5.",
    },
    {
      icon: "FLOW",
      title: "Inflow / Outflow Index",
      body: "Understand capital flow changes across individual funds and the broader market.",
    },
    {
      icon: "AD",
      title: "Ad-Free Experience",
      body: "Enjoy a cleaner member experience without promotional interruptions.",
    },
    {
      icon: "NEW",
      title: "Early Access to New Features",
      body: "Join the inner circle, send feedback directly to developers, and try new features first.",
    },
  ];

  const modal = document.createElement("div");
  modal.id = "pro-upgrade-modal";
  modal.className = "pro-modal";
  modal.hidden = true;
  modal.innerHTML = `
    <div class="pro-modal__backdrop" data-pro-cancel></div>
    <section class="pro-modal__panel" role="dialog" aria-modal="true" aria-labelledby="pro-modal-title">
      <button type="button" class="pro-modal__cancel" data-pro-cancel aria-label="Cancel">Cancel</button>
      <header class="pro-modal__hero">
        <div class="pro-modal__avatar" aria-hidden="true">FM</div>
        <div>
          <p class="pro-modal__eyebrow">FundMaster Pro</p>
          <h2 id="pro-modal-title" class="pro-modal__title">Upgrade Your Membership</h2>
          <p class="pro-modal__sub">You are not a Pro member yet.</p>
        </div>
      </header>
      <div class="pro-modal__plans" role="list" aria-label="Membership plans">
        <button type="button" class="pro-plan pro-plan--active" data-plan-price="588">
          <span class="pro-plan__badge">Best Value</span>
          <span class="pro-plan__name">Annual Pro</span>
          <strong class="pro-plan__price">¥ 588</strong>
          <span class="pro-plan__note">Only ¥1.6 / day</span>
        </button>
        <button type="button" class="pro-plan" data-plan-price="348">
          <span class="pro-plan__name">Semiannual Pro</span>
          <strong class="pro-plan__price">¥ 348</strong>
          <span class="pro-plan__note">Only ¥1.9 / day</span>
        </button>
      </div>
      <div class="pro-modal__section-title"><span></span> Pro Member Benefits <span></span></div>
      <ul class="pro-benefits">
        ${benefits
          .map(
            (item) => `
              <li class="pro-benefit">
                <span class="pro-benefit__icon">${item.icon}</span>
                <div>
                  <h3>${item.title}</h3>
                  <p>${item.body}</p>
                </div>
                <span class="pro-benefit__arrow" aria-hidden="true">›</span>
              </li>
            `
          )
          .join("")}
      </ul>
      <button type="button" class="pro-modal__confirm" data-pro-confirm>¥ 588 · Upgrade Now</button>
      <p class="pro-modal__status" hidden></p>
    </section>
  `;

  document.body.appendChild(modal);

  const panel = modal.querySelector(".pro-modal__panel");
  const status = modal.querySelector(".pro-modal__status");
  const confirmButton = modal.querySelector("[data-pro-confirm]");

  function setPrice(price) {
    confirmButton.textContent = `¥ ${price} · Upgrade Now`;
  }

  function openModal() {
    modal.hidden = false;
    document.body.classList.add("pro-modal-open");
    status.hidden = true;
    panel.focus();
  }

  function closeModal() {
    modal.hidden = true;
    document.body.classList.remove("pro-modal-open");
  }

  upgradeButtons.forEach((button) => {
    button.addEventListener("click", openModal);
  });

  modal.querySelectorAll("[data-pro-cancel]").forEach((button) => {
    button.addEventListener("click", closeModal);
  });

  modal.querySelectorAll(".pro-plan").forEach((plan) => {
    plan.addEventListener("click", () => {
      modal.querySelectorAll(".pro-plan").forEach((item) => item.classList.remove("pro-plan--active"));
      plan.classList.add("pro-plan--active");
      setPrice(plan.dataset.planPrice || "588");
    });
  });

  confirmButton.addEventListener("click", () => {
    const activePlan = modal.querySelector(".pro-plan--active .pro-plan__name");
    status.textContent = `${activePlan ? activePlan.textContent : "Pro"} selected. Membership upgrade confirmed for demo.`;
    status.hidden = false;
    confirmButton.textContent = "Confirmed";
    window.setTimeout(() => {
      confirmButton.textContent = `¥ ${modal.querySelector(".pro-plan--active").dataset.planPrice || "588"} · Upgrade Now`;
      closeModal();
    }, 900);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) closeModal();
  });
})(window, document);
