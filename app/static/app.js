const apiStatus = document.querySelector("#api-status");
const providerNote = document.querySelector("#provider-note");
const todayLabel = document.querySelector("#today-label");
const watchlistForm = document.querySelector("#watchlist-form");
const watchlistRows = document.querySelector("#watchlist-rows");
const watchlistMessage = document.querySelector("#watchlist-message");
const newsFeedList = document.querySelector("#news-feed-list");
const newsFeedMessage = document.querySelector("#news-feed-message");
const refreshNewsButton = document.querySelector("#refresh-news-button");
const newsDetailDialog = document.querySelector("#news-detail-dialog");
const newsDetailContent = document.querySelector("#news-detail-content");
const closeNewsDetailButton = document.querySelector("#close-news-detail");
let latestNewsItems = [];

const escapeHtml = (value) => {
  const element = document.createElement("div");
  element.textContent = String(value ?? "");
  return element.innerHTML;
};

const formatPercent = (value) => {
  if (value === null || value === undefined) return "—";
  const number = Number(value);
  const sign = number > 0 ? "+" : number < 0 ? "−" : "";
  return `${sign}${Math.abs(number).toFixed(2)}%`;
};

const directionClass = (value) => {
  if (value === null || value === undefined) return "neutral";
  return Number(value) >= 0 ? "positive" : "negative";
};

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

const importanceLabel = { high: "중요", medium: "보통", low: "낮음" };

