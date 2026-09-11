(() => {
  "use strict";

  const els = {
    regionSelect: document.getElementById("region-select"),
    modeSelect: document.getElementById("mode-select"),
    nameSelect: document.getElementById("name-select"),
    groupSelect: document.getElementById("group-select"),
    restartBtn: document.getElementById("restart-btn"),
    progressText: document.getElementById("progress-text"),
    scoreText: document.getElementById("score-text"),
    progressBarFill: document.getElementById("progress-bar-fill"),
    quizCard: document.getElementById("quiz-card"),
    galleryScroll: document.getElementById("gallery-scroll"),
    galleryDots: document.getElementById("gallery-dots"),
    galleryCaption: document.getElementById("gallery-caption"),
    galleryPrev: document.getElementById("gallery-prev"),
    galleryNext: document.getElementById("gallery-next"),
    hintBtn: document.getElementById("hint-btn"),
    hintBox: document.getElementById("hint-box"),
    promptText: document.getElementById("prompt-text"),
    mcOptions: document.getElementById("mc-options"),
    fillForm: document.getElementById("fill-form"),
    fillInput: document.getElementById("fill-input"),
    flashcardControls: document.getElementById("flashcard-controls"),
    revealBtn: document.getElementById("reveal-btn"),
    feedback: document.getElementById("feedback"),
    nextBtn: document.getElementById("next-btn"),
    summary: document.getElementById("summary"),
    summaryScore: document.getElementById("summary-score"),
    missedList: document.getElementById("missed-list"),
    retryMissedBtn: document.getElementById("retry-missed-btn"),
    restartAllBtn: document.getElementById("restart-all-btn"),
    creditsLink: document.getElementById("credits-link"),
    creditsModal: document.getElementById("credits-modal"),
    creditsClose: document.getElementById("credits-close"),
    creditsList: document.getElementById("credits-list"),
  };

  let allSpecies = [];
  let attributions = {};
  let deck = [];
  let currentIndex = 0;
  let score = 0;
  let answered = 0;
  let missed = [];
  let currentAnswered = false;

  const SETTINGS_KEY = "treeid-settings-v1";

  const CATEGORY_LABELS = {
    leaf: "Leaf",
    flower: "Flower",
    fruit: "Fruit / Cone",
    bark: "Bark",
    trunk: "Trunk",
    tree: "Full Tree",
  };
  const CATEGORY_ORDER = ["leaf", "flower", "fruit", "bark", "trunk", "tree"];

  function loadSettings() {
    try {
      const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}");
      if (saved.region) els.regionSelect.value = saved.region;
      if (saved.mode) els.modeSelect.value = saved.mode;
      if (saved.name) els.nameSelect.value = saved.name;
      if (saved.group) els.groupSelect.value = saved.group;
    } catch (e) { /* ignore corrupt settings */ }
  }

  function saveSettings() {
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify({
        region: els.regionSelect.value,
        mode: els.modeSelect.value,
        name: els.nameSelect.value,
        group: els.groupSelect.value,
      }));
    } catch (e) { /* storage unavailable, ignore */ }
  }

  function shuffle(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function normalize(str) {
    return str
      .toLowerCase()
      .replace(/\([^)]*\)/g, " ")   // drop parenthetical alt names
      .replace(/[^a-z0-9\s-]/g, "") // strip punctuation
      .replace(/\s+/g, " ")
      .trim();
  }

  function acceptableAnswers(species) {
    // Accept the common name, its bare form without a parenthetical alt,
    // the parenthetical alt name itself, and the scientific name.
    const answers = new Set();
    answers.add(normalize(species.common));
    const parenMatch = species.common.match(/\(([^)]+)\)/);
    if (parenMatch) {
      answers.add(normalize(parenMatch[1]));
      answers.add(normalize(species.common.replace(/\([^)]*\)/, "")));
    }
    answers.add(normalize(species.scientific));
    return answers;
  }

  function speciesInRegion(species, region) {
    return region === "all" || (species.region || []).includes(region);
  }

  function buildDeck(sourceList) {
    const region = els.regionSelect.value;
    const group = els.groupSelect.value;
    const byRegion = sourceList.filter(s => speciesInRegion(s, region));
    const filtered = group === "all" ? byRegion : byRegion.filter(s => s.group === group);
    deck = shuffle(filtered);
    currentIndex = 0;
    score = 0;
    answered = 0;
    missed = [];
    updateGroupLabels();
    els.summary.classList.add("hidden");
    els.quizCard.classList.remove("hidden");
    renderCard();
  }

  function updateGroupLabels() {
    const region = els.regionSelect.value;
    const byRegion = allSpecies.filter(s => speciesInRegion(s, region));

    const regionOpt = els.regionSelect.selectedOptions[0];
    if (els.regionSelect.value !== "all") {
      const countAll = allSpecies.filter(s => speciesInRegion(s, els.regionSelect.value)).length;
      const base = regionOpt.textContent.replace(/\s*\([^)]*\)\s*$/, "").trim();
      regionOpt.dataset.baseLabel = regionOpt.dataset.baseLabel || base;
      regionOpt.textContent = `${regionOpt.dataset.baseLabel} (${countAll})`;
    }

    ["all", "broadleaf", "conifer", "palm"].forEach(g => {
      const opt = Array.from(els.groupSelect.options).find(o => o.value === g);
      if (!opt) return;
      const count = g === "all" ? byRegion.length : byRegion.filter(s => s.group === g).length;
      const base = opt.textContent.replace(/ \(\d+\)$/, "");
      opt.textContent = `${base} (${count})`;
    });
  }

  function pickDistractors(correct, count) {
    const sameFamily = allSpecies.filter(s => s.id !== correct.id && s.family === correct.family);
    const sameGroup = allSpecies.filter(s => s.id !== correct.id && s.group === correct.group && s.family !== correct.family);
    const rest = allSpecies.filter(s => s.id !== correct.id && s.group !== correct.group);

    const pool = shuffle(sameFamily).concat(shuffle(sameGroup)).concat(shuffle(rest));
    return pool.slice(0, count);
  }

  function currentNameField() {
    return els.nameSelect.value === "scientific" ? "scientific" : "common";
  }

  function displayName(species) {
    return species[currentNameField()];
  }

  function renderCard() {
    currentAnswered = false;
    const species = deck[currentIndex];
    if (!species) {
      showSummary();
      return;
    }

    els.progressText.textContent = `Card ${currentIndex + 1} / ${deck.length}`;
    els.progressBarFill.style.width = `${(currentIndex / deck.length) * 100}%`;

    renderGallery(species);

    els.hintBox.classList.add("hidden");
    els.hintBox.textContent = "";

    els.feedback.classList.add("hidden");
    els.feedback.textContent = "";
    els.nextBtn.classList.add("hidden");

    const mode = els.modeSelect.value;
    els.mcOptions.classList.add("hidden");
    els.fillForm.classList.add("hidden");
    els.flashcardControls.classList.add("hidden");

    if (mode === "flashcard") {
      els.scoreText.textContent = `Cards reviewed: ${answered} / ${deck.length}`;
      els.promptText.textContent = "Identify this species, then reveal the answer.";
      els.flashcardControls.classList.remove("hidden");
      els.revealBtn.disabled = false;
    } else if (mode === "multiple") {
      els.scoreText.textContent = `Score: ${score} / ${answered}`;
      const nameLabel = currentNameField() === "scientific" ? "scientific name" : "common name";
      els.promptText.textContent = `What is the ${nameLabel} of this tree/leaf?`;
      els.mcOptions.classList.remove("hidden");
      renderMultipleChoice(species);
    } else {
      els.scoreText.textContent = `Score: ${score} / ${answered}`;
      const nameLabel = currentNameField() === "scientific" ? "scientific name" : "common name";
      els.promptText.textContent = `What is the ${nameLabel} of this tree/leaf?`;
      els.fillForm.classList.remove("hidden");
      els.fillInput.value = "";
      els.fillInput.disabled = false;
      els.fillInput.focus();
    }
  }

  function availableCategories(species) {
    const attrs = attributions[species.id] || {};
    return CATEGORY_ORDER.filter(cat => attrs[cat]);
  }

  function renderGallery(species) {
    const cats = availableCategories(species);
    const attrs = attributions[species.id] || {};

    els.galleryScroll.innerHTML = "";
    els.galleryDots.innerHTML = "";

    if (cats.length === 0) {
      const slide = document.createElement("div");
      slide.className = "gallery-slide gallery-empty";
      slide.textContent = "📷 Photos coming soon for this species";
      els.galleryScroll.appendChild(slide);
      els.galleryCaption.innerHTML = "";
      els.galleryPrev.disabled = true;
      els.galleryNext.disabled = true;
      return;
    }

    cats.forEach((cat, i) => {
      const slide = document.createElement("div");
      slide.className = "gallery-slide";
      slide.dataset.category = cat;

      const img = document.createElement("img");
      img.src = `images/${species.id}/${cat}.jpg`;
      img.alt = `${CATEGORY_LABELS[cat]} of ${species.common}`;
      img.loading = i === 0 ? "eager" : "lazy";
      slide.appendChild(img);

      const label = document.createElement("span");
      label.className = "gallery-slide-label";
      label.textContent = CATEGORY_LABELS[cat];
      slide.appendChild(label);

      els.galleryScroll.appendChild(slide);

      const dot = document.createElement("button");
      dot.className = "gallery-dot" + (i === 0 ? " active" : "");
      dot.setAttribute("aria-label", `Show ${CATEGORY_LABELS[cat]} photo`);
      dot.addEventListener("click", () => scrollToSlide(i));
      els.galleryDots.appendChild(dot);
    });

    updateGalleryCaption(species, cats, 0);
    updateGalleryNav(0, cats.length);
    els.galleryScroll.scrollLeft = 0;

    els.galleryScroll.onscroll = () => {
      const width = els.galleryScroll.clientWidth || 1;
      const idx = Math.round(els.galleryScroll.scrollLeft / width);
      Array.from(els.galleryDots.children).forEach((d, i) => d.classList.toggle("active", i === idx));
      updateGalleryCaption(species, cats, idx);
      updateGalleryNav(idx, cats.length);
    };
  }

  function scrollToSlide(index) {
    const width = els.galleryScroll.clientWidth;
    els.galleryScroll.scrollTo({ left: width * index, behavior: "smooth" });
  }

  function updateGalleryNav(idx, total) {
    els.galleryPrev.disabled = idx <= 0;
    els.galleryNext.disabled = idx >= total - 1;
  }

  function galleryStep(delta) {
    const width = els.galleryScroll.clientWidth || 1;
    const idx = Math.round(els.galleryScroll.scrollLeft / width);
    const total = els.galleryDots.children.length;
    const next = Math.min(Math.max(idx + delta, 0), total - 1);
    scrollToSlide(next);
  }

  function updateGalleryCaption(species, cats, idx) {
    const cat = cats[idx];
    const attr = (attributions[species.id] || {})[cat];
    if (!attr) {
      els.galleryCaption.innerHTML = "";
      return;
    }
    els.galleryCaption.innerHTML =
      `${CATEGORY_LABELS[cat]} photo: ${escapeHtml(attr.author)} (${escapeHtml(attr.license)}) — ` +
      `<a href="${attr.sourcePage}" target="_blank" rel="noopener">Wikimedia Commons</a>`;
  }

  function renderMultipleChoice(species) {
    const distractors = pickDistractors(species, 3);
    const options = shuffle([species, ...distractors]);
    els.mcOptions.innerHTML = "";
    options.forEach(opt => {
      const btn = document.createElement("button");
      btn.className = "mc-option";
      btn.textContent = displayName(opt);
      btn.addEventListener("click", () => handleMultipleChoiceAnswer(btn, opt, species));
      els.mcOptions.appendChild(btn);
    });
  }

  function handleMultipleChoiceAnswer(btn, chosen, correctSpecies) {
    if (currentAnswered) return;
    currentAnswered = true;
    answered++;

    const isCorrect = chosen.id === correctSpecies.id;
    if (isCorrect) score++;
    else missed.push(correctSpecies);

    Array.from(els.mcOptions.children).forEach(child => {
      child.disabled = true;
      if (child === btn) {
        child.classList.add(isCorrect ? "correct" : "incorrect");
      }
      if (child.textContent === displayName(correctSpecies) && !isCorrect) {
        child.classList.add("correct");
      }
    });

    showFeedback(isCorrect, correctSpecies);
  }

  function handleFillSubmit(e) {
    e.preventDefault();
    if (currentAnswered) return;
    const species = deck[currentIndex];
    const userValue = normalize(els.fillInput.value);
    if (!userValue) return;

    currentAnswered = true;
    answered++;
    els.fillInput.disabled = true;

    const accepted = acceptableAnswers(species);
    const isCorrect = accepted.has(userValue);
    if (isCorrect) score++;
    else missed.push(species);

    showFeedback(isCorrect, species);
  }

  function revealAnswer() {
    if (currentAnswered) return;
    currentAnswered = true;
    answered++;
    els.revealBtn.disabled = true;
    const species = deck[currentIndex];
    els.scoreText.textContent = `Cards reviewed: ${answered} / ${deck.length}`;

    els.feedback.classList.remove("hidden", "correct", "incorrect");
    els.feedback.classList.add("reveal");

    const attr = (attributions[species.id] || {}).leaf;
    const creditHtml = attr
      ? `<a class="credit-link" href="${attr.sourcePage}" target="_blank" rel="noopener">Leaf photo: ${escapeHtml(attr.author)} (${escapeHtml(attr.license)}) — Wikimedia Commons</a>`
      : "";

    els.feedback.innerHTML = `
      <strong>${escapeHtml(species.common)}</strong>
      <span class="answer-detail">
        <em>${escapeHtml(species.scientific)}</em><br>
        Family: ${escapeHtml(species.family)} · Leaf: ${escapeHtml(species.leafType)}, ${escapeHtml(species.arrangement)}
      </span>
      ${creditHtml}
    `;

    els.nextBtn.classList.remove("hidden");
    els.nextBtn.focus();
  }

  function showFeedback(isCorrect, species) {
    els.feedback.classList.remove("hidden", "correct", "incorrect");
    els.feedback.classList.add(isCorrect ? "correct" : "incorrect");

    const attr = (attributions[species.id] || {}).leaf;
    const creditHtml = attr
      ? `<a class="credit-link" href="${attr.sourcePage}" target="_blank" rel="noopener">Leaf photo: ${escapeHtml(attr.author)} (${escapeHtml(attr.license)}) — Wikimedia Commons</a>`
      : "";

    els.feedback.innerHTML = `
      <strong>${isCorrect ? "Correct!" : "Not quite."}</strong>
      <span class="answer-detail">
        ${escapeHtml(species.common)} — <em>${escapeHtml(species.scientific)}</em><br>
        Family: ${escapeHtml(species.family)} · Leaf: ${escapeHtml(species.leafType)}, ${escapeHtml(species.arrangement)}
      </span>
      ${creditHtml}
    `;

    els.scoreText.textContent = `Score: ${score} / ${answered}`;
    els.nextBtn.classList.remove("hidden");
    els.nextBtn.focus();
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function showHint() {
    const species = deck[currentIndex];
    if (!species) return;
    els.hintBox.textContent =
      `Family: ${species.family} · Leaf type: ${species.leafType} · Arrangement: ${species.arrangement}`;
    els.hintBox.classList.remove("hidden");
  }

  function nextCard() {
    currentIndex++;
    if (currentIndex >= deck.length) {
      showSummary();
    } else {
      renderCard();
    }
  }

  function showSummary() {
    els.quizCard.classList.add("hidden");
    els.summary.classList.remove("hidden");
    els.progressBarFill.style.width = "100%";
    els.progressText.textContent = `Card ${deck.length} / ${deck.length}`;

    const isFlashcard = els.modeSelect.value === "flashcard";
    els.summaryScore.textContent = isFlashcard
      ? `You reviewed ${answered} card${answered === 1 ? "" : "s"}.`
      : `You scored ${score} out of ${answered} (${deck.length ? Math.round((score / Math.max(answered,1)) * 100) : 0}%).`;

    els.missedList.innerHTML = "";
    if (isFlashcard) {
      els.retryMissedBtn.classList.add("hidden");
    } else if (missed.length === 0) {
      els.retryMissedBtn.classList.add("hidden");
      const p = document.createElement("p");
      p.textContent = "Perfect run — no missed species!";
      els.missedList.appendChild(p);
    } else {
      els.retryMissedBtn.classList.remove("hidden");
      const uniqueMissed = Array.from(new Map(missed.map(s => [s.id, s])).values());
      uniqueMissed.forEach(species => {
        const div = document.createElement("div");
        div.className = "missed-item";
        div.innerHTML = `
          <img src="images/${species.id}/leaf.jpg" alt="${escapeHtml(species.common)}">
          <div class="missed-name">${escapeHtml(species.common)}</div>
          <div class="missed-sci">${escapeHtml(species.scientific)}</div>
        `;
        els.missedList.appendChild(div);
      });
    }
  }

  function retryMissed() {
    const uniqueMissed = Array.from(new Map(missed.map(s => [s.id, s])).values());
    if (uniqueMissed.length === 0) return;
    buildDeck(uniqueMissed);
  }

  function renderCredits() {
    els.creditsList.innerHTML = "";
    allSpecies.forEach(species => {
      const attrs = attributions[species.id];
      if (!attrs) return;
      CATEGORY_ORDER.filter(cat => attrs[cat]).forEach(cat => {
        const attr = attrs[cat];
        const row = document.createElement("div");
        row.className = "credit-row";
        row.innerHTML = `
          <span>${escapeHtml(species.common)} — ${CATEGORY_LABELS[cat]}</span>
          <a href="${attr.sourcePage}" target="_blank" rel="noopener">${escapeHtml(attr.author)} — ${escapeHtml(attr.license)}</a>
        `;
        els.creditsList.appendChild(row);
      });
    });
  }

  function attachEvents() {
    els.restartBtn.addEventListener("click", () => { saveSettings(); buildDeck(allSpecies); });
    els.regionSelect.addEventListener("change", () => { saveSettings(); buildDeck(allSpecies); });
    els.modeSelect.addEventListener("change", () => { saveSettings(); buildDeck(allSpecies); });
    els.nameSelect.addEventListener("change", () => { saveSettings(); buildDeck(allSpecies); });
    els.groupSelect.addEventListener("change", () => { saveSettings(); buildDeck(allSpecies); });

    els.hintBtn.addEventListener("click", showHint);
    els.galleryPrev.addEventListener("click", () => galleryStep(-1));
    els.galleryNext.addEventListener("click", () => galleryStep(1));
    els.fillForm.addEventListener("submit", handleFillSubmit);
    els.revealBtn.addEventListener("click", revealAnswer);
    els.nextBtn.addEventListener("click", nextCard);
    els.retryMissedBtn.addEventListener("click", retryMissed);
    els.restartAllBtn.addEventListener("click", () => buildDeck(allSpecies));

    els.creditsLink.addEventListener("click", () => {
      renderCredits();
      els.creditsModal.classList.remove("hidden");
    });
    els.creditsClose.addEventListener("click", () => els.creditsModal.classList.add("hidden"));
    els.creditsModal.addEventListener("click", (e) => {
      if (e.target === els.creditsModal) els.creditsModal.classList.add("hidden");
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !els.nextBtn.classList.contains("hidden") && document.activeElement !== els.fillInput) {
        nextCard();
        return;
      }
      if ((e.key === "Enter" || e.key === " ") && els.modeSelect.value === "flashcard" && !currentAnswered && document.activeElement !== els.fillInput) {
        e.preventDefault();
        revealAnswer();
        return;
      }
      if (!currentAnswered && els.modeSelect.value === "multiple" && /^[1-4]$/.test(e.key)) {
        const idx = parseInt(e.key, 10) - 1;
        const btn = els.mcOptions.children[idx];
        if (btn) btn.click();
      }
      if (document.activeElement !== els.fillInput) {
        if (e.key === "ArrowLeft") galleryStep(-1);
        if (e.key === "ArrowRight") galleryStep(1);
      }
    });
  }

  async function init() {
    loadSettings();
    attachEvents();

    const [speciesRes, attrRes] = await Promise.all([
      fetch("data/species.json"),
      fetch("data/attributions.json"),
    ]);
    allSpecies = await speciesRes.json();
    attributions = await attrRes.json();

    buildDeck(allSpecies);
  }

  init();
})();
