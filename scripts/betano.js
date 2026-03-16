#!/usr/bin/env node
/**
 * BETANO SCRAPER
 *  node scripts/betano.js         → defaultně fotbal pre-match
 *  node scripts/betano.js --json  → uloží betano_odds.json
 */
const { chromium } = require("playwright");
const fs = require("fs");

const CFG = {
  baseUrl: "https://www.betano.cz",
  sportFilter: "FOOT",
  outputFile: "betano_odds.json",
  urls: [
    "https://www.betano.cz/sport/fotbal/",
  ],
};

const C = {
  reset: "\x1b[0m", bright: "\x1b[1m", dim: "\x1b[2m",
  red: "\x1b[31m", green: "\x1b[32m", yellow: "\x1b[33m", cyan: "\x1b[36m",
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const fmtTime = (ms) => {
  if (!ms) return "?";
  try {
    return new Date(ms).toLocaleString("cs-CZ", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  } catch {
    return "?";
  }
};

function parseOverview(body, sportFilter) {
  const events = body.events || {};
  const markets = body.markets || {};
  const selections = body.selections || {};
  const leagues = body.leagues || {};
  const zones = body.zones || {};
  const matches = [];

  for (const ev of Object.values(events)) {
    if (sportFilter && ev.sportId !== sportFilter) continue;

    const home = (ev.participants || []).find((p) => p.isHome)?.name || "?";
    const away = (ev.participants || []).find((p) => !p.isHome)?.name || "?";
    const league = leagues[String(ev.leagueId || "")]?.name || "?";
    const zone = zones[String(ev.zoneId || "")]?.name || "";
    const leagueFull = zone && !league.includes(zone) ? `${zone} - ${league}` : league;

    const odds = {};
    const allOdds = {};

    for (const mid of (ev.marketIdList || [])) {
      const mk = markets[String(mid)] || markets[mid];
      if (!mk) continue;

      const mktName = mk.name || mk.type || "?";
      const mOdds = {};

      for (const sid of (mk.selectionIdList || [])) {
        const sel = selections[String(sid)] || selections[sid];
        if (!sel) continue;
        const price = parseFloat(sel.price || 0);
        if (price <= 1) continue;
        mOdds[sel.name] = price;
      }

      if (!Object.keys(mOdds).length) continue;
      allOdds[mktName] = mOdds;

      if (mk.type === "MRES") {
        let mapped = false;
        for (const sid of (mk.selectionIdList || [])) {
          const sel = selections[String(sid)] || selections[sid];
          if (!sel) continue;
          const price = parseFloat(sel.price || 0);
          if (price <= 1) continue;
          if (sel.name === "1") {
            odds["1"] = price;
            mapped = true;
          } else if (sel.name === "0") {
            odds["X"] = price;
            mapped = true;
          } else if (sel.name === "2") {
            odds["2"] = price;
            mapped = true;
          }
        }

        if (!mapped) {
          const keys = Object.keys(mOdds);
          if (keys.length === 3) {
            odds["1"] = mOdds[keys[0]];
            odds["X"] = mOdds[keys[1]];
            odds["2"] = mOdds[keys[2]];
          } else if (keys.length === 2) {
            odds["1"] = mOdds[keys[0]];
            odds["2"] = mOdds[keys[1]];
          }
        }
      }
    }

    matches.push({
      id: ev.id,
      sport: ev.sportId,
      home,
      away,
      league: leagueFull,
      startTime: ev.startTime,
      isLive: !!ev.isLive,
      url: ev.url ? `${CFG.baseUrl}${ev.url}` : null,
      odds,
      allOdds,
    });
  }

  matches.sort((a, b) => (a.startTime || 0) - (b.startTime || 0));
  return matches;
}

function parseMatchPage(body) {
  const ev = body?.data?.event;
  if (!ev) return null;

  const home = ev.participants?.[0]?.name || "?";
  const away = ev.participants?.[1]?.name || "?";
  const odds = {};
  const allOdds = {};

  for (const mk of (ev.markets || [])) {
    const mktName = mk.name || mk.type || "?";
    const mOdds = {};
    for (const sel of (mk.selections || [])) {
      const price = parseFloat(sel.price || 0);
      if (price <= 1) continue;
      mOdds[sel.fullName || sel.name] = price;
    }
    if (!Object.keys(mOdds).length) continue;
    allOdds[mktName] = mOdds;

    if (mk.type === "MRES") {
      for (const sel of (mk.selections || [])) {
        const price = parseFloat(sel.price || 0);
        if (price <= 1) continue;
        if (sel.name === "1") odds["1"] = price;
        else if (sel.name === "0") odds["X"] = price;
        else if (sel.name === "2") odds["2"] = price;
      }
    }
  }

  return {
    id: ev.id,
    sport: "FOOT",
    home,
    away,
    league: ev.leagueName || ev.leagueDescription || "?",
    startTime: ev.startTime,
    isLive: false,
    url: ev.url ? `${CFG.baseUrl}${ev.url}` : null,
    odds,
    allOdds,
  };
}

function printMatches(matches) {
  if (!matches.length) {
    console.log(`\n  ${C.yellow}Žádné zápasy.${C.reset}\n`);
    return;
  }

  const byLeague = {};
  matches.forEach((m) => {
    (byLeague[m.league] = byLeague[m.league] || []).push(m);
  });

  for (const [league, lm] of Object.entries(byLeague)) {
    console.log(`\n  ${C.cyan}${C.bright}▶ ${league}${C.reset}  ${C.dim}(${lm.length})${C.reset}`);
    console.log(`  ${C.dim}${"─".repeat(72)}${C.reset}`);
    console.log(`  ${C.dim}${"ZÁPAS".padEnd(44)} ${"1".padStart(6)} ${"X".padStart(6)} ${"2".padStart(6)}${C.reset}`);
    for (const m of lm) {
      const live = m.isLive ? `${C.red}●${C.reset} ` : "  ";
      const nm = `${m.home} - ${m.away}`.substring(0, 40).padEnd(40);
      const o1 = m.odds["1"] ? m.odds["1"].toFixed(2) : "   —";
      const oX = m.odds["X"] ? m.odds["X"].toFixed(2) : "   —";
      const o2 = m.odds["2"] ? m.odds["2"].toFixed(2) : "   —";
      console.log(`  ${live}${C.bright}${nm}${C.reset} ${C.dim}[${fmtTime(m.startTime)}]${C.reset}  ${C.green}${o1.padStart(6)}${C.reset}  ${C.yellow}${oX.padStart(6)}${C.reset}  ${C.red}${o2.padStart(6)}${C.reset}`);
    }
  }
}

async function run() {
  const args = process.argv.slice(2);
  if (args.includes("--all")) CFG.sportFilter = null;
  if (args.includes("--esports")) {
    CFG.sportFilter = null;
    CFG.urls = ["https://www.betano.cz/sport/esports/"];
  }

  console.clear();
  console.log(`${C.bright}${C.cyan}\n  ╔══════════════════════════════════════════════╗\n  ║   BETANO SCRAPER  ·  Playwright              ║\n  ║   ${new Date().toLocaleTimeString("cs-CZ").padEnd(42)}║\n  ╚══════════════════════════════════════════════╝${C.reset}\n`);

  const browser = await chromium.launch({
    headless: false,
    args: ["--no-sandbox", "--disable-blink-features=AutomationControlled"],
  });
  const context = await browser.newContext({
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    viewport: { width: 1280, height: 800 },
    locale: "cs-CZ",
    extraHTTPHeaders: { "accept-language": "cs-CZ,cs;q=0.9" },
  });
  await context.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => false });
    window.chrome = { runtime: {} };
  });

  const page = await context.newPage();
  const overviewData = [];
  const matchPageData = [];

  page.on("response", async (resp) => {
    try {
      const url = resp.url();
      if (resp.status() !== 200) return;
      if (url.includes("/danae-webapi/api/live/overview/")) {
        const body = await resp.json();
        if (body?.events && Object.keys(body.events).length > 0) overviewData.push(body);
      } else if (url.includes("/api/zapas-sance/") || (url.includes("/api/") && url.includes("/81"))) {
        const body = await resp.json();
        if (body?.data?.event) matchPageData.push(body);
      }
    } catch {
      // noop
    }
  });

  for (let i = 0; i < CFG.urls.length; i++) {
    const url = CFG.urls[i];
    const prevTotal = overviewData.length + matchPageData.length;
    process.stdout.write(`  ${C.dim}[${i + 1}/${CFG.urls.length}] Načítám...${C.reset}\r`);

    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {});

    if (i === 0) {
      try {
        const btn = page.locator('button:has-text("Přijmout vše"), button:has-text("Accept all")').first();
        if (await btn.isVisible({ timeout: 5000 })) {
          await btn.click();
          process.stdout.write(`  ${C.green}✓ Cookie potvrzen${C.reset}\n`);
        }
      } catch {
        // noop
      }
    }

    const deadline = Date.now() + 12000;
    while (overviewData.length + matchPageData.length === prevTotal && Date.now() < deadline) await sleep(300);

    if (overviewData.length + matchPageData.length === prevTotal) {
      await page.reload({ waitUntil: "domcontentloaded", timeout: 10000 }).catch(() => {});
      const d2 = Date.now() + 8000;
      while (overviewData.length + matchPageData.length === prevTotal && Date.now() < d2) await sleep(300);
    }

    const newCount = overviewData.length + matchPageData.length - prevTotal;
    process.stdout.write(`  ${C.green}✓ [${i + 1}/${CFG.urls.length}] +${newCount} responses${C.reset}\n`);
    if (i < CFG.urls.length - 1) await sleep(1000);
  }

  await browser.close();

  const merged = { events: {}, markets: {}, selections: {}, leagues: {}, zones: {} };
  for (const body of overviewData) {
    Object.assign(merged.events, body.events || {});
    Object.assign(merged.markets, body.markets || {});
    Object.assign(merged.selections, body.selections || {});
    Object.assign(merged.leagues, body.leagues || {});
    Object.assign(merged.zones, body.zones || {});
  }

  const matches = parseOverview(merged, CFG.sportFilter);

  for (const body of matchPageData) {
    const m = parseMatchPage(body);
    if (!m || !m.odds["1"]) continue;
    const norm = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, "");
    const exists = matches.some((x) => norm(x.home).includes(norm(m.home).substring(0, 5)) || norm(m.home).includes(norm(x.home).substring(0, 5)));
    if (!exists) {
      matches.push(m);
      console.log(`  ${C.dim}+ přidán z match-page: ${m.home} - ${m.away}${C.reset}`);
    }
  }

  if (!matches.length) {
    console.log(`  ${C.red}✗ Žádná data${C.reset}\n`);
    return;
  }

  console.log(`  ${C.green}✓ Betano: ${matches.length} zápasů (${matches.filter((m) => m.odds["1"]).length} s kurzy 1X2)${C.reset}`);
  printMatches(matches);

  if (args.includes("--json")) {
    fs.writeFileSync(CFG.outputFile, JSON.stringify({
      timestamp: new Date().toISOString(),
      count: matches.length,
      matches,
    }, null, 2));
    console.log(`\n  ${C.green}✓ Uloženo: ${CFG.outputFile}${C.reset}`);
  }

  console.log(`\n  ${C.dim}${new Date().toLocaleString("cs-CZ")}${C.reset}\n`);
}

run().catch((e) => {
  console.error(`\n${C.red}Chyba: ${e.message}${C.reset}`);
  process.exit(1);
});
