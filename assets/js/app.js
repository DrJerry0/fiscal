const COLORS = [
    "#2563eb", "#7c3aed", "#0891b2", "#16a34a", "#f97316",
    "#dc2626", "#9333ea", "#0f766e", "#ca8a04", "#be123c"
];

const STANDARD_MINISTRIES = [
    "감사원", "개인정보위원회", "경찰청", "고용노동부", "과학기술정보통신부",
    "관세청", "교육부", "국가데이터처", "국가유산청", "국민권익위원회",
    "국방부", "국세청", "국토교통부", "금융위원회", "기상청",
    "기획예산처", "기후에너지환경부", "농립축산식품부", "농촌진흥청",
    "대법원", "문화체육관광부", "방송미디어통신위원회", "방위사업청",
    "법무부", "법제처", "병무청", "보건복지부", "산림청",
    "산업통상부", "소방청", "식품의약품안전처", "우주항공청",
    "인사혁신처", "조달청", "중소벤처기업부", "지식재산처",
    "질병관리청", "해양경찰청", "해양수산부", "행정안전부"
];

let chartInstances = {};

function showPage(pageId) {
    document.querySelectorAll(".page").forEach(page => {
        page.classList.remove("active-page");
    });

    document.querySelectorAll(".nav-btn").forEach(btn => {
        btn.classList.remove("active");
    });

    const page = document.getElementById(pageId);
    const button = document.querySelector(`[data-page="${pageId}"]`);

    if (page) page.classList.add("active-page");
    if (button) button.classList.add("active");
}

document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        showPage(btn.dataset.page);
    });
});

async function loadJson(path) {
    const response = await fetch(path);
    if (!response.ok) {
        throw new Error(`${path} 파일을 불러오지 못했습니다.`);
    }
    return await response.json();
}

function formatBudget(value) {
    const num = Number(value || 0);
    if (num >= 10000) {
        return `${(num / 10000).toFixed(1)}조원`;
    }
    return `${num.toLocaleString()}백만원`;
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function updateKpis(summary) {
    setText("totalProjects", Number(summary.total_projects || 0).toLocaleString());
    setText("totalBudget", formatBudget(summary.total_budget));
    setText("totalMinistries", Number(summary.total_ministries || 0).toLocaleString());
    setText("strategyFields", Number(summary.strategy_fields || 0).toLocaleString());
    setText("policyAxes", Number(summary.policy_axes || 0).toLocaleString());
    setText("policyRecs", Number(summary.policy_recommendations || 0).toLocaleString());
    setText("urgentCount", Number(summary.urgent_or_overdue || 0).toLocaleString());
}

function createChart(canvasId, config) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    chartInstances[canvasId] = new Chart(canvas, config);
}

function drawPieChart(canvasId, title, rows) {
    createChart(canvasId, {
        type: "doughnut",
        data: {
            labels: rows.map(d => d.label),
            datasets: [{
                data: rows.map(d => d.value),
                backgroundColor: COLORS
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: "bottom"
                },
                title: {
                    display: false,
                    text: title
                }
            }
        }
    });
}

function drawBarChart(canvasId, label, rows, horizontal = false) {
    createChart(canvasId, {
        type: "bar",
        data: {
            labels: rows.map(d => d.label || d.project_name),
            datasets: [{
                label,
                data: rows.map(d => d.value ?? d.change_amount ?? d.budget_2026)
            }]
        },
        options: {
            indexAxis: horizontal ? "y" : "x",
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    ticks: {
                        callback: value => {
                            const label = this?.getLabelForValue ? this.getLabelForValue(value) : value;
                            return label;
                        }
                    }
                }
            }
        }
    });
}

function shorten(text, max = 18) {
    const str = String(text || "");
    return str.length > max ? str.slice(0, max) + "…" : str;
}

function drawIncreaseDecrease(canvasId, label, rows, isDecrease = false) {
    createChart(canvasId, {
        type: "bar",
        data: {
            labels: rows.map(d => shorten(d.project_name, 20)),
            datasets: [{
                label,
                data: rows.map(d => d.change_amount)
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        afterLabel: context => {
                            const row = rows[context.dataIndex];
                            return [
                                `부처: ${row.ministry}`,
                                `2026 예산: ${Number(row.budget_2026 || 0).toLocaleString()}백만원`
                            ];
                        }
                    }
                }
            }
        }
    });
}

