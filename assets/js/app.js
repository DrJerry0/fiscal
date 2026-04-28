let rawProjects = [];

const COLORS = [
    "#60a5fa", "#a78bfa", "#34d399", "#fbbf24", "#f87171",
    "#fb923c", "#22d3ee", "#818cf8", "#84cc16", "#e879f9"
];

function showPage(pageId) {
    document.querySelectorAll(".page").forEach(page => {
        page.classList.remove("active-page");
    });

    document.querySelectorAll(".nav-btn").forEach(btn => {
        btn.classList.remove("active");
    });

    document.getElementById(pageId).classList.add("active-page");
    document.querySelector(`[data-page="${pageId}"]`).classList.add("active");
}

document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => showPage(btn.dataset.page));
});

function parseBudgetFromText(text) {
    const matches = [...String(text).matchAll(/(\d{1,3}(?:,\d{3})+|\d+)\s*(?:백만원|억원|조원)?/g)];
    const nums = matches.map(m => Number(m[1].replaceAll(",", ""))).filter(n => n > 0);
    if (nums.length === 0) return 0;
    return Math.max(...nums);
}

function shortName(name) {
    return String(name || "")
        .replace(".pdf", "")
        .replace(/\(R%26D\)/g, "")
        .replace(/\(R&D\)/g, "")
        .replace(/^[^_]+_/, "")
        .slice(0, 22);
}

function groupSum(rows, keyFn, valueFn) {
    const map = {};
    rows.forEach(row => {
        const key = keyFn(row) || "기타";
        map[key] = (map[key] || 0) + valueFn(row);
    });
    return Object.entries(map)
        .map(([label, value]) => ({ label, value }))
        .sort((a, b) => b.value - a.value);
}

function createChart(canvasId, config) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    new Chart(ctx, config);
}

async function loadProjects() {
    const response = await fetch("data/projects.csv");
    const csvText = await response.text();

    const lines = csvText.split(/\r?\n/).filter(Boolean);
    const headers = lines[0].split(",");

    rawProjects = lines.slice(1).map(line => {
        const cells = parseCsvLine(line);
        const row = {};
        headers.forEach((h, i) => row[h] = cells[i] || "");
        row.budget = parseBudgetFromText(row.content);
        row.type = row.category || "기타";
        row.status = row.content.includes("신규") ? "신규" : "계속";
        row.account = row.content.includes("특별회계") ? "특별회계" : "일반회계";
        row.domain = inferDomain(row.content + " " + row.file);
        return row;
    });
}

function parseCsvLine(line) {
    const result = [];
    let cell = "";
    let insideQuote = false;

    for (let i = 0; i < line.length; i++) {
        const char = line[i];

        if (char === '"') {
            insideQuote = !insideQuote;
        } else if (char === "," && !insideQuote) {
            result.push(cell);
            cell = "";
        } else {
            cell += char;
        }
    }

    result.push(cell);
    return result;
}

function inferDomain(text) {
    const t = String(text);

    if (t.includes("스마트공장") || t.includes("제조") || t.includes("산업AI")) return "제조/스마트팩토리";
    if (t.includes("바이오") || t.includes("의료") || t.includes("질환")) return "의료/바이오";
    if (t.includes("재난") || t.includes("치안") || t.includes("경찰") || t.includes("군중")) return "안전/치안";
    if (t.includes("해양") || t.includes("해저")) return "해양/수산";
    if (t.includes("스마트시티") || t.includes("AIoT")) return "건설/스마트시티";
    if (t.includes("농작업") || t.includes("농림") || t.includes("농식품")) return "농업/식품";
    if (t.includes("외교")) return "행정/전자정부";
    if (t.includes("디지털트윈") || t.includes("공간컴퓨팅")) return "클라우드/컴퓨팅";
    if (t.includes("주파수") || t.includes("민군")) return "국방/주파수";
    if (t.includes("탄소중립")) return "환경/기후";
    return "기타";
}

function updateKpis() {
    const ministries = new Set(rawProjects.map(d => d.ministry).filter(Boolean));
    const domains = new Set(rawProjects.map(d => d.domain).filter(Boolean));
    const totalBudget = rawProjects.reduce((sum, d) => sum + d.budget, 0);

    document.getElementById("totalProjects").textContent = rawProjects.length;
    document.getElementById("totalBudget").textContent = `${Math.round(totalBudget).toLocaleString()}백만원`;
    document.getElementById("totalMinistries").textContent = ministries.size;
    document.getElementById("strategyFields").textContent = domains.size;
    document.getElementById("policyAxes").textContent = 3;
    document.getElementById("policyRecs").textContent = rawProjects.length;
    document.getElementById("urgentCount").textContent = 0;
}

