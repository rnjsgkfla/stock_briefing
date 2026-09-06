const analysisForm = document.querySelector("#analysis-form");
const resultPanel = document.querySelector("#analysis-result");
const analyzeButton = document.querySelector("#analyze-button");
const apiStatus = document.querySelector("#api-status");
const todayLabel = document.querySelector("#today-label");
const watchlistForm = document.querySelector("#watchlist-form");
const watchlistRows = document.querySelector("#watchlist-rows");
const watchlistMessage = document.querySelector("#watchlist-message");

const escapeHtml = (value) => {
  const element = document.createElement("div");
  element.textContent = String(value ?? "");
  return element.innerHTML;
};

const formatPercent = (value) => {
  const number = Number(value);
  const sign = number > 0 ? "+" : number < 0 ? "−" : "";
  return `${sign}${Math.abs(number).toFixed(2)}%`;
};

const directionClass = (value) => (Number(value) >= 0 ? "positive" : "negative");

const fetchJson = async (url, options) => {
  const response = await fetch(url, options);
  if (response.status === 204) return null;

  const data = await response.json();
  if (!response.ok) throw new Error(data.detail ?? "요청을 처리하지 못했습니다.");
  return data;
};

const formatList = (items) => {
  if (!items?.length) return "<p>확인된 내용이 없습니다.</p>";
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
};

const directionLabel = {
  positive: "긍정 가능성",
  neutral: "중립",
  negative: "부정 가능성",
  mixed: "혼재",
};

const importanceLabel = { high: "중요", medium: "보통", low: "낮음" };

const renderResult = (data) => {
  const symbols = data.related_symbols.length
    ? data.related_symbols.map((symbol) => escapeHtml(symbol)).join(" · ")
    : "관련 종목 없음";

  resultPanel.innerHTML = `
    <div class="result-header">
      <h3>분석 완료</h3>
      <span class="provider-badge">${escapeHtml(data.provider)} provider</span>
    </div>
    <p class="result-summary">${escapeHtml(data.summary)}</p>
    <div class="result-meta">
      <span>${symbols}</span>
      <span>${escapeHtml(directionLabel[data.impact_direction] ?? data.impact_direction)}</span>
      <span>${escapeHtml(importanceLabel[data.importance] ?? data.importance)}</span>
    </div>
    <div class="result-block"><strong>확인된 사실</strong>${formatList(data.facts)}</div>
    <div class="result-block"><strong>해석</strong><p>${escapeHtml(data.interpretation)}</p></div>
    <div class="result-block"><strong>불확실성</strong>${formatList(data.uncertainties)}</div>
  `;
};

const renderDashboard = (data) => {
  document.querySelector("#market-summary").textContent = data.summary;

  data.markets.forEach((market) => {
    const card = document.querySelector(`[data-market-symbol="${market.symbol}"]`);
    if (!card) return;
    card.querySelector('[data-role="name"]').textContent = market.name;
    card.querySelector('[data-role="value"]').textContent = market.display_value;
    const change = card.querySelector('[data-role="change"]');
    change.textContent = formatPercent(market.change_percent);
    change.classList.toggle("positive", market.change_percent >= 0);
    change.classList.toggle("negative", market.change_percent < 0);
  });

  const portfolioImpact = document.querySelector("#portfolio-impact");
  portfolioImpact.textContent = formatPercent(data.expected_portfolio_impact_percent);
  portfolioImpact.className = directionClass(data.expected_portfolio_impact_percent);

  document.querySelector("#holding-list").innerHTML = data.holdings
    .map(
      (holding) => `
        <div class="holding-row">
          <span class="ticker ${escapeHtml(holding.color)}">${escapeHtml(holding.symbol.slice(0, 2))}</span>
          <div class="holding-name">
            <strong>${escapeHtml(holding.name)}</strong>
            <span>${escapeHtml(holding.symbol)} · 비중 ${holding.weight_percent}%</span>
          </div>
          <span class="impact-pill ${escapeHtml(holding.importance)}">
            ${escapeHtml(importanceLabel[holding.importance] ?? holding.importance)}
          </span>
          <strong class="${directionClass(holding.change_percent)}">
            ${formatPercent(holding.change_percent)}
          </strong>
        </div>
      `,
    )
    .join("");

  document.querySelector("#focus-list").innerHTML = data.focus_items
    .map(
      (item, index) => `
        <li>
          <span>${index + 1}</span>
          <div><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.description)}</p></div>
        </li>
      `,
    )
    .join("");
};

const loadDashboard = async () => {
  try {
    renderDashboard(await fetchJson("/api/v1/dashboard"));
  } catch (error) {
    document.querySelector("#market-summary").textContent = `브리핑을 불러오지 못했습니다. ${error.message}`;
  }
};

const renderWatchlist = (items) => {
  if (!items.length) {
    watchlistRows.innerHTML = '<p class="empty-watchlist">관심 종목을 추가해보세요.</p>';
    return;
  }

  watchlistRows.innerHTML = items
    .map(
      (item) => `
        <div class="table-row" role="row">
          <span><b>${escapeHtml(item.symbol)}</b><small>${escapeHtml(item.name)}</small></span>
          <span>${escapeHtml(item.display_price)}</span>
          <span class="${directionClass(item.change_percent)}">${formatPercent(item.change_percent)}</span>
          <span class="watchlist-actions">
            <small>새 소식 ${item.news_count}</small>
            <button type="button" data-remove-symbol="${escapeHtml(item.symbol)}" aria-label="${escapeHtml(item.symbol)} 삭제">삭제</button>
          </span>
        </div>
      `,
    )
    .join("");
};

const loadWatchlist = async () => {
  try {
    renderWatchlist(await fetchJson("/api/v1/watchlist"));
  } catch (error) {
    watchlistMessage.textContent = error.message;
    watchlistMessage.classList.add("error");
  }
};

const checkApi = async () => {
  try {
    const health = await fetchJson("/api/v1/health");
    apiStatus.textContent = `${health.ai_provider.toUpperCase()} · 연결됨`;
    apiStatus.classList.add("connected");
  } catch {
    apiStatus.textContent = "API 연결 실패";
    apiStatus.classList.remove("connected");
  }
};

watchlistForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.querySelector("#watchlist-symbol");
  const button = watchlistForm.querySelector("button");
  button.disabled = true;
  watchlistMessage.textContent = "";
  watchlistMessage.classList.remove("error");

  try {
    const item = await fetchJson("/api/v1/watchlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: input.value }),
    });
    input.value = "";
    watchlistMessage.textContent = `${item.symbol} 종목을 추가했습니다.`;
    await loadWatchlist();
  } catch (error) {
    watchlistMessage.textContent = error.message;
    watchlistMessage.classList.add("error");
  } finally {
    button.disabled = false;
  }
});

watchlistRows.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-remove-symbol]");
  if (!button) return;
  button.disabled = true;
  const symbol = button.dataset.removeSymbol;

  try {
    await fetchJson(`/api/v1/watchlist/${encodeURIComponent(symbol)}`, { method: "DELETE" });
    watchlistMessage.textContent = `${symbol} 종목을 삭제했습니다.`;
    watchlistMessage.classList.remove("error");
    await loadWatchlist();
  } catch (error) {
    watchlistMessage.textContent = error.message;
    watchlistMessage.classList.add("error");
    button.disabled = false;
  }
});

analysisForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  analyzeButton.disabled = true;
  analyzeButton.querySelector("span").textContent = "분석 중…";

  const symbols = document
    .querySelector("#news-symbols")
    .value.split(",")
    .map((symbol) => symbol.trim())
    .filter(Boolean);

  try {
    const data = await fetchJson("/api/v1/news/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: document.querySelector("#news-title").value,
        content: document.querySelector("#news-content").value,
        candidate_symbols: symbols,
      }),
    });
    renderResult(data);
  } catch (error) {
    resultPanel.innerHTML = `
      <div class="error-message">
        <div><strong>분석하지 못했습니다.</strong><br />${escapeHtml(error.message)}</div>
      </div>
    `;
  } finally {
    analyzeButton.disabled = false;
    analyzeButton.querySelector("span").textContent = "AI 분석 실행";
  }
});

todayLabel.textContent = new Intl.DateTimeFormat("ko-KR", {
  year: "numeric",
  month: "long",
  day: "numeric",
  weekday: "long",
}).format(new Date());

Promise.all([checkApi(), loadDashboard(), loadWatchlist()]);
