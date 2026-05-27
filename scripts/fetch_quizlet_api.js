import fs from "node:fs";
import { chromium } from "playwright";

const SET_ID = "1061896430";
const OUT = "data/quizlet_api_raw.json";

async function main() {
  // Quizlet's public webapi blocks headless Chromium. A visible browser window
  // returns the same JSON that the website uses for the set page.
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage({
    userAgent:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
  });
  const url =
    `https://quizlet.com/webapi/3.4/studiable-item-documents` +
    `?filters%5BstudiableContainerId%5D=${SET_ID}` +
    `&filters%5BstudiableContainerType%5D=1&perPage=500&page=1`;
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  const text = await page.locator("body").innerText({ timeout: 60000 });
  JSON.parse(text);
  fs.writeFileSync(OUT, text + "\n", "utf8");
  await browser.close();
  console.log(`saved ${OUT}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