function drawRequestVsFinal(rows) {
    const filtered = rows
        .filter(d => Number(d.request_2026) > 0 || Number(d.budget_2026) > 0)
        .slice(0, 120);

    createChart("requestVsFinalScatter", {
        type: "scatter",
        data: {
            datasets: [{
                label: "사업",
                data: filtered.map(d => ({
                    x: Number(d.request_2026 || 0),
                    y: Number(d.budget_2026 || 0),
                    project_name: d.project_name,
                    ministry: d.ministry
                }))
            }]
        },
        options: {
            responsive: true,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: context => {
                            const p = context.raw;
                            return `${shorten(p.project_name, 30)} / 요구 ${Number(p.x).toLocaleString()} / 편성 ${Number(p.y).toLocaleString()}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: "2026 요구액(백만원)"
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: "2026 편성액(백만원)"
                    }
                }
            }
        }
    });
}

function drawDomainBubble(rows) {
    createChart("aiDomainBubble", {
        type: "bubble",
        data: {
            datasets: rows.map((d, i) => ({
                label: d.label,
                data: [{
                    x: i + 1,
                    y: Number(d.value || 0),
                    r: Math.max(8, Math.min(45, Number(d.value || 0) / 20000))
                }],
                backgroundColor: COLORS[i % COLORS.length]
            }))
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: "bottom"
                },
                tooltip: {
                    callbacks: {
                        label: context => {
                            const label = context.dataset.label;
                            const value = context.raw.y;
                            return `${label}: ${Number(value).toLocaleString()}백만원`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: "AI 분야"
                    },
                    ticks: {
                        stepSize: 1
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: "예산(백만원)"
                    }
                }
            }
        }
    });
}

function drawHeatmap(rows) {
    const container = document.getElementById("heatmap");
    if (!container || !rows.length) return;

    const domains = [...new Set(rows.flatMap(row =>
        Object.keys(row).filter(k => k !== "ministry")
    ))];

    let maxValue = 0;
    rows.forEach(row => {
        domains.forEach(domain => {
            maxValue = Math.max(maxValue, Number(row[domain] || 0));
        });
    });

    let html = `<table class="heatmap-table"><thead><tr><th>부처 × AI 도메인</th>`;
    domains.forEach(domain => {
        html += `<th>${domain}</th>`;
    });
    html += `</tr></thead><tbody>`;

    rows.forEach(row => {
        html += `<tr><th>${row.ministry}</th>`;
        domains.forEach(domain => {
            const value = Number(row[domain] || 0);
            let cls = "";

            if (value > 0) {
                const ratio = value / maxValue;
                if (ratio >= 0.6) cls = "heat-high";
                else if (ratio >= 0.2) cls = "heat-mid";
                else cls = "heat-low";
            }

            html += `<td class="${cls}">${value ? value.toLocaleString() : ""}</td>`;
        });
        html += `</tr>`;
    });

    html += `</tbody></table>`;
    container.innerHTML = html;
}

function drawPolicyBoard(recommendations) {
    const board = document.getElementById("policyBoard");
    if (!board) return;

    const topItems = recommendations.slice(0, 20);

    board.innerHTML = topItems.map((item, index) => {
        const urgent = item.due_status === "기한임박" || item.due_status === "초과";
        const badgeClass = urgent ? "urgent" : "normal";
        const badgeText = urgent ? item.due_status : item.priority;

        return `
            <li>
                <span class="badge ${badgeClass}">${badgeText}</span>
                <strong>${index + 1}. ${shorten(item.title, 42)}</strong>
                <span> | ${item.ministry} | ${item.domain} | ${Number(item.budget_2026 || 0).toLocaleString()}백만원</span>
            </li>
        `;
    }).join("");
}

function drawDashboardCharts(charts) {
    drawPieChart(
        "ministryBudgetPie",
        "부처별 예산 비중",
        charts.ministry_budget_top10 || []
    );

    drawBarChart(
        "projectTypeBar",
        "사업 수",
        charts.project_type_distribution || []
    );

    drawPieChart(
        "accountTypePie",
        "회계유형별 예산",
        charts.account_budget || []
    );

    drawPieChart(
        "newContinuePie",
        "신규/계속사업 분포",
        charts.status_distribution || []
    );

    drawIncreaseDecrease(
        "budgetIncreaseBar",
        "증가액(백만원)",
        charts.increase_top10 || []
    );

    drawIncreaseDecrease(
        "budgetDecreaseBar",
        "감소액(백만원)",
        charts.decrease_top10 || [],
        true
    );

    drawRequestVsFinal(charts.request_vs_final || []);
    drawDomainBubble(charts.domain_budget || []);
    drawHeatmap(charts.domain_ministry_heatmap || []);
}

async function loadKeywordChart() {
    const keywordCanvas = document.getElementById("keywordChart");
    if (!keywordCanvas) return;

    const data = await loadJson("data/keywords.json");
    const topKeywords = data.slice(0, 20);

    createChart("keywordChart", {
        type: "bar",
        data: {
            labels: topKeywords.map(item => item.keyword),
            datasets: [{
                label: "TF-IDF 점수",
                data: topKeywords.map(item => item.score)
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

let ministryAnalysisData = null;

function objectToChartRows(obj) {
    return Object.entries(obj || {}).map(([label, value]) => ({
        label,
        value: Number(value || 0)
    }));
}

function renderTable(containerId, rows) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!rows || rows.length === 0) {
        container.innerHTML = "<p>표시할 사업이 없습니다.</p>";
        return;
    }

    container.innerHTML = `
        <table class="analysis-table">
            <thead>
                <tr>
                    <th>사업명</th>
                    <th>분야</th>
                    <th>유형</th>
                    <th>2026 예산</th>
                    <th>증감률</th>
                </tr>
            </thead>
            <tbody>
                ${rows.map(row => `
                    <tr>
                        <td>${row.project_name || ""}</td>
                        <td>${row.domain || ""}</td>
                        <td>${row.category || ""}</td>
                        <td class="num">${Number(row.budget_2026 || 0).toLocaleString()}백만원</td>
                        <td class="num">${Number(row.change_rate || 0).toFixed(1)}%</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}

function populateMinistryDropdown(data) {
    const select = document.getElementById("ministrySelect");
    if (!select) return;

    select.innerHTML = `<option value="">부처 선택...</option>` +
        STANDARD_MINISTRIES.map(m => `<option value="${m}">${m}</option>`).join("");

    select.addEventListener("change", () => {
        renderSelectedMinistry(select.value);
    });

    select.value = STANDARD_MINISTRIES[0];
    renderSelectedMinistry(STANDARD_MINISTRIES[0]);
}

function renderSelectedMinistry(ministryName) {
    if (!ministryAnalysisData || !ministryName) return;

    const item = ministryAnalysisData.items.find(d => d.ministry === ministryName) || {
        ministry: ministryName,
        project_count: 0,
        total_budget: 0,
        avg_budget: 0,
        new_count: 0,
        category_distribution: {},
        domain_budget_top10: {},
        top_projects: []
    };

    setText("selectedMinistryProjects", Number(item.project_count || 0).toLocaleString());
    setText("selectedMinistryBudget", formatBudget(item.total_budget || 0));
    setText("selectedMinistryAvg", formatBudget(item.avg_budget || 0));
    setText("selectedMinistryNew", Number(item.new_count || 0).toLocaleString());

    drawPieChart(
        "selectedMinistryCategoryChart",
        "사업유형 분포",
        objectToChartRows(item.category_distribution)
    );

    drawBarChart(
        "selectedMinistryDomainChart",
        "예산",
        objectToChartRows(item.domain_budget_top10),
        true
    );

    renderTable("selectedMinistryProjectTable", item.top_projects || []);
}

async function loadMinistryAnalysis() {
    ministryAnalysisData = await loadJson("data/ministry_analysis.json");

    drawBarChart(
        "ministryProjectCountChart",
        "과제 수",
        ministryAnalysisData.ministry_project_count || [],
        true
    );

    drawBarChart(
        "ministryBudgetChart",
        "예산",
        ministryAnalysisData.ministry_budget || [],
        true
    );

    populateMinistryDropdown(ministryAnalysisData);
}

async function initDashboard() {
    try {
        const [summary, charts, recommendations] = await Promise.all([
            loadJson("data/overview_summary.json"),
            loadJson("data/dashboard_charts.json"),
            loadJson("data/policy_recommendations.json")
        ]);

        updateKpis(summary);
        drawDashboardCharts(charts);
        drawPolicyBoard(recommendations);
        await loadKeywordChart();
        await loadMinistryAnalysis();

    } catch (error) {
        console.error(error);
        alert("대시보드 데이터를 불러오는 중 오류가 발생했습니다. data/*.json 파일이 GitHub에 올라갔는지 확인하십시오.");
    }
}

initDashboard();