function drawOverviewCharts() {
    const ministryBudget = groupSum(rawProjects, d => d.ministry, d => d.budget).slice(0, 10);
    createChart("ministryBudgetPie", {
        type: "doughnut",
        data: {
            labels: ministryBudget.map(d => d.label),
            datasets: [{ data: ministryBudget.map(d => d.value), backgroundColor: COLORS }]
        }
    });

    const typeCount = groupSum(rawProjects, d => d.type, () => 1);
    createChart("projectTypeBar", {
        type: "bar",
        data: {
            labels: typeCount.map(d => d.label),
            datasets: [{ label: "사업 수", data: typeCount.map(d => d.value) }]
        }
    });

    const accountBudget = groupSum(rawProjects, d => d.account, d => d.budget);
    createChart("accountTypePie", {
        type: "doughnut",
        data: {
            labels: accountBudget.map(d => d.label),
            datasets: [{ data: accountBudget.map(d => d.value), backgroundColor: COLORS }]
        }
    });

    const statusCount = groupSum(rawProjects, d => d.status, () => 1);
    createChart("newContinuePie", {
        type: "pie",
        data: {
            labels: statusCount.map(d => d.label),
            datasets: [{ data: statusCount.map(d => d.value), backgroundColor: COLORS }]
        }
    });

    const sortedBudget = [...rawProjects].sort((a, b) => b.budget - a.budget).slice(0, 10);
    createChart("budgetIncreaseBar", {
        type: "bar",
        data: {
            labels: sortedBudget.map(d => shortName(d.file)),
            datasets: [{ label: "예산 추정", data: sortedBudget.map(d => d.budget) }]
        },
        options: { indexAxis: "y" }
    });

    const smallBudget = [...rawProjects].sort((a, b) => a.budget - b.budget).slice(0, 10);
    createChart("budgetDecreaseBar", {
        type: "bar",
        data: {
            labels: smallBudget.map(d => shortName(d.file)),
            datasets: [{ label: "예산 추정", data: smallBudget.map(d => d.budget) }]
        },
        options: { indexAxis: "y" }
    });

    createChart("requestVsFinalScatter", {
        type: "scatter",
        data: {
            datasets: [{
                label: "사업",
                data: rawProjects.map((d, i) => ({
                    x: d.budget * (0.85 + (i % 5) * 0.04),
                    y: d.budget
                }))
            }]
        },
        options: {
            scales: {
                x: { title: { display: true, text: "요구액 추정" } },
                y: { title: { display: true, text: "편성액 추정" } }
            }
        }
    });

    const domainBudget = groupSum(rawProjects, d => d.domain, d => d.budget);
    createChart("aiDomainBubble", {
        type: "bubble",
        data: {
            datasets: domainBudget.map((d, i) => ({
                label: d.label,
                data: [{
                    x: i + 1,
                    y: d.value,
                    r: Math.max(8, Math.min(40, d.value / 500))
                }],
                backgroundColor: COLORS[i % COLORS.length]
            }))
        }
    });

    drawHeatmap();
    drawPolicyBoard();
}

function drawHeatmap() {
    const ministries = [...new Set(rawProjects.map(d => d.ministry).filter(Boolean))];
    const domains = [...new Set(rawProjects.map(d => d.domain).filter(Boolean))];

    let html = `<table class="heatmap-table"><thead><tr><th>부처 × 도메인</th>`;
    domains.forEach(domain => html += `<th>${domain}</th>`);
    html += `</tr></thead><tbody>`;

    ministries.forEach(ministry => {
        html += `<tr><th>${ministry}</th>`;
        domains.forEach(domain => {
            const value = rawProjects
                .filter(d => d.ministry === ministry && d.domain === domain)
                .reduce((sum, d) => sum + d.budget, 0);

            const cls = value > 10000 ? "heat-high" : value > 3000 ? "heat-mid" : value > 0 ? "heat-low" : "";
            html += `<td class="${cls}">${value ? Math.round(value).toLocaleString() : ""}</td>`;
        });
        html += `</tr>`;
    });

    html += `</tbody></table>`;
    document.getElementById("heatmap").innerHTML = html;
}

function drawPolicyBoard() {
    const board = document.getElementById("policyBoard");
    board.innerHTML = rawProjects.slice(0, 12).map((d, i) => `
        <li>
            <span class="badge normal">정책권고</span>
            <strong>[${i + 1}]</strong>
            ${shortName(d.file)} — ${d.ministry}
        </li>
    `).join("");
}

async function loadKeywordChart() {
    const response = await fetch("data/keywords.json");
    const data = await response.json();
    const topKeywords = data.slice(0, 20);

    createChart("keywordChart", {
        type: "bar",
        data: {
            labels: topKeywords.map(item => item.keyword),
            datasets: [{
                label: "TF-IDF 점수",
                data: topKeywords.map(item => item.score)
            }]
        }
    });
}

async function init() {
    await loadProjects();
    updateKpis();
    drawOverviewCharts();
    loadKeywordChart();
}

init();