const renderDashboard = (data) => {
  document.querySelector("#market-summary").textContent = data.summary;

  document.querySelector("#market-sessions").innerHTML = data.market_sessions
    .map(
      (session) => `
        <span class="market-badge ${session.market === "KR" ? "korea" : ""}">
          <span></span>${escapeHtml(session.label)} ${escapeHtml(session.status)}
        </span>
      `,
    )
    .join("");

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

  const holdingRow = (holding) => `
        <div class="holding-row">
          <span class="ticker ${escapeHtml(holding.color)}">
            ${escapeHtml(holding.market_group === "KR" ? holding.name.slice(0, 1) : holding.symbol.slice(0, 2))}
          </span>
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
      `;

  const portfolioGroups = [
    { key: "KR", label: "국장 포트폴리오", market: "KOSPI · KOSDAQ" },
    { key: "US", label: "미장 포트폴리오", market: "NASDAQ · NYSE" },
  ];
  document.querySelector("#holding-groups").innerHTML = portfolioGroups
    .map((group) => {
      const holdings = data.holdings.filter((holding) => holding.market_group === group.key);
      return `
        <section class="holding-group">
          <div class="holding-group-title">
            <strong>${group.label}</strong><span>${group.market}</span>
          </div>
          <div class="holding-list">${holdings.map(holdingRow).join("")}</div>
        </section>
      `;
    })
    .join("");

  document.querySelector("#focus-list").innerHTML = data.focus_items
    .map(
      (item, index) => `
        <li>
          <span>${index + 1}</span>
          <div class="focus-content">
            <strong>${escapeHtml(item.title)}</strong>
            <p>${escapeHtml(item.description)}</p>
            <details class="focus-detail">
              <summary>상세 보기</summary>
              <div class="focus-detail-body">
                <p>${escapeHtml(item.detail_summary)}</p>
                <strong>종합 근거</strong>
                ${formatList(item.evidence)}
                <div class="symbol-list">
                  ${item.related_symbols.map((symbol) => `<span>${escapeHtml(symbol)}</span>`).join("")}
                </div>
              </div>
            </details>
          </div>
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

const formatPublishedAt = (value) =>
  new Intl.DateTimeFormat("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));

const sentimentClass = (value) => {
  const label = String(value ?? "").toLowerCase();
  if (label.includes("bullish")) return "positive";
  if (label.includes("bearish")) return "negative";
  return "neutral";
};

const renderNewsFeed = (items) => {
  latestNewsItems = items;
  if (!items.length) {
    newsFeedList.innerHTML = `
      <div class="empty-news-feed">
        <strong>아직 수집된 뉴스가 없습니다.</strong>
        <p>뉴스 수집 버튼을 눌러 관심 종목의 최신 이슈를 불러오세요.</p>
      </div>
    `;
    return;
  }

  const renderNewsCard = (item) => `
        <article class="news-card ${item.provider === "mock" ? "sample" : "actual"}">
          <div class="news-card-meta">
            <span>${escapeHtml(item.source)} · ${item.provider === "mock" ? "샘플" : "실제 뉴스"}</span>
            <time datetime="${escapeHtml(item.published_at)}">${formatPublishedAt(item.published_at)}</time>
          </div>
          <button class="news-card-title" type="button" data-news-id="${item.id}">
            ${escapeHtml(item.title)}
          </button>
          <p>${escapeHtml(item.korean_summary ?? item.summary)}</p>
          <div class="news-card-footer">
            <div class="symbol-list">
              ${item.symbols.map((symbol) => `<span>${escapeHtml(symbol)}</span>`).join("")}
            </div>
            <span class="sentiment ${sentimentClass(item.sentiment)}">
              ${escapeHtml(item.sentiment ?? "분석 전")}
            </span>
          </div>
        </article>
      `;
  const categories = [...new Set(items.map((item) => item.category || "기타"))];
  newsFeedList.innerHTML = categories
    .map(
      (category) => `
        <section class="news-category-group">
          <div class="news-category-title">
            <h3>${escapeHtml(category)}</h3>
            <span>${items.filter((item) => item.category === category).length}건</span>
          </div>
          <div class="news-category-grid">
            ${items.filter((item) => item.category === category).map(renderNewsCard).join("")}
          </div>
        </section>
      `,
    )
    .join("");
};

const openNewsDetail = (item) => {
  newsDetailContent.innerHTML = `
    <div class="news-detail-meta">
      <span>${escapeHtml(item.source)}</span>
      <time datetime="${escapeHtml(item.published_at)}">${formatPublishedAt(item.published_at)}</time>
    </div>
    <h3>${escapeHtml(item.title)}</h3>
    <p class="news-detail-summary">${escapeHtml(item.korean_summary ?? item.summary)}</p>
    <div class="news-detail-section">
      <strong>관련 종목</strong>
      <div class="symbol-list">
        ${item.symbols.length ? item.symbols.map((symbol) => `<span>${escapeHtml(symbol)}</span>`).join("") : "<span>관련 종목 없음</span>"}
      </div>
    </div>
    <div class="news-detail-section">
      <strong>제공 데이터</strong>
      <p>${escapeHtml(item.category)} · ${escapeHtml(item.sentiment ?? "감성 정보 없음")} · ${escapeHtml(item.provider)}</p>
    </div>
    <a class="news-source-link" href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener noreferrer">
      원문 기사 보기
    </a>
  `;
  newsDetailDialog.showModal();
};

const loadNewsFeed = async () => {
  try {
    renderNewsFeed(await fetchJson("/api/v1/news/latest?limit=20"));
  } catch (error) {
    newsFeedMessage.textContent = error.message;
    newsFeedMessage.classList.add("error");
  }
};

const checkApi = async () => {
  try {
    const health = await fetchJson("/api/v1/health");
    apiStatus.textContent = `${health.ai_provider.toUpperCase()} · 연결됨`;
    providerNote.textContent = `${health.ai_provider.toUpperCase()} AI 활성화`;
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

refreshNewsButton.addEventListener("click", async () => {
  refreshNewsButton.disabled = true;
  refreshNewsButton.textContent = "수집 중…";
  newsFeedMessage.textContent = "";
  newsFeedMessage.classList.remove("error");

  try {
    const result = await fetchJson("/api/v1/news/refresh", { method: "POST" });
    if (result.stored_count) {
      newsFeedMessage.textContent =
        `${result.provider} 실제 뉴스 ${result.collected_count}건 중 ` +
        `${result.stored_count}건을 저장하고 ${result.summarized_count}건을 한국어로 요약했습니다.`;
    } else if (result.collected_count) {
      newsFeedMessage.textContent =
        `실제 뉴스 ${result.collected_count}건은 모두 저장되어 있으며 ` +
        `${result.summarized_count}건을 추가로 한국어 요약했습니다.`;
    } else {
      newsFeedMessage.textContent =
        "Alpha Vantage가 현재 관심 종목의 실제 뉴스를 반환하지 않았습니다.";
      newsFeedMessage.classList.add("error");
    }
    await loadNewsFeed();
  } catch (error) {
    newsFeedMessage.textContent = error.message;
    newsFeedMessage.classList.add("error");
  } finally {
    refreshNewsButton.disabled = false;
    refreshNewsButton.textContent = "뉴스 수집";
  }
});

newsFeedList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-news-id]");
  if (!button) return;
  const item = latestNewsItems.find((news) => news.id === Number(button.dataset.newsId));
  if (item) openNewsDetail(item);
});

closeNewsDetailButton.addEventListener("click", () => newsDetailDialog.close());

newsDetailDialog.addEventListener("click", (event) => {
  if (event.target === newsDetailDialog) newsDetailDialog.close();
});

todayLabel.textContent = new Intl.DateTimeFormat("ko-KR", {
  year: "numeric",
  month: "long",
  day: "numeric",
  weekday: "long",
}).format(new Date());

Promise.all([checkApi(), loadDashboard(), loadWatchlist(), loadNewsFeed()]);
