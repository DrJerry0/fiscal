async function loadKeywordChart() {
    const response = await fetch("data/keywords.json");
    const data = await response.json();

    const topKeywords = data.slice(0, 20);

    const labels = topKeywords.map(item => item.keyword);
    const scores = topKeywords.map(item => item.score);

    const ctx = document.getElementById("keywordChart");

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "TF-IDF 점수",
                data: scores
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: "정부 AI 정책예산 핵심 키워드 TOP 20"
                }
            }
        }
    });
}

loadKeywordChart();