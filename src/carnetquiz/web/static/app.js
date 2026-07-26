(() => {
    "use strict";

    const storage = {
        get(key, fallback) {
            try { return localStorage.getItem(key) ?? fallback; } catch (_) { return fallback; }
        },
        set(key, value) {
            try { localStorage.setItem(key, value); } catch (_) {}
        }
    };

    const root = document.documentElement;
    const themeSelect = document.querySelector("#theme-select");
    const savedTheme = storage.get("cq-theme", "system");

    function applyTheme(theme) {
        if (theme === "dark" || theme === "light") root.dataset.theme = theme;
        else delete root.dataset.theme;
        if (themeSelect) themeSelect.value = theme;
    }

    applyTheme(savedTheme);
    themeSelect?.addEventListener("change", () => {
        const theme = themeSelect.value;
        storage.set("cq-theme", theme);
        applyTheme(theme);
    });

    const navToggle = document.querySelector(".nav-toggle");
    const mainNav = document.querySelector("#main-nav");
    const closeNav = () => {
        if (!navToggle || !mainNav) return;
        navToggle.setAttribute("aria-expanded", "false");
        mainNav.classList.remove("is-open");
    };
    navToggle?.addEventListener("click", () => {
        const open = navToggle.getAttribute("aria-expanded") === "true";
        navToggle.setAttribute("aria-expanded", String(!open));
        mainNav?.classList.toggle("is-open", !open);
    });
    mainNav?.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeNav));
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeNav();
    });
    document.addEventListener("click", (event) => {
        if (!mainNav?.classList.contains("is-open")) return;
        if (!mainNav.contains(event.target) && !navToggle?.contains(event.target)) closeNav();
    });

    const soundToggle = document.querySelector("#sound-toggle");
    const soundLabel = soundToggle?.querySelector(".sound-label");
    let soundEnabled = storage.get("cq-sound", "off") === "on";
    const syncSoundControl = () => {
        if (!soundToggle) return;
        soundToggle.setAttribute("aria-pressed", String(soundEnabled));
        soundToggle.title = soundEnabled ? "Silenciar sonidos" : "Activar sonidos";
        if (soundLabel) soundLabel.textContent = soundEnabled ? "Sonido activado" : "Sonido apagado";
    };
    syncSoundControl();
    soundToggle?.addEventListener("click", () => {
        soundEnabled = !soundEnabled;
        storage.set("cq-sound", soundEnabled ? "on" : "off");
        syncSoundControl();
    });

    function playTone(type) {
        if (!soundEnabled || type === "exam") return;
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return;
        try {
            const context = new AudioContext();
            const oscillator = context.createOscillator();
            const gain = context.createGain();
            const now = context.currentTime;
            const correct = type === "correct";
            oscillator.type = correct ? "sine" : "triangle";
            oscillator.frequency.setValueAtTime(correct ? 520 : 180, now);
            if (correct) oscillator.frequency.exponentialRampToValueAtTime(780, now + 0.16);
            else oscillator.frequency.exponentialRampToValueAtTime(120, now + 0.18);
            gain.gain.setValueAtTime(0.0001, now);
            gain.gain.exponentialRampToValueAtTime(0.045, now + 0.015);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.2);
            oscillator.connect(gain);
            gain.connect(context.destination);
            oscillator.start(now);
            oscillator.stop(now + 0.21);
            oscillator.addEventListener("ended", () => context.close().catch(() => {}), { once: true });
        } catch (_) {
            // Audio is optional. Browser policies must never break the quiz.
        }
    }

    const feedback = document.querySelector("[data-feedback]");
    if (feedback) playTone(feedback.dataset.soundResult);

    const answerForm = document.querySelector("[data-answer-form]");
    if (answerForm) {
        const radios = [...answerForm.querySelectorAll("input[type=radio]")];
        const submit = answerForm.querySelector("[data-submit-answer]");
        let submitted = false;
        const syncAnswer = () => {
            if (submit) submit.disabled = !radios.some((radio) => radio.checked);
        };
        radios.forEach((radio) => radio.addEventListener("change", syncAnswer));
        syncAnswer();
        answerForm.addEventListener("submit", (event) => {
            if (submitted || !radios.some((radio) => radio.checked)) {
                if (!radios.some((radio) => radio.checked)) event.preventDefault();
                return;
            }
            submitted = true;
            answerForm.classList.add("is-loading");
            if (submit) {
                submit.disabled = true;
                submit.setAttribute("aria-busy", "true");
            }
        });
        document.addEventListener("keydown", (event) => {
            const target = event.target;
            const tag = target?.tagName;
            const editable = target?.isContentEditable || ["TEXTAREA", "SELECT"].includes(tag) || (tag === "INPUT" && target.type !== "radio");
            if (editable) return;
            if (["1", "2", "3", "4"].includes(event.key)) {
                const radio = radios[Number(event.key) - 1];
                if (radio) {
                    radio.checked = true;
                    radio.dispatchEvent(new Event("change", { bubbles: true }));
                    event.preventDefault();
                }
            } else if (event.key === "Enter" && radios.some((radio) => radio.checked) && !submitted) {
                event.preventDefault();
                if (answerForm.requestSubmit) answerForm.requestSubmit();
                else submit?.click();
            }
        });
    }

    document.querySelectorAll("[data-loading-form]").forEach((form) => {
        form.addEventListener("submit", () => {
            if (form.classList.contains("is-loading")) return;
            form.classList.add("is-loading");
            const button = form.querySelector("button[type=submit]");
            if (button) {
                button.disabled = true;
                button.setAttribute("aria-busy", "true");
            }
        });
    });

    const resultFilters = [...document.querySelectorAll("[data-result-filter]")];
    const resultCards = [...document.querySelectorAll("[data-result-card]")];
    resultFilters.forEach((filter) => {
        filter.addEventListener("click", () => {
            const value = filter.dataset.resultFilter;
            resultFilters.forEach((item) => {
                const active = item === filter;
                item.classList.toggle("is-active", active);
                item.setAttribute("aria-pressed", String(active));
            });
            resultCards.forEach((card) => {
                card.hidden = value !== "all" && card.dataset.resultCard !== value;
            });
        });
    });

    const builder = document.querySelector("[data-test-builder]");
    if (builder) {
        const modeInputs = [...builder.querySelectorAll("input[name=mode]")];
        const countInput = builder.querySelector("#question-count");
        const startInput = builder.querySelector("#test-start");
        const untilInput = builder.querySelector("#test-until");
        const videos = [...builder.querySelectorAll("input[name=video_ids]")];
        const summaryCount = builder.querySelector("[data-summary-count]");
        const summaryMode = builder.querySelector("[data-summary-mode]");
        const summaryVideos = builder.querySelector("[data-summary-videos]");
        const summaryRange = builder.querySelector("[data-summary-range]");
        const modeNames = Object.fromEntries(modeInputs.map((input) => [input.value, input.closest("label")?.querySelector("strong")?.textContent || input.value]));
        const updateBuilder = () => {
            modeInputs.forEach((input) => input.closest("label")?.classList.toggle("is-selected", input.checked));
            if (summaryCount && countInput) summaryCount.textContent = countInput.value || "0";
            const chosenMode = modeInputs.find((input) => input.checked);
            if (summaryMode && chosenMode) summaryMode.textContent = modeNames[chosenMode.value];
            if (summaryVideos) summaryVideos.textContent = String(videos.filter((input) => input.checked).length || "todos");
            if (summaryRange) {
                const start = startInput?.value.trim();
                const until = untilInput?.value.trim();
                summaryRange.textContent = start || until ? `${start || "00:00:00"}–${until || "fin"}` : "Todo el contenido";
            }
        };
        modeInputs.forEach((input) => input.addEventListener("change", updateBuilder));
        [countInput, startInput, untilInput].forEach((input) => input?.addEventListener("input", updateBuilder));
        videos.forEach((input) => input.addEventListener("change", updateBuilder));
        builder.querySelector("[data-select-all]")?.addEventListener("click", () => { videos.forEach((input) => { input.checked = true; }); updateBuilder(); });
        builder.querySelector("[data-select-none]")?.addEventListener("click", () => { videos.forEach((input) => { input.checked = false; }); updateBuilder(); });
        updateBuilder();
    }
})();
