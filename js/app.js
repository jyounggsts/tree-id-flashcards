(() => {
  "use strict";

  const els = {
    modeSelect: document.getElementById("mode-select"),
    nameSelect: document.getElementById("name-select"),
    groupSelect: document.getElementById("group-select"),
    restartBtn: document.getElementById("restart-btn"),
    progressText: document.getElementById("progress-text"),
    scoreText: document.getElementById("score-text"),
    progressBarFill: document.getElementById("progress-bar-fill"),
    quizCard: document.getElementById("quiz-card"),
    speciesImage: document.getElementById("species-image"),
    hintBtn: document.getElementById("hint-btn"),
    hintBox: document.getElementById("hint-box"),
    promptText: document.getElementById("prompt-text"),
    mcOptions: document.getElementById("mc-options"),
    fillForm: document.getElementById("fill-form"),
    fillInput: document.getElementById("fill-input"),
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

  function loadSettings() {
    try {
      const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}");
      if (saved.mode) els.modeSelect.value = saved.mode;
      if (saved.name) els.nameSelect.value = saved.name;
      if (saved.group) els.groupSelect.value = saved.group;
    } catch (e) { /* ignore corrupt settings */ }
  }

  function saveSettings() {
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify({
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

  function buildDeck(sourceList) {
    const group = els.groupSelect.value;
    const filtered = group === "all" ? sourceList : sourceList.filter(s => s.group === group);
    deck = shuffle(filtered);
    currentIndex = 0;
    score = 0;
    answered = 0;
    missed = [];
    updateGroupLabel();
    els.summary.classList.add("hidden");
    els.quizCard.classList.remove("hidden");
    renderCard();
  }

  function updateGroupLabel() {
    const opt = els.groupSelect.selectedOptions[0];
    const totalForGroup = els.groupSelect.value === "all"
      ? allSpecies.length
      : allSpecies.filter(s => s.group === els.groupSelect.value).length;
    opt.textContent = opt.textContent.replace(/\(\d+\)/, `(${totalForGroup})`);
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
    els.scoreText.textContent = `Score: ${score} / ${answered}`;
    els.progressBarFill.style.width = `${(currentIndex / deck.length) * 100}%`;

    els.speciesImage.src = `images/${species.id}.jpg`;
    els.speciesImage.alt = `Photo to identify (species ${currentIndex + 1})`;

    els.hintBox.classList.add("hidden");
    els.hintBox.textContent = "";

    const nameLabel = currentNameField() === "scientific" ? "scientific name" : "common name";
    els.promptText.textContent = `What is the ${nameLabel} of this tree/leaf?`;

    els.feedback.classList.add("hidden");
    els.feedback.textContent = "";
    els.nextBtn.classList.add("hidden");

    const mode = els.modeSelect.value;
    if (mode === "multiple") {
      els.mcOptions.classList.remove("hidden");
      els.fillForm.classList.add("hidden");
      renderMultipleChoice(species);
    } else {
      els.mcOptions.classList.add("hidden");
      els.fillForm.classList.remove("hidden");
      els.fillInput.value = "";
      els.fillInput.disabled = false;
      els.fillInput.focus();
    }
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

  function showFeedback(isCorrect, species) {
    els.feedback.classList.remove("hidden", "correct", "incorrect");
    els.feedback.classList.add(isCorrect ? "correct" : "incorrect");

    const attr = attributions[species.id];
    const creditHtml = attr
      ? `<a class="credit-link" href="${attr.sourcePage}" target="_blank" rel="noopener">Photo: ${escapeHtml(attr.author)} (${escapeHtml(attr.license)}) — Wikimedia Commons</a>`
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
    els.summaryScore.textContent = `You scored ${score} out of ${answered} (${deck.length ? Math.round((score / Math.max(answered,1)) * 100) : 0}%).`;

    els.missedList.innerHTML = "";
    if (missed.length === 0) {
      const p = document.createElement("p");
      p.textContent = "Perfect run — no missed species!";
      els.missedList.appendChild(p);
    } else {
      const uniqueMissed = Array.from(new Map(missed.map(s => [s.id, s])).values());
      uniqueMissed.forEach(species => {
        const div = document.createElement("div");
        div.className = "missed-item";
        div.innerHTML = `
          <img src="images/${species.id}.jpg" alt="${escapeHtml(species.common)}">
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
      const attr = attributions[species.id];
      if (!attr) return;
      const row = document.createElement("div");
      row.className = "credit-row";
      row.innerHTML = `
        <span>${escapeHtml(species.common)}</span>
        <a href="${attr.sourcePage}" target="_blank" rel="noopener">${escapeHtml(attr.author)} — ${escapeHtml(attr.license)}</a>
      `;
      els.creditsList.appendChild(row);
    });
  }

  function attachEvents() {
    els.restartBtn.addEventListener("click", () => { saveSettings(); buildDeck(allSpecies); });
    els.modeSelect.addEventListener("change", () => { saveSettings(); buildDeck(allSpecies); });
    els.nameSelect.addEventListener("change", () => { saveSettings(); buildDeck(allSpecies); });
    els.groupSelect.addEventListener("change", () => { saveSettings(); buildDeck(allSpecies); });

    els.hintBtn.addEventListener("click", showHint);
    els.fillForm.addEventListener("submit", handleFillSubmit);
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
      }
      if (!currentAnswered && els.modeSelect.value === "multiple" && /^[1-4]$/.test(e.key)) {
        const idx = parseInt(e.key, 10) - 1;
        const btn = els.mcOptions.children[idx];
        if (btn) btn.click();
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
