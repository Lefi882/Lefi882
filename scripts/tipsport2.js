#!/usr/bin/env node
/**
 * TIPSPORT SCRAPER
 *  node scripts/tipsport2.js          → fotbal, kurzy do konzole
 *  node scripts/tipsport2.js --json   → uloží tipsport_odds.json
 *  node scripts/tipsport2.js --sport 188  → esporty
 *  node scripts/tipsport2.js --sport 188 --details → esporty + všechny trhy každého zápasu
 *  node scripts/tipsport2.js --sport 188 --details --limit 5 → jen prvních 5 zápasů
 */
const { chromium } = require("playwright");
const fs = require("fs");

const CFG = {
  baseUrl: "https://www.tipsport.cz",
  sports: {
    16: { name: "Fotbal", path: "fotbal-16" },
    188: { name: "Esporty", path: "esporty-188" },
  },
  outputFile: "tipsport_odds.json",
};

const C = {
  reset: "\x1b[0m", bright: "\x1b[1m", dim: "\x1b[2m",
  red: "\x1b[31m", green: "\x1b[32m", yellow: "\x1b[33m", cyan: "\x1b[36m",
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const fmtTime = (iso) => {
  if (!iso) return "?";
  try {
    return new Date(iso).toLocaleString("cs-CZ", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  } catch {
    return "?";
  }
};

function parseOffer(data, sportName) {
  const matches = [];
  for (const sport of (data.offerSuperSports || [])) {
    for (const tab of (sport.tabs || [])) {
      for (const comp of (tab.offerCompetitionAnnuals || [])) {
        const league = comp.name || sportName;
        for (const m of (comp.matches || [])) {
          if (!m) continue;
          const odds = {};
          for (const row of (m.oppRows || [])) {
            for (const opp of (row?.oppsTab || [])) {
              if (!opp?.bettingEnabled) continue;
              const o = parseFloat(opp.odd || 0);
              if (o <= 1) continue;
              const t = opp.type || "";
              if (t === "1") odds["1"] = o;
              else if (t === "x") odds["X"] = o;
              else if (t === "2") odds["2"] = o;
              else if (t === "1x") odds["1X"] = o;
              else if (t === "x2") odds["X2"] = o;
              else if (t === "12") odds["12"] = o;
              else odds[opp.label || t] = o;
            }
          }
          matches.push({
            id: m.id,
            sport: sportName,
            home: String(m.participantHome || "?").trim(),
            away: String(m.participantVisiting || "?").trim(),
            league,
            startTime: m.dateStartTv,
            isLive: !!(m.inLive),
            url: m.url ? `${CFG.baseUrl}${m.url}` : null,
            odds,
          });
        }
      }
    }
  }
  return matches;
}

async function scrapeSport(context, name, path, cookieClicked) {
  const page = await context.newPage();
  let offerData = null;
  const allResponses = [];

  page.on("response", async (resp) => {
    try {
      const url = resp.url();
      if (!url.includes("tipsport.cz/rest/")) return;
      if (resp.status() !== 200) return;
      const ct = resp.headers()["content-type"] || "";
      if (!ct.includes("json")) return;
      const body = await resp.json();
      const size = JSON.stringify(body).length;
      allResponses.push({ url: url.replace("https://www.tipsport.cz", ""), size, body });
      if (url.includes("/rest/offer/v2/offer") && body?.offerSuperSports) {
        offerData = body;
      }
    } catch {
      // noop
    }
  });

  await page.goto(`${CFG.baseUrl}/kurzy/${path}`, {
    waitUntil: "domcontentloaded", timeout: 20000,
  }).catch(() => {});

  if (!cookieClicked.done) {
    try {
      const btn = page.locator('button:has-text("Schválit vše")').first();
      await btn.waitFor({ state: "visible", timeout: 6000 });
      await btn.click();
      cookieClicked.done = true;
      process.stdout.write(`  ${C.green}✓ Cookie potvrzen${C.reset}\n`);
    } catch {
      cookieClicked.done = true;
    }
  }

  const deadline = Date.now() + 15000;
  while (!offerData && Date.now() < deadline) await sleep(200);

  if (!offerData) {
    await page.reload({ waitUntil: "domcontentloaded", timeout: 12000 }).catch(() => {});
    const d2 = Date.now() + 10000;
    while (!offerData && Date.now() < d2) await sleep(200);
  }

  if (!offerData && allResponses.length > 0) {
    process.stdout.write(`  ${C.yellow}⚠ ${name}: offer nezachycen, ale přišlo ${allResponses.length} responses:${C.reset}\n`);
    allResponses.sort((a, b) => b.size - a.size).slice(0, 5).forEach((r) =>
      process.stdout.write(`    ${C.dim}${r.size.toString().padStart(7)}B  ${r.url.substring(0, 70)}${C.reset}\n`),
    );
    const biggest = allResponses.find((r) => r.body?.offerSuperSports);
    if (biggest) offerData = biggest.body;
  }

  await page.close();

  if (!offerData) {
    process.stdout.write(`  ${C.red}✗ ${name}: data nezachycena${C.reset}\n`);
    return [];
  }

  const matches = parseOffer(offerData, name);
  process.stdout.write(`  ${C.green}✓ ${name}: ${matches.length} zápasů (${matches.filter((m) => m.odds["1"]).length} s kurzy 1X2)${C.reset}\n`);
  return matches;
}

function parseMatchDetail(data) {
  const match = data.match || data;
  const eventTables = match.eventTables || [];
  const groups = match.eventTableGroups || [];

  const tableToGroup = {};
  for (const g of groups) {
    for (const tid of (g.tableIds || [])) tableToGroup[tid] = g.groupName;
  }

  const result = {};
  for (const table of eventTables) {
    const groupName = tableToGroup[table.id] || "Ostatní";
    const tableName = table.name || "?";
    if (!result[groupName]) result[groupName] = {};
    const odds = {};
    for (const box of (table.boxes || [])) {
      for (const cell of (box.cells || [])) {
        if (!cell.active) continue;
        const o = parseFloat(cell.odd || 0);
        if (o <= 1) continue;
        odds[cell.name] = o;
      }
    }
    if (Object.keys(odds).length > 0) result[groupName][tableName] = odds;
  }
  return result;
}

async function scrapeMatchDetails(context, matches, limit) {
  const toScrape = (limit ? matches.slice(0, limit) : matches).filter((m) => m.url);
  if (!toScrape.length) return;
  console.log(`\n  ${C.dim}Načítám detaily ${toScrape.length} zápasů...${C.reset}`);

  for (let i = 0; i < toScrape.length; i++) {
    const match = toScrape[i];
    process.stdout.write(`  ${C.dim}[${i + 1}/${toScrape.length}] ${match.home} - ${match.away}...${C.reset}\r`);

    const page = await context.newPage();
    let detailData = null;

    page.on("response", async (resp) => {
      try {
        if (!resp.url().includes("/rest/offer/v3/matches/")) return;
        if (resp.status() !== 200) return;
        const body = await resp.json();
        if (body?.match?.eventTables?.length > 0) detailData = body;
      } catch {
        // noop
      }
    });

    const detailUrl = match.url.endsWith("/co-se-sazi") ? match.url : `${match.url}/co-se-sazi`;
    await page.goto(detailUrl, { waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {});

    await page.evaluate(() => {
      document.querySelectorAll("button").forEach((btn) => {
        const t = btn.textContent?.trim();
        if (t === "Schválit vše" || t === "NEMÁM ZÁJEM" || t === "Nemám zájem") btn.click();
      });
    }).catch(() => {});

    const deadline = Date.now() + 12000;
    while (!detailData && Date.now() < deadline) await sleep(300);

    await page.close();

    if (detailData) {
      match.markets = parseMatchDetail(detailData);
      const tabNames = Object.values(match.markets).flatMap((g) => Object.keys(g));
      process.stdout.write(`  ${C.green}✓ ${match.home} - ${match.away}: ${tabNames.length} trhů${C.reset}\n`);
    } else {
      process.stdout.write(`  ${C.yellow}⚠ ${match.home} - ${match.away}: detail nezachycen${C.reset}\n`);
    }

    if ((i + 1) % 5 === 0) {
      process.stdout.write(`  ${C.dim}Pauza 5s...${C.reset}\r`);
      await sleep(5000);
    } else {
      await sleep(1500);
    }
  }
}

function printMatchDetails(matches) {
  const withMarkets = matches.filter((m) => m.markets);
  if (!withMarkets.length) return;
  console.log(`\n\n  ${C.bright}${C.cyan}══ DETAILNÍ TRHY ════════════════════════════════════${C.reset}`);
  for (const m of withMarkets) {
    console.log(`\n  ${C.bright}${m.home} - ${m.away}${C.reset}  ${C.dim}[${fmtTime(m.startTime)}]${C.reset}`);
    for (const [groupName, tables] of Object.entries(m.markets)) {
      console.log(`\n  ${C.cyan}  ── ${groupName} ──${C.reset}`);
      for (const [tableName, odds] of Object.entries(tables)) {
        const entries = Object.entries(odds);
        if (!entries.length) continue;
        const str = entries.slice(0, 6)
          .map(([k, v]) => `${C.dim}${k.substring(0, 18)}:${C.reset}${C.bright}${v.toFixed(2)}${C.reset}`)
          .join("  ");
        console.log(`    ${C.yellow}${tableName}${C.reset}`);
        console.log(`      ${str}`);
      }
    }
  }
}

function printMatches(matches) {
  if (!matches.length) { console.log(`\n  ${C.yellow}Žádné zápasy.${C.reset}\n`); return; }
  const byLeague = {};
  matches.forEach((m) => { (byLeague[m.league] = byLeague[m.league] || []).push(m); });
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
  const doDetails = args.includes("--details");
  const limitIdx = args.indexOf("--limit");
  const detailLimit = limitIdx !== -1 && args[limitIdx + 1] ? parseInt(args[limitIdx + 1], 10) : null;

  let sportIds = [16];
  const sIdx = args.indexOf("--sport");
  if (sIdx !== -1 && args[sIdx + 1]) {
    sportIds = args[sIdx + 1] === "all"
      ? Object.keys(CFG.sports).map(Number)
      : args[sIdx + 1].split(",").map(Number);
  }

  console.clear();
  console.log(`${C.bright}${C.cyan}\n  ╔══════════════════════════════════════════════╗\n  ║   TIPSPORT SCRAPER  ·  Playwright            ║\n  ║   ${new Date().toLocaleTimeString("cs-CZ").padEnd(42)}║\n  ╚══════════════════════════════════════════════╝${C.reset}\n`);

  const browser = await chromium.launch({
    headless: false,
    args: ["--no-sandbox", "--disable-blink-features=AutomationControlled"],
  });

  const statePath = "tipsport_state.json";
  const context = await browser.newContext({
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    viewport: { width: 1280, height: 800 }, locale: "cs-CZ",
    extraHTTPHeaders: { "accept-language": "cs-CZ,cs;q=0.9" },
    storageState: fs.existsSync(statePath) ? statePath : undefined,
  });
  await context.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => false });
    window.chrome = { runtime: {} };
  });

  const cookieClicked = { done: false };
  const allMatches = [];

  for (let i = 0; i < sportIds.length; i++) {
    const id = sportIds[i];
    const info = CFG.sports[id];
    if (!info) continue;
    if (i > 0) await sleep(2000);
    process.stdout.write(`  ${C.dim}[${i + 1}/${sportIds.length}] Načítám ${info.name}...${C.reset}\r`);
    const matches = await scrapeSport(context, info.name, info.path, cookieClicked);
    allMatches.push(...matches);
    if (cookieClicked.done && !fs.existsSync(statePath)) {
      await context.storageState({ path: statePath });
      process.stdout.write(`  ${C.dim}✓ Cookie stav uložen${C.reset}\n`);
    }
  }

  if (doDetails && allMatches.length > 0) {
    await scrapeMatchDetails(context, allMatches, detailLimit);
  }

  await browser.close();

  console.log(`\n  ${C.bright}Celkem: ${allMatches.length} zápasů${C.reset}`);
  printMatches(allMatches);
  if (doDetails) printMatchDetails(allMatches);

  if (args.includes("--json")) {
    fs.writeFileSync(CFG.outputFile, JSON.stringify({
      timestamp: new Date().toISOString(),
      count: allMatches.length,
      matches: allMatches,
    }, null, 2));
    console.log(`\n  ${C.green}✓ Uloženo: ${CFG.outputFile}${C.reset}`);
  }

  console.log(`\n  ${C.dim}${new Date().toLocaleString("cs-CZ")}${C.reset}\n`);
}

run().catch((e) => {
  console.error(`\n${C.red}Chyba: ${e.message}${C.reset}`);
  process.exit(1);
});
