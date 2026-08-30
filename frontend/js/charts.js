const charts = new Map();

export function renderBarChart(canvas, labels, values, label) {
  destroy(canvas);
  const Chart = window.Chart;
  if (!Chart) return;
  charts.set(
    canvas,
    new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [{ label, data: values, backgroundColor: "#1890ff" }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        animation: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? false : undefined,
      },
    }),
  );
}

export function renderDoughnut(canvas, labels, values) {
  destroy(canvas);
  const Chart = window.Chart;
  if (!Chart) return;
  charts.set(
    canvas,
    new Chart(canvas, {
      type: "doughnut",
      data: {
        labels,
        datasets: [
          {
            data: values,
            backgroundColor: ["#1890ff", "#52c41a", "#722ed1", "#13c2c2", "#faad14", "#eb2f96", "#2f54eb"],
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? false : undefined,
      },
    }),
  );
}

function destroy(canvas) {
  const existing = charts.get(canvas);
  if (existing) {
    existing.destroy();
    charts.delete(canvas);
  }
}
