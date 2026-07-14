import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Brain,
  CalendarDays,
  Database,
  Gauge,
  HeartPulse,
  Layers3,
  LineChart,
  MapPin,
  Radio,
  RefreshCw,
  ShieldAlert,
  SlidersHorizontal,
  Sparkles,
  Wind,
} from "lucide-react";

const NAV_ITEMS = [
  { id: "dashboard", label: "Tổng quan", icon: Gauge },
  { id: "model", label: "Dự báo", icon: Sparkles },
  { id: "analytics", label: "Phân tích", icon: LineChart },
  { id: "data", label: "Mô hình & Dữ liệu", icon: Database },
];
const PM25_SCALE = [
  {
    key: "Good",
    max: 9,
    label: "Tốt",
    color: "#4edea3",
    text: "Không khí ở mức chấp nhận được.",
  },
  {
    key: "Moderate",
    max: 35.4,
    label: "Trung bình",
    color: "#f8d66d",
    text: "Nhóm nhạy cảm nên theo dõi khi hoạt động ngoài trời lâu.",
  },
  {
    key: "USG",
    max: 55.4,
    label: "Kém cho nhóm nhạy cảm",
    color: "#ff9f43",
    text: "Trẻ em, người lớn tuổi và người có bệnh hô hấp nên giảm vận động ngoài trời kéo dài.",
  },
  {
    key: "Unhealthy",
    max: 125.4,
    label: "Xấu",
    color: "#fc7c78",
    text: "Nên giảm thời gian ngoài trời; nhóm nhạy cảm nên tránh vận động mạnh.",
  },
  {
    key: "Very Unhealthy",
    max: 225.4,
    label: "Rất xấu",
    color: "#b893ff",
    text: "Nên hạn chế ra ngoài và giảm các hoạt động làm tăng nhịp thở.",
  },
  {
    key: "Hazardous",
    max: Infinity,
    label: "Nguy hại",
    color: "#d16a8a",
    text: "Cần tránh tiếp xúc ngoài trời nếu có thể.",
  },
];

const CITY_REGIONS = {
  "Hà Nội": "Miền Bắc",
  "TP.HCM": "Miền Nam",
  "Đà Nẵng": "Miền Trung",
};


const MANUAL_FORECAST_GROUPS = [
  {
    title: "Ô nhiễm hiện tại",
    fields: [
      ["pm25", "PM2.5", "µg/m³", 0, 500, 0.1],
      ["pm10", "PM10", "µg/m³", 0, 800, 0.1],
      ["o3", "O₃", "µg/m³", 0, 500, 0.1],
      ["no2", "NO₂", "µg/m³", 0, 500, 0.1],
      ["so2", "SO₂", "µg/m³", 0, 500, 0.1],
      ["co", "CO", "µg/m³", 0, 50000, 1],
    ],
  },
  {
    title: "Thời tiết",
    fields: [
      ["temp", "Nhiệt độ", "°C", -10, 55, 0.1],
      ["humidity", "Độ ẩm", "%", 0, 100, 1],
      ["wind_speed", "Tốc độ gió", "km/h", 0, 150, 0.1],
    ],
  },
  {
    title: "Lịch sử PM2.5",
    fields: [
      ["pm25_lag_24h", "Cùng giờ hôm qua", "µg/m³", 0, 500, 0.1],
      ["pm25_roll_24h", "Trung bình 24 giờ", "µg/m³", 0, 500, 0.1],
      ["pm25_lag_168h", "Cùng giờ tuần trước", "µg/m³", 0, 500, 0.1],
    ],
  },
];

const MANUAL_FORECAST_FIELDS = MANUAL_FORECAST_GROUPS.flatMap((group) => group.fields);

const POLLUTANTS = [
  ["pm25", "PM2.5", "µg/m³"],
  ["pm10", "PM10", "µg/m³"],
  ["o3", "O3", "µg/m³"],
  ["no2", "NO2", "µg/m³"],
  ["so2", "SO2", "µg/m³"],
  ["co", "CO", "µg/m³"],
];

function normalizeCityName(value = "") {
  if (value.includes("Hà") || value.includes("Nội")) return "Hà Nội";
  if (value.includes("TP") || value.includes("HCM") || value.includes("Chí Minh")) return "TP.HCM";
  if (value.includes("Nẵng")) return "Đà Nẵng";
  return value;
}

function fmt(value, digits = 1) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "N/A";
  return number.toLocaleString("vi-VN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

function fmtDate(value) {
  if (!value) return "N/A";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("vi-VN", {
    hour12: false,
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function categoryFromPm25(value) {
  const number = Number(value);
  return PM25_SCALE.find((item) => number <= item.max) ?? PM25_SCALE[PM25_SCALE.length - 1];
}

function normalizedPredictionCategory(prediction, fallbackValue) {
  if (prediction?.category) {
    return {
      key: prediction.category.category,
      label: prediction.category.label_vi,
      color: prediction.category.color,
      text: prediction.category.note,
    };
  }
  const fallback = categoryFromPm25(fallbackValue);
  return {
    key: fallback.key,
    label: fallback.label,
    color: fallback.color,
    text: fallback.text,
  };
}

function riskRank(categoryKey) {
  const index = PM25_SCALE.findIndex((item) => item.key === categoryKey);
  return Math.max(index, 0);
}

function profilePayload(profile, overrides = {}) {
  const payload = {
    city: profile.city,
    observed_at: profile.datetime,
    profile,
  };

  Object.entries(overrides).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) payload[key] = Number(value);
  });

  return payload;
}

function manualValuesFromProfile(profile = {}) {
  return Object.fromEntries(
    MANUAL_FORECAST_FIELDS.map(([key]) => {
      const value = Number(profile[key]);
      return [key, Number.isFinite(value) ? String(Math.round(value * 100) / 100) : ""];
    }),
  );
}

function manualProfileFromInput(profile = {}, input = {}) {
  const overrides = Object.fromEntries(
    Object.entries(input)
      .filter(([, value]) => value !== "" && value !== null && value !== undefined)
      .map(([key, value]) => [key, Number(value)]),
  );
  return { ...profile, ...overrides };
}

function validateManualForecastInput(input = {}) {
  for (const [key, label, , min, max] of MANUAL_FORECAST_FIELDS) {
    const raw = input[key];
    const value = Number(raw);
    if (raw === "" || raw === null || raw === undefined || !Number.isFinite(value)) {
      return `${label} phải là một giá trị số.`;
    }
    if (value < min || value > max) {
      return `${label} phải nằm trong khoảng ${min}–${max}.`;
    }
  }
  return "";
}

async function requestJson(path, options) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error(`${path} failed: ${response.status}`);
  return response.json();
}

function postJson(path, payload) {
  return requestJson(path, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export default function App() {
  const [activeView, setActiveView] = useState("dashboard");
  const [forecastMode, setForecastMode] = useState("automatic");
  const [boot, setBoot] = useState({ loading: true, error: "" });
  const [model, setModel] = useState(null);
  const [cities, setCities] = useState([]);
  const [selectedCity, setSelectedCity] = useState("");
  const [predictions, setPredictions] = useState({});
  const [histories, setHistories] = useState({});
  const [refreshing, setRefreshing] = useState(false);

  const selectedItem = useMemo(
    () => cities.find((item) => item.city === selectedCity) ?? cities[0],
    [cities, selectedCity],
  );
  const selectedProfile = selectedItem?.profile;
  const selectedHistory = histories[selectedProfile?.city] ?? [];
  const selectedPrediction = predictions[selectedProfile?.city];
  const selectedForecastCategory = normalizedPredictionCategory(selectedPrediction, selectedProfile?.pm25);

  useEffect(() => {
    loadAll(false, true);
  }, []);


  async function loadAll(forceRefresh = false, showLoading = true) {
    if (showLoading) setBoot({ loading: true, error: "" });
    try {
      const [modelData, cityData] = await Promise.all([
        requestJson("/api/model"),
        requestJson(`/api/cities${forceRefresh ? "?refresh=true" : ""}`),
      ]);
      const normalizedCities = cityData.map((item) => ({
        ...item,
        city: normalizeCityName(item.city),
        profile: {
          ...item.profile,
          city: normalizeCityName(item.profile.city),
        },
      }));
      const defaultCity = normalizedCities.find((item) => item.city === "Hà Nội") ?? normalizedCities[0];
      setModel(modelData);
      setCities(normalizedCities);
      setSelectedCity((current) => normalizedCities.some((item) => item.city === current) ? current : (defaultCity?.city ?? ""));

      const [predictionResults, historyResults] = await Promise.all([
        Promise.allSettled(
          normalizedCities.map(async (item) => [
            item.city,
            await postJson("/api/predict", profilePayload(item.profile)),
          ]),
        ),
        Promise.allSettled(
          normalizedCities.map(async (item) => [
            item.city,
            await requestJson(`/api/history/${encodeURIComponent(item.city)}?limit=168`),
          ]),
        ),
      ]);
      const predictionEntries = predictionResults
        .filter((result) => result.status === "fulfilled")
        .map((result) => result.value);
      const historyEntries = historyResults
        .filter((result) => result.status === "fulfilled")
        .map((result) => result.value);
      if (!predictionEntries.length) throw new Error("No city prediction was available");
      if (predictionEntries.length !== normalizedCities.length || historyEntries.length !== normalizedCities.length) {
        console.warn("Một phần dữ liệu thành phố không tải được; giao diện tiếp tục với dữ liệu còn lại.");
      }
      setPredictions(Object.fromEntries(predictionEntries));
      setHistories(Object.fromEntries(historyEntries));
      setBoot({ loading: false, error: "" });
    } catch (error) {
      console.error(error);
      setBoot({ loading: false, error: "Không tải được API hoặc model." });
    }
  }


  async function refreshAll() {
    setRefreshing(true);
    try {
      await loadAll(true, false);
    } finally {
      setRefreshing(false);
    }
  }

  const viewProps = {
    model,
    cities,
    predictions,
    histories,
    selectedCity,
    selectedItem,
    selectedProfile,
    selectedHistory,
    selectedPrediction,
    selectedForecastCategory,
    forecastMode,
    setForecastMode,
    setSelectedCity,
    setActiveView,
    refreshing,
  };

  return (
    <div className="app">
      <TopNav
        activeView={activeView}
        setActiveView={setActiveView}
        refreshing={refreshing}
        onRefresh={refreshAll}
        cities={cities}
        selectedCity={selectedCity}
        onCityChange={setSelectedCity}
      />
      <main className="workspace">
        {boot.loading ? (
          <LoadingScreen />
        ) : boot.error ? (
          <ErrorScreen message={boot.error} onRetry={loadAll} />
        ) : (
          <>
            {activeView === "dashboard" && <DashboardHome {...viewProps} />}
            {activeView === "data" && <ModelDataLab {...viewProps} />}
            {activeView === "analytics" && <Analytics {...viewProps} />}
            {activeView === "model" && <ForecastStudio {...viewProps} />}
          </>
        )}
      </main>
    </div>
  );
}

function TopNav({
  activeView,
  setActiveView,
  refreshing,
  onRefresh,
  cities,
  selectedCity,
  onCityChange,
}) {
  return (
    <header className="top-nav">
      <div className="logo-block">
        <span className="logo-mark"><Wind size={21} /></span>
        <div className="logo-copy">
          <span className="logo">Không khí</span>
          <span className="logo-sub">Việt Nam</span>
        </div>
      </div>
      <nav className="nav-tabs" aria-label="Điều hướng chính">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={activeView === item.id ? "active" : ""}
              type="button"
              onClick={() => setActiveView(item.id)}
              aria-current={activeView === item.id ? "page" : undefined}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
      <div className="nav-actions">
        <label className="city-switcher" title="Chọn thành phố hiển thị">
          <MapPin size={16} aria-hidden="true" />
          <span>Thành phố</span>
          <select
            aria-label="Chọn thành phố"
            value={selectedCity}
            onChange={(event) => onCityChange(event.target.value)}
            disabled={!cities.length}
          >
            {!cities.length && <option value="">Đang tải</option>}
            {cities.map((item) => <option key={item.city} value={item.city}>{item.city}</option>)}
          </select>
        </label>
        <button
          className="icon-button"
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          aria-label={refreshing ? "Đang làm mới dữ liệu" : "Làm mới dữ liệu"}
          title={refreshing ? "Đang làm mới dữ liệu" : "Làm mới dữ liệu"}
        >
          <RefreshCw size={18} className={refreshing ? "spin" : ""} />
        </button>
      </div>
    </header>
  );
}
function ModelDataLab({ model, cities }) {
  const [section, setSection] = useState("model");

  return (
    <section className="screen model-data-shell">
      <div className="screen-head model-data-head">
        <div>
          <p className="eyebrow">Bằng chứng kỹ thuật và nguồn dữ liệu</p>
          <h1>Mô hình & Dữ liệu</h1>
          <p className="screen-copy">
            Theo dõi quy trình chọn model, hiệu năng trên tập Test, sai số theo thành phố
            và khả năng truy xuất nguồn gốc của dữ liệu huấn luyện.
          </p>
        </div>
        <div className="section-tabs" role="tablist" aria-label="Chọn nội dung kỹ thuật">
          <button type="button" role="tab" aria-selected={section === "model"} className={section === "model" ? "active" : ""} onClick={() => setSection("model")}>
            <Brain size={17} /> Mô hình
          </button>
          <button type="button" role="tab" aria-selected={section === "data"} className={section === "data" ? "active" : ""} onClick={() => setSection("data")}>
            <Database size={17} /> Dữ liệu
          </button>
        </div>
      </div>
      {section === "model" ? <ModelEvidence model={model} /> : <DataLab model={model} cities={cities} embedded />}
    </section>
  );
}

function ModelEvidence({ model }) {
  const suite = model?.required_model_suite ?? {};
  const comparison = suite.comparison?.length ? suite.comparison : (model?.comparison ?? []);
  const comparisonByCity = suite.comparison_by_city?.length ? suite.comparison_by_city : (model?.comparison_by_city ?? []);
  const selection = suite.selection ?? model?.selection ?? {};
  const selectedModel = selection.selected_model ?? model?.name ?? "XGBoost";
  const selectedRow = comparison.find((row) => row.model === selectedModel) ?? comparison[0] ?? {};
  const learningCurve = suite.xgboost_learning_curve?.length ? suite.xgboost_learning_curve : (model?.learning_curve ?? []);
  const protocol = suite.protocol ?? {};
  const featureImportance = model?.feature_importance ?? [];

  return (
    <div className="model-evidence">
      <div className="kpi-grid">
        <KpiCard label="Model được chọn" value={selectedModel} suffix="theo Validation RMSE" icon={Brain} tone="mint" />
        <KpiCard label="Validation RMSE" value={fmt(selectedRow.val_rmse_ug_m3, 2)} suffix="µg/m³" icon={LineChart} tone="blue" />
        <KpiCard label="Test RMSE" value={fmt(selectedRow.test_rmse_ug_m3, 2)} suffix="µg/m³" icon={BarChart3} tone="yellow" />
        <KpiCard label="Test R²" value={fmt(selectedRow.test_r2, 3)} suffix="hồi quy t + 24h" icon={Gauge} tone="green" />
      </div>

      <Panel title="So sánh ba mô hình" eyebrow="Chọn theo Validation RMSE · Test không dùng để chọn model">
        <ModelComparisonTable rows={comparison} selectedModel={selectedModel} />
        <p className="panel-note">
          XGBoost đứng đầu trên Validation RMSE. Khoảng cách Train–Validation cho thấy vẫn còn
          overfitting, vì vậy kết quả Test và sai số theo từng thành phố được báo cáo riêng.
        </p>
      </Panel>

      <div className="evidence-grid model-chart-grid">
        <Panel title="Learning curve của XGBoost" eyebrow="RMSE trên Train và Validation">
          <LearningCurveChart rows={learningCurve} />
          <p className="panel-note">
            Validation RMSE giảm rồi gần như đi ngang, trong khi Train RMSE tiếp tục giảm.
            Đây là dấu hiệu khoảng cách tổng quát hóa, không phải hai đường bắt buộc phải trùng nhau.
          </p>
        </Panel>
        <Panel title="Đặc trưng quan trọng" eyebrow="Top feature của model triển khai">
          <FeatureImportanceBars rows={featureImportance} />
          <p className="panel-note">
            Importance phản ánh mức độ model sử dụng feature, không chứng minh feature gây ra ô nhiễm.
          </p>
        </Panel>
      </div>

      <Panel title="Hiệu năng theo thành phố" eyebrow="Đánh giá trên tập Test · đơn vị µg/m³">
        <CityModelMetricsTable rows={comparisonByCity} />
        <p className="panel-note">
          Hà Nội có sai số cao hơn rõ rệt do chuỗi biến động mạnh và nhiều đỉnh PM2.5 đột ngột.
          Chỉ số tổng hợp vì vậy không nên được diễn giải như hiệu năng giống nhau ở cả ba thành phố.
        </p>
      </Panel>

      <div className="evidence-grid">
        <Panel title="Giao thức thực nghiệm" eyebrow="Không rò rỉ dữ liệu tương lai">
          <div className="protocol-list">
            <MetricPill label="Bài toán" value="Hồi quy chuỗi thời gian" />
            <MetricPill label="Target" value="PM2.5 tại đúng t + 24 giờ" />
            <MetricPill label="Chia tập" value={protocol.split ?? "Chronological 70/15/15"} />
            <MetricPill label="Tiêu chí chọn" value={protocol.selection_metric ?? "Validation RMSE"} />
          </div>
        </Panel>
        <Panel title="Giới hạn cần lưu ý" eyebrow="Diễn giải khoa học">
          <div className="source-list compact-source-list">
            <article><strong>Dự báo điểm lưới</strong><p>Mỗi thành phố dùng một điểm đại diện gần trung tâm, không đại diện cho mọi quận.</p></article>
            <article><strong>Không phải quan hệ nhân quả</strong><p>Các kịch bản đầu vào chỉ đo độ nhạy của model khi feature thay đổi.</p></article>
            <article><strong>Không phải AQI chính thức</strong><p>Đầu ra là nồng độ PM2.5 theo giờ, không phải AQI trung bình 24 giờ.</p></article>
          </div>
        </Panel>
      </div>

      <div className="evidence-grid">
        <Panel title="Ma trận nhầm lẫn" eyebrow="Nhóm rủi ro tham chiếu từ đầu ra hồi quy">
          <ConfusionMatrix rows={model?.confusion_matrix ?? []} />
        </Panel>
        <Panel title="Các lần dự báo sai lớn" eyebrow="Phân tích lỗi trên tập Test">
          <TopErrorCases rows={model?.top_error_cases ?? []} />
        </Panel>
      </div>
    </div>
  );
}

function DataLab({ model, cities, embedded = false }) {
  const data = model?.data_profile ?? {};
  const crawl = model?.crawl_manifest ?? {};
  const counts = data.city_counts ?? {};
  const providers = Object.values(crawl.sources ?? {})
    .map((source) => source?.provider)
    .filter(Boolean);
  const quality = crawl.quality ?? {};
  return (
    <section className={embedded ? "data-evidence" : "screen"}>
      <div className="screen-head">
        <div>
          <p className="eyebrow">Nguồn gốc và chất lượng</p>
          <h1>Dữ liệu</h1>
          <p className="screen-copy">Dữ liệu ô nhiễm được crawl từ CAMS Global qua Open-Meteo. Mỗi thành phố là một điểm lưới đại diện gần trung tâm, không phải số đo cho từng quận hay trạm mặt đất.</p>
        </div>
        <div className="source-card">
          <span>Kiểm định tự động</span>
          <strong>{data.quality_passed ? "Đạt" : "Cần kiểm tra"}</strong>
        </div>
      </div>

      <div className="kpi-grid">
        <KpiCard label="Số bản ghi" value={fmt(data.rows, 0)} suffix="theo giờ" icon={Database} tone="mint" />
        <KpiCard label="Mẫu có target 24h" value={fmt(data.supervised_rows_24h, 0)} suffix="mẫu" icon={Layers3} tone="blue" />
        <KpiCard label="Thành phố" value={data.cities?.length ?? cities.length} suffix="điểm đại diện" icon={MapPin} tone="green" />
        <KpiCard label="Thiếu toàn bảng" value={`${fmt((data.missing_rate ?? 0) * 100, 3)}%`} suffix="gồm lag đầu chuỗi" icon={Activity} tone="yellow" />
      </div>

      <div className="evidence-grid">
        <Panel title="Dữ liệu được lấy như thế nào" eyebrow="Crawl thật, không sinh tổng hợp">
          <div className="source-list">
            <article>
              <strong>CAMS Global qua Open-Meteo</strong>
              <p>PM2.5, PM10, O₃, NO₂, SO₂ và CO theo giờ tại ba tọa độ đại diện. Độ phân giải nguồn toàn cầu khoảng 45 km.</p>
            </article>
            <article>
              <strong>Thời tiết cùng tọa độ</strong>
              <p>Nhiệt độ, độ ẩm, gió, mưa, áp suất và mây được ghép đúng theo thời gian và được XGBoost sử dụng cùng tín hiệu ô nhiễm, lịch sử.</p>
            </article>
            <article>
              <strong>OpenStreetMap / Overpass</strong>
              <p>Số đối tượng công nghiệp được lập bản đồ được dùng như ngữ cảnh tĩnh. Đây không phải số đo phát thải và không được diễn giải như quan hệ nhân quả.</p>
            </article>
          </div>
        </Panel>
        <Panel title="Phạm vi thời gian" eyebrow="Snapshot huấn luyện">
          <div className="coverage-card">
            <strong>{fmtDate(data.start_time)}</strong>
            <span>đến</span>
            <strong>{fmtDate(data.end_time)}</strong>
            <p>Target được nối bằng đúng timestamp sau 24 giờ; không giả định 24 dòng luôn tương đương 24 giờ.</p>
          </div>
        </Panel>
      </div>

      <div className="evidence-grid">
        <Panel title="Bằng chứng crawl" eyebrow={`Run ${crawl.run_id ?? "N/A"}`}>
          <div className="source-list">
            <article>
              <strong>Thời điểm crawl</strong>
              <p>{fmtDate(crawl.created_at)} · {crawl.start_date ?? "N/A"} đến {crawl.end_date ?? "N/A"}</p>
            </article>
            <article>
              <strong>Nguồn đã ghi trong manifest</strong>
              <p>{providers.join(" · ") || "N/A"}</p>
            </article>
            <article>
              <strong>Dấu vân tay dữ liệu</strong>
              <p className="mono-copy">{shortHash(data.source_sha256)}</p>
            </article>
          </div>
        </Panel>
        <Panel title="Kết quả kiểm định" eyebrow="Data quality gate">
          <div className="metric-strip vertical">
            <MetricPill label="Trùng city + datetime" value={fmt(quality.duplicate_city_time_rows ?? 0, 0)} />
            <MetricPill label="Khoảng trống theo giờ" value={fmt(quality.non_hourly_gaps ?? 0, 0)} />
            <MetricPill label="Target khớp đúng 24h" value={`${fmt((quality.target_coverage ?? 0) * 100, 2)}%`} />
            <MetricPill label="Trạng thái" value={quality.passed ? "Đạt" : "Không đạt"} />
          </div>
        </Panel>
      </div>

      <div className="evidence-grid">
        <Panel title="Phân bố theo thành phố" eyebrow="Số giờ hợp lệ">
          <div className="feature-bars">
            {Object.entries(counts).map(([city, count]) => {
              const max = Math.max(...Object.values(counts).map(Number), 1);
              return (
                <div key={city}>
                  <div><span>{city}</span><strong>{fmt(count, 0)}</strong></div>
                  <i style={{ "--width": `${Math.max(5, (Number(count) / max) * 100)}%` }} />
                </div>
              );
            })}
          </div>
        </Panel>
        <Panel title="Feature thực sự vào model" eyebrow="Sau ablation">
          <FeatureGroupList data={data} />
        </Panel>
      </div>


    </section>
  );
}

function ModelComparisonTable({ rows, selectedModel }) {
  if (!rows.length) return <div className="empty-state">Chưa có kết quả so sánh model.</div>;
  return (
    <div className="model-table-wrap">
      <table className="model-comparison-table">
        <thead>
          <tr>
            <th>Model</th>
            <th>Val RMSE</th>
            <th>Test RMSE</th>
            <th>Test MAE</th>
            <th>Test R²</th>
            <th>Gap Val</th>
            <th>Kết quả</th>
          </tr>
        </thead>
        <tbody>
          {[...rows].sort((a, b) => Number(a.validation_rank) - Number(b.validation_rank)).map((row) => (
            <tr key={row.model} className={row.model === selectedModel ? "selected" : ""}>
              <td><strong>{row.model}</strong><small>{row.family}</small></td>
              <td>{fmt(row.val_rmse_ug_m3, 2)}</td>
              <td>{fmt(row.test_rmse_ug_m3, 2)}</td>
              <td>{fmt(row.test_mae_ug_m3, 2)}</td>
              <td>{fmt(row.test_r2, 3)}</td>
              <td>{fmt(row.val_generalization_gap_pct, 1)}%</td>
              <td><span className={row.model === selectedModel ? "selected-chip" : "candidate-chip"}>{row.model === selectedModel ? "Được chọn" : "Đối chứng"}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LearningCurveChart({ rows }) {
  if (!rows.length) return <div className="empty-state">Chưa có learning curve.</div>;
  const values = rows
    .flatMap((row) => [Number(row.train_rmse_ug_m3 ?? row.train_rmse), Number(row.val_rmse_ug_m3 ?? row.val_rmse)])
    .filter(Number.isFinite);
  const rounds = rows.map((row, index) => Number(row.round ?? index + 1));
  const width = 720;
  const height = 280;
  const pad = { left: 52, right: 18, top: 22, bottom: 42 };
  const minY = Math.floor(Math.min(...values) - 1);
  const maxY = Math.ceil(Math.max(...values) + 1);
  const minX = Math.min(...rounds);
  const maxX = Math.max(...rounds);
  const x = (value) => pad.left + ((value - minX) / Math.max(maxX - minX, 1)) * (width - pad.left - pad.right);
  const y = (value) => pad.top + ((maxY - value) / Math.max(maxY - minY, 1)) * (height - pad.top - pad.bottom);
  const pathFor = (keyA, keyB) => rows.map((row, index) => {
    const value = Number(row[keyA] ?? row[keyB]);
    return `${index ? "L" : "M"} ${x(rounds[index]).toFixed(1)} ${y(value).toFixed(1)}`;
  }).join(" ");
  const ticks = [minY, (minY + maxY) / 2, maxY];

  return (
    <div className="learning-curve">
      <div className="chart-legend">
        <span className="train">Train RMSE</span>
        <span className="validation">Validation RMSE</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Learning curve RMSE của XGBoost">
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} className="chart-grid-line" />
            <text x={pad.left - 10} y={y(tick) + 4} textAnchor="end">{fmt(tick, 1)}</text>
          </g>
        ))}
        <line x1={pad.left} x2={pad.left} y1={pad.top} y2={height - pad.bottom} className="chart-axis" />
        <line x1={pad.left} x2={width - pad.right} y1={height - pad.bottom} y2={height - pad.bottom} className="chart-axis" />
        <path d={pathFor("train_rmse_ug_m3", "train_rmse")} className="curve-train" />
        <path d={pathFor("val_rmse_ug_m3", "val_rmse")} className="curve-validation" />
        <text x={width / 2} y={height - 8} textAnchor="middle" className="axis-title">Boosting round</text>
        <text x="14" y={height / 2} textAnchor="middle" className="axis-title" transform={`rotate(-90 14 ${height / 2})`}>RMSE (µg/m³)</text>
      </svg>
    </div>
  );
}

function FeatureImportanceBars({ rows }) {
  const items = rows.slice(0, 10);
  if (!items.length) return <div className="empty-state">Chưa có feature importance.</div>;
  const max = Math.max(...items.map((row) => Number(row.importance)), 1e-6);
  return (
    <div className="importance-bars">
      {items.map((row, index) => (
        <div key={row.feature}>
          <span>{index + 1}</span>
          <strong>{featureLabel(row.feature)}</strong>
          <i><b style={{ "--width": `${(Number(row.importance) / max) * 100}%` }} /></i>
          <small>{fmt(Number(row.importance) * 100, 1)}%</small>
        </div>
      ))}
    </div>
  );
}

function CityModelMetricsTable({ rows }) {
  if (!rows.length) return <div className="empty-state">Chưa có đánh giá theo thành phố.</div>;
  return (
    <div className="model-table-wrap">
      <table className="model-comparison-table city-model-table">
        <thead>
          <tr>
            <th>Model</th>
            <th>Thành phố</th>
            <th>RMSE</th>
            <th>MAE</th>
            <th>R²</th>
            <th>Macro F1</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.model}-${row.city}`}>
              <td><strong>{row.model}</strong></td>
              <td>{row.city}</td>
              <td>{fmt(row.rmse_ug_m3, 2)}</td>
              <td>{fmt(row.mae_ug_m3, 2)}</td>
              <td>{fmt(row.r2, 3)}</td>
              <td>{fmt(row.bucket_f1_macro, 3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FeatureGroupList({ data }) {
  const groups = [
    ["Chất ô nhiễm", data.pollutant_features ?? []],
    ["Thời tiết", data.weather_features ?? []],
    ["Lag / Rolling", data.lag_features ?? []],
    ["Không gian", data.spatial_features ?? []],
    ["Feature dẫn xuất", data.engineered_features ?? []],
  ];
  return (
    <div className="feature-group-list">
      {groups.map(([name, features]) => (
        <article key={name}>
          <strong>{name}</strong>
          <p>{features.length ? features.join(", ") : "Không được model cuối chọn"}</p>
        </article>
      ))}
    </div>
  );
}

function ConfusionMatrix({ rows }) {
  if (!rows.length) return <div className="empty-state">Không có confusion matrix.</div>;
  const labels = Object.keys(rows[0]).filter((key) => key !== "label");
  return (
    <div className="confusion-wrap">
      <table className="confusion-table">
        <thead>
          <tr>
            <th>Thực tế \ Dự đoán</th>
            {labels.map((label) => (
              <th key={label}>{riskBucketLabel(label)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <td>{riskBucketLabel(row.label)}</td>
              {labels.map((label) => (
                <td key={label}>{fmt(row[label], 0)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TopErrorCases({ rows }) {
  if (!rows.length) return <div className="empty-state">Không có top error cases.</div>;
  return (
    <div className="error-case-list">
      {rows.slice(0, 5).map((row) => (
        <article key={`${row.datetime}-${row.city}`}>
          <div>
            <strong>{row.city}</strong>
            <span>{fmtDate(row.target_time)}</span>
          </div>
          <p>
            Thực tế {fmt(row.actual_pm25, 1)}, dự đoán {fmt(row.predicted_pm25, 1)} µg/m³, sai lệch tuyệt đối {fmt(row.abs_error_ug_m3, 1)}.
          </p>
          <small>{errorLabel(row.diagnostic_label ?? row.error_hypothesis)}</small>
        </article>
      ))}
    </div>
  );
}

function DashboardHome({
  model,
  cities,
  selectedCity,
  selectedItem,
  selectedProfile,
  selectedHistory,
  setSelectedCity,
  setActiveView,
  setForecastMode,
}) {
  const currentCategory = categoryFromPm25(selectedProfile?.pm25);
  const currentValue = Number(selectedProfile?.pm25 ?? 0);
  const recentPm25 = selectedHistory
    .slice(-24)
    .map((row) => Number(row.pm25))
    .filter(Number.isFinite);
  const recentStats = {
    min: recentPm25.length ? Math.min(...recentPm25) : currentValue,
    mean: recentPm25.length ? recentPm25.reduce((sum, value) => sum + value, 0) / recentPm25.length : currentValue,
    max: recentPm25.length ? Math.max(...recentPm25) : currentValue,
  };
  const advice = healthAdviceFor(currentCategory.key);
  const source = selectedItem?.source ?? {};
  const modelName = model?.name ?? model?.metrics?.model ?? "Model dự báo";
  const currentCityRows = [...cities]
    .map((item) => ({
      city: item.city,
      value: Number(item.profile.pm25 ?? 0),
      category: categoryFromPm25(item.profile.pm25),
    }))
    .sort((left, right) => right.value - left.value);
  const environment = [
    ["PM10", fmt(selectedProfile?.pm10, 1), "µg/m³"],
    ["O₃", fmt(selectedProfile?.o3, 1), "µg/m³"],
    ["NO₂", fmt(selectedProfile?.no2, 1), "µg/m³"],
    ["Nhiệt độ", fmt(selectedProfile?.temp, 1), "°C"],
    ["Độ ẩm", fmt(selectedProfile?.humidity, 0), "%"],
    ["Gió", fmt(selectedProfile?.wind_speed, 1), "km/h"],
  ];

  return (
    <section className="screen consumer-screen">
      <header className="overview-head">
        <div>
          <p className="eyebrow">Chất lượng không khí hiện tại</p>
          <div className="location-title">
            <MapPin size={22} />
            <h1>{selectedProfile?.city ?? "Việt Nam"}</h1>
          </div>
          <p className="screen-copy">
            Trạng thái mới nhất tại điểm lưới CAMS đại diện gần trung tâm thành phố.
          </p>
        </div>
        <button
          className="secondary-action"
          type="button"
          onClick={() => {
            setForecastMode("automatic");
            setActiveView("model");
          }}
        >
          <Sparkles size={17} />
          Xem dự báo sau 24 giờ
        </button>
      </header>

      <div className="data-status-bar">
        <span className={`source-state ${isLiveSource(source.status) ? "live" : "warning"}`}>
          <Radio size={14} /> {sourceStatusLabel(source.status)}
        </span>
        <span>Quan sát {fmtDate(selectedProfile?.datetime)}</span>
        <span>{modelName} · v{model?.version ?? "2"}</span>
        <span>Mỗi thành phố là một điểm lưới đại diện</span>
      </div>

      <div className="overview-current-summary">
        <article className="air-condition-card" style={{ "--tone": currentCategory.color }}>
          <div className="air-card-head">
            <span>PM2.5 mới nhất</span>
            <strong>{currentCategory.label}</strong>
          </div>
          <div className="air-reading">
            <b>{fmt(currentValue, 1)}</b>
            <span>µg/m³</span>
          </div>
          <p>{currentCategory.text}</p>
          <div className="current-observation-meta">
            <span>Thời điểm quan sát</span>
            <strong>{fmtDate(selectedProfile?.datetime)}</strong>
          </div>
          <div className="current-range-stats" aria-label="Thống kê PM2.5 trong 24 giờ gần nhất">
            <div><span>Thấp nhất</span><strong>{fmt(recentStats.min, 1)}</strong></div>
            <div><span>Trung bình</span><strong>{fmt(recentStats.mean, 1)}</strong></div>
            <div><span>Cao nhất</span><strong>{fmt(recentStats.max, 1)}</strong></div>
          </div>
          <Pm25Scale value={currentValue} />
        </article>

        <Panel title="PM2.5 trong 24 giờ gần nhất" eyebrow="Chỉ gồm dữ liệu đã quan sát">
          <ForecastBandChart
            rows={selectedHistory.slice(-24)}
            prediction={null}
            metric="pm25"
          />
        </Panel>
      </div>

      <section className="health-guidance" style={{ "--tone": currentCategory.color }}>
        <div className="guidance-icon"><HeartPulse size={24} /></div>
        <div className="guidance-main">
          <span>Khuyến nghị theo PM2.5 hiện tại</span>
          <h2>{advice[0]?.title}</h2>
          <p>{advice[0]?.text}</p>
        </div>
        <div className="guidance-more">
          {advice.slice(1, 3).map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.title}>
                <Icon size={17} />
                <span>{item.title}</span>
              </div>
            );
          })}
        </div>
      </section>

      <div className="overview-detail-grid">
        <Panel title="Chỉ số môi trường" eyebrow="Quan sát cùng thời điểm">
          <div className="environment-grid">
            {environment.map(([label, value, unit]) => (
              <div key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
                <small>{unit}</small>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="So sánh 3 thành phố" eyebrow="PM2.5 mới nhất">
          <div className="city-forecast-list">
            {currentCityRows.map((item, index) => (
              <button
                key={item.city}
                type="button"
                className={item.city === selectedCity ? "active" : ""}
                onClick={() => setSelectedCity(item.city)}
                style={{ "--tone": item.category.color }}
              >
                <span>{index + 1}</span>
                <strong>{item.city}</strong>
                <b>{fmt(item.value, 1)}</b>
                <small>{item.category.label}</small>
              </button>
            ))}
          </div>
        </Panel>

        <Panel title="Trạng thái dữ liệu" eyebrow="Nguồn đầu vào hiện tại">
          <div className="model-trust">
            <strong>{source.provider ?? "Không xác định nguồn"}</strong>
            <p>{sourceStatusLabel(source.status)}. Dữ liệu được cache để tránh gọi API lặp lại khi nhiều người cùng truy cập.</p>
            <div>
              <MetricPill label="Quan sát mới nhất" value={fmtDate(selectedProfile?.datetime)} />
              <MetricPill label="Chu kỳ cache" value="15 phút" />
              <MetricPill label="Phạm vi" value="Điểm lưới đại diện" />
            </div>
            <button className="text-action" type="button" onClick={() => setActiveView("data")}>
              Xem nguồn và chất lượng dữ liệu
            </button>
          </div>
        </Panel>
      </div>
    </section>
  );
}
function Pm25Scale({ value }) {
  const thresholds = [0, 9, 35.4, 55.4, 125.4, 225.4];
  const labels = ["Tốt", "Trung bình", "Nhạy cảm", "Xấu", "Rất xấu"];
  const colors = PM25_SCALE.slice(0, 5).map((item) => item.color);
  const numeric = Math.max(0, Number(value) || 0);
  let segment = thresholds.length - 2;
  for (let index = 0; index < thresholds.length - 1; index += 1) {
    if (numeric <= thresholds[index + 1]) {
      segment = index;
      break;
    }
  }
  const low = thresholds[segment];
  const high = thresholds[segment + 1];
  const within = Math.min(1, Math.max(0, (numeric - low) / Math.max(high - low, 0.01)));
  const marker = Math.min(99, ((segment + within) / labels.length) * 100);

  return (
    <div className="pm25-scale" aria-label={`Thang PM2.5, giá trị hiện tại ${fmt(numeric, 1)} microgam trên mét khối`}>
      <div className="pm25-track">
        {colors.map((color, index) => <span key={labels[index]} style={{ background: color }} />)}
        <i style={{ left: `${marker}%` }} />
      </div>
      <div className="pm25-labels">
        {labels.map((label) => <span key={label}>{label}</span>)}
      </div>
    </div>
  );
}
function buildCityForecastRows(cities, predictions) {
  return [...cities]
    .map((item) => {
      const value = Number(predictions[item.city]?.prediction_pm25 ?? item.profile.pm25 ?? 0);
      return {
        city: item.city,
        value,
        category: normalizedPredictionCategory(predictions[item.city], item.profile.pm25),
      };
    })
    .sort((left, right) => right.value - left.value);
}

function healthAdviceFor(key = "Moderate") {
  const general = [
    {
      icon: HeartPulse,
      title: "Theo dõi triệu chứng",
      text: "Nếu thấy ho, khó thở hoặc cay mắt, giảm thời gian ngoài trời và chuyển sang hoạt động trong nhà.",
    },
    {
      icon: Wind,
      title: "Ưu tiên khung giờ thoáng",
      text: "Khi cần ra ngoài, chọn thời điểm gió tốt hơn và tránh vận động mạnh gần đường đông xe.",
    },
  ];
  if (riskRank(key) >= 3) {
    return [
      {
        icon: ShieldAlert,
        title: "Hạn chế ra ngoài",
        text: "Nhóm nhạy cảm nên tránh hoạt động mạnh ngoài trời; người khỏe mạnh cũng nên giảm thời lượng tiếp xúc.",
      },
      {
        icon: AlertTriangle,
        title: "Dùng khẩu trang lọc bụi",
        text: "Khi bắt buộc di chuyển, nên dùng khẩu trang lọc bụi mịn và đóng cửa khu vực nhiều bụi.",
      },
      ...general,
    ];
  }
  if (riskRank(key) >= 2) {
    return [
      {
        icon: ShieldAlert,
        title: "Nhóm nhạy cảm cần chú ý",
        text: "Trẻ em, người lớn tuổi và người có bệnh hô hấp nên giảm vận động ngoài trời kéo dài.",
      },
      ...general,
    ];
  }
  return [
    {
      icon: HeartPulse,
      title: "Có thể sinh hoạt bình thường",
      text: "Chất lượng không khí đang ở mức chấp nhận được, vẫn nên theo dõi nếu hoạt động ngoài trời lâu.",
    },
    ...general,
  ];
}

function Analytics({ cities, histories, selectedProfile, selectedHistory }) {
  const [metric, setMetric] = useState("pm25");
  const [range, setRange] = useState(168);
  const rows = selectedHistory.slice(-range);
  const currentValue = selectedProfile?.[metric];
  const category = metric === "pm25" ? categoryFromPm25(currentValue) : null;
  const calendar = buildDailyCells(rows, metric);
  const metricValues = rows.map((row) => Number(row[metric])).filter(Number.isFinite);
  const average = metricValues.length
    ? metricValues.reduce((sum, value) => sum + value, 0) / metricValues.length
    : Number(currentValue ?? 0);
  const volatility = calculateVolatility(rows, metric);

  return (
    <section className="screen">
      <div className="screen-head">
        <div>
          <p className="eyebrow">Lịch sử, biến động và đối chiếu khu vực</p>
          <h1>Phân tích</h1>
          <p className="screen-copy">
            Khám phá chuỗi thời gian của thành phố đang chọn và so sánh cùng chỉ số
            tại ba điểm lưới đại diện.
          </p>
        </div>
        <div className="control-row">
          <SelectBox label="Khoảng thời gian" icon={CalendarDays} value={range} onChange={(value) => setRange(Number(value))} options={[24, 72, 168]} suffix="h" />
          <SelectBox label="Chỉ số" icon={SlidersHorizontal} value={metric} onChange={setMetric} options={["pm25", "pm10", "temp", "humidity", "wind_speed"]} />
        </div>
      </div>

      <div className="kpi-grid">
        <KpiCard label="Giá trị hiện tại" value={fmt(currentValue, metric === "humidity" ? 0 : 1)} suffix={metricUnit(metric)} icon={Activity} tone="mint" />
        <KpiCard label="Nhóm sức khỏe" value={category?.label ?? "Chỉ áp dụng PM2.5"} suffix="tham chiếu hiện tại" icon={HeartPulse} tone="yellow" />
        <KpiCard label="Trung bình giai đoạn" value={fmt(average, metric === "humidity" ? 0 : 1)} suffix={metricUnit(metric)} icon={BarChart3} tone="blue" />
        <KpiCard label="Độ biến động" value={fmt(volatility, 1)} suffix={metricUnit(metric)} icon={LineChart} tone="green" />
      </div>

      <Panel title={`${metricLabel(metric)} tại ${selectedProfile?.city ?? "thành phố đã chọn"}`} eyebrow="Chuỗi thời gian đã quan sát">
        <ForecastBandChart
          rows={rows}
          prediction={null}
          metric={metric}
          title=""
          tall
        />
      </Panel>

      <div className="analytics-grid">
        <Panel title="Trung bình theo ngày" eyebrow="Lịch gần đây">
          <div className="heatmap">
            {calendar.map((cell) => (
              <span key={cell.label} style={{ background: heatColor(cell.value, metric) }}>{cell.day}</span>
            ))}
          </div>
        </Panel>
        <Panel title="Hồ sơ chất ô nhiễm" eyebrow="Quan sát cùng thời điểm">
          <PollutantProfile profile={selectedProfile} />
        </Panel>
      </div>

      <div className="analysis-section-head">
        <div>
          <p className="eyebrow">Ba điểm đại diện</p>
          <h2>So sánh thành phố</h2>
        </div>
        <span>96 giờ gần nhất</span>
      </div>

      <Panel title={`Xu hướng ${metricLabel(metric).toLowerCase()} nhiều thành phố`} eyebrow="Cùng thang đo và thời gian">
        <CompareLineChart histories={histories} cities={cities} metric={metric} />
      </Panel>

      <div className="compare-card-grid">
        {cities.map((item) => (
          <CityCompareCard key={item.city} item={item} />
        ))}
      </div>

      <Panel title="Bảng trạng thái hiện tại" eyebrow="Quan sát mới nhất tại ba điểm đại diện">
        <CompareTable cities={cities} />
      </Panel>
    </section>
  );
}
function ActivityPlanner({ city, currentPm25, prediction }) {
  const [group, setGroup] = useState("general");
  const [activity, setActivity] = useState("moderate");
  const [duration, setDuration] = useState(60);
  const [plan, setPlan] = useState(null);
  const [status, setStatus] = useState({ loading: false, error: "" });

  useEffect(() => {
    setPlan(null);
    setStatus({ loading: false, error: "" });
  }, [city, currentPm25, prediction?.prediction_pm25]);

  async function createPlan(event) {
    event.preventDefault();
    if (!prediction?.interval) return;
    setStatus({ loading: true, error: "" });
    try {
      const result = await postJson("/api/activity-plan", {
        city,
        current_pm25: Number(currentPm25),
        forecast_pm25: Number(prediction.prediction_pm25),
        forecast_lower: Number(prediction.interval.lower),
        forecast_upper: Number(prediction.interval.upper),
        group,
        activity,
        duration_minutes: Number(duration),
      });
      setPlan(result);
      setStatus({ loading: false, error: "" });
    } catch (error) {
      console.error(error);
      setStatus({ loading: false, error: "Không lập được kế hoạch từ API." });
    }
  }

  return (
    <section className="planner-tool">
      <div className="planner-heading">
        <div>
          <p className="eyebrow">Tính năng sáng tạo · có xét bất định</p>
          <h2>Lập kế hoạch hoạt động ngoài trời</h2>
          <p>Điều chỉnh hồ sơ và thời lượng để so sánh tải phơi nhiễm tương đối giữa hai thời điểm.</p>
        </div>
        <span className="planner-method"><Brain size={16} /> Model + conformal 90%</span>
      </div>

      <div className="planner-layout">
        <form className="planner-controls" onSubmit={createPlan}>
          <fieldset>
            <legend>Nhóm người dùng</legend>
            <div className="segmented-control">
              <button className={group === "general" ? "active" : ""} type="button" onClick={() => setGroup("general")}>Thông thường</button>
              <button className={group === "sensitive" ? "active" : ""} type="button" onClick={() => setGroup("sensitive")}>Nhạy cảm</button>
            </div>
          </fieldset>

          <label className="planner-field">
            <span>Cường độ hoạt động</span>
            <select value={activity} onChange={(event) => setActivity(event.target.value)}>
              <option value="light">Nhẹ · đi bộ chậm</option>
              <option value="moderate">Vừa · đi bộ nhanh</option>
              <option value="intense">Cao · chạy bộ / đạp xe</option>
            </select>
          </label>

          <label className="planner-range">
            <span><b>Thời lượng</b><strong>{duration} phút</strong></span>
            <input type="range" min="15" max="180" step="15" value={duration} onChange={(event) => setDuration(Number(event.target.value))} />
            <small><span>15 phút</span><span>180 phút</span></small>
          </label>

          <button className="primary-action" type="submit" disabled={status.loading || !prediction}>
            <Sparkles size={18} />
            {status.loading ? "Đang phân tích" : "Lập kế hoạch"}
          </button>
          {status.error && <p className="planner-error">{status.error}</p>}
        </form>

        <div className="planner-output" aria-live="polite">
          {plan ? <ActivityPlanResult plan={plan} /> : (
            <div className="planner-empty">
              <HeartPulse size={30} />
              <strong>Chưa có kế hoạch cá nhân</strong>
              <p>Chọn hồ sơ, cường độ và thời lượng, sau đó chạy bộ phân tích.</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function ActivityPlanResult({ plan }) {
  const now = plan.options.now;
  const future = plan.options.after_24h;
  return (
    <div className="planner-result">
      <div className="planner-result-head">
        <div>
          <span>Kết luận cho {plan.city}</span>
          <h3>{plan.timing_label}</h3>
        </div>
        <span className={`confidence-chip ${plan.confidence}`}>{plan.confidence_label}</span>
      </div>

      <div className="planner-options">
        <div className={plan.timing === "now" ? "preferred" : ""}>
          <span>Đi ngay</span>
          <strong>{fmt(now.pm25, 1)} <small>µg/m³</small></strong>
          <p>{now.category.label_vi}</p>
          <em>Tải tương đối {fmt(now.relative_exposure_load, 1)}</em>
        </div>
        <div className={plan.timing === "after_24h" ? "preferred" : ""}>
          <span>Sau 24 giờ</span>
          <strong>{fmt(future.pm25, 1)} <small>µg/m³</small></strong>
          <p>{future.category.label_vi}</p>
          <em>Tải {fmt(future.relative_exposure_load_lower, 1)} - {fmt(future.relative_exposure_load_upper, 1)}</em>
        </div>
      </div>

      <div className="planner-action">
        <ShieldAlert size={20} />
        <div>
          <strong>{plan.action}</strong>
          {plan.expected_load_reduction_pct !== null && (
            <span>Chênh lệch tải trung tâm ước tính: {fmt(plan.expected_load_reduction_pct, 1)}%</span>
          )}
        </div>
      </div>

      <ul className="planner-reasons">
        {plan.reasons.map((reason) => <li key={reason}>{reason}</li>)}
      </ul>
      <p className="planner-disclaimer">{plan.method.limitations}</p>
    </div>
  );
}

function ForecastStudio({
  model,
  cities,
  predictions,
  selectedCity,
  setSelectedCity,
  selectedItem,
  selectedProfile,
  selectedHistory,
  selectedPrediction,
  forecastMode,
  setForecastMode,
}) {
  const [manualInput, setManualInput] = useState(() => manualValuesFromProfile(selectedProfile));
  const [manualResult, setManualResult] = useState(null);
  const [manualLoading, setManualLoading] = useState(false);
  const [manualError, setManualError] = useState("");

  useEffect(() => {
    setManualInput(manualValuesFromProfile(selectedProfile));
    setManualResult(null);
    setManualError("");
  }, [selectedProfile?.city]);

  const currentValue = Number(selectedProfile?.pm25 ?? 0);
  const automaticValue = Number(selectedPrediction?.prediction_pm25 ?? currentValue);
  const automaticCategory = normalizedPredictionCategory(selectedPrediction, automaticValue);
  const automaticDelta = automaticValue - currentValue;
  const source = selectedItem?.source ?? {};
  const forecastRows = buildCityForecastRows(cities, predictions);
  const manualProfile = manualProfileFromInput(selectedProfile, manualInput);
  const manualValue = Number(manualResult?.prediction_pm25 ?? 0);
  const manualCategory = normalizedPredictionCategory(manualResult, manualProfile.pm25);
  const comparisonDelta = manualResult ? manualValue - automaticValue : 0;

  function applyPreset(preset) {
    const base = manualValuesFromProfile(selectedProfile);
    const scaled = (key, factor) => {
      const value = Number(base[key]);
      return Number.isFinite(value) ? String(Math.max(0, Math.round(value * factor * 100) / 100)) : "";
    };
    if (preset === "pollution") {
      base.pm25 = scaled("pm25", 1.35);
      base.pm10 = scaled("pm10", 1.25);
      base.no2 = scaled("no2", 1.2);
      base.co = scaled("co", 1.1);
      base.wind_speed = scaled("wind_speed", 0.65);
    }
    if (preset === "ventilation") {
      base.pm25 = scaled("pm25", 0.8);
      base.pm10 = scaled("pm10", 0.85);
      base.wind_speed = scaled("wind_speed", 1.6);
    }
    setManualInput(base);
    setManualResult(null);
    setManualError("");
  }

  async function runManualForecast() {
    if (!selectedProfile) return;
    const validationError = validateManualForecastInput(manualInput);
    if (validationError) {
      setManualError(validationError);
      setManualResult(null);
      return;
    }
    setManualLoading(true);
    setManualError("");
    try {
      const result = await postJson("/api/predict", profilePayload(selectedProfile, manualInput));
      setManualResult(result);
    } catch (error) {
      console.error(error);
      setManualError("Không thể chạy dự đoán. Hãy kiểm tra các giá trị đã nhập.");
    } finally {
      setManualLoading(false);
    }
  }

  return (
    <section className="screen forecast-studio">
      <div className="screen-head forecast-studio-head">
        <div>
          <p className="eyebrow">XGBoost · dự báo PM2.5 tại đúng t + 24 giờ</p>
          <h1>Trung tâm dự báo</h1>
          <p className="screen-copy">
            Chọn bản tin tự động từ dữ liệu mới nhất hoặc nhập thông số để tạo một kịch bản riêng.
            Cả hai chế độ dùng cùng model đã được chọn bằng Validation RMSE.
          </p>
        </div>
        <div className="forecast-mode-switch" role="tablist" aria-label="Chọn cách dự báo">
          <button
            type="button"
            role="tab"
            aria-selected={forecastMode === "automatic"}
            className={forecastMode === "automatic" ? "active" : ""}
            onClick={() => setForecastMode("automatic")}
          >
            <Sparkles size={18} />
            <span>Dự báo tự động</span>
            <small>Không cần nhập số</small>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={forecastMode === "manual"}
            className={forecastMode === "manual" ? "active" : ""}
            onClick={() => setForecastMode("manual")}
          >
            <SlidersHorizontal size={18} />
            <span>Nhập thông số</span>
            <small>Tạo kịch bản riêng</small>
          </button>
        </div>
      </div>

      {forecastMode === "automatic" ? (
        <div className="automatic-forecast">
          <div className="forecast-status-line">
            <span className={`source-state ${isLiveSource(source.status) ? "live" : "warning"}`}>
              <Radio size={14} /> {sourceStatusLabel(source.status)}
            </span>
            <span>Quan sát {fmtDate(selectedProfile?.datetime)}</span>
            <span>Đích dự báo {fmtDate(selectedPrediction?.target_time)}</span>
          </div>

          <div className="weather-forecast-grid">
            <section className="weather-forecast-main" style={{ "--tone": automaticCategory.color }}>
              <div className="weather-location">
                <div>
                  <span>Bản tin PM2.5</span>
                  <h2>{selectedCity}</h2>
                </div>
                <Wind size={30} />
              </div>
              <div className="weather-transition">
                <div>
                  <span>Hiện tại</span>
                  <strong>{fmt(currentValue, 1)}</strong>
                  <small>µg/m³</small>
                </div>
                <div className="weather-arrow">
                  <b>24h</b>
                  <i>→</i>
                </div>
                <div>
                  <span>Dự báo</span>
                  <strong>{fmt(automaticValue, 1)}</strong>
                  <small>µg/m³</small>
                </div>
              </div>
              <div className="weather-verdict">
                <strong>{automaticCategory.label}</strong>
                <span className={automaticDelta >= 0 ? "trend-up" : "trend-down"}>
                  {automaticDelta >= 0 ? "+" : ""}{fmt(automaticDelta, 1)} µg/m³ so với hiện tại
                </span>
              </div>
              <p>{automaticCategory.text}</p>
              <div className="weather-interval">
                <span>Khoảng dự báo 90%</span>
                <strong>
                  {fmt(selectedPrediction?.interval?.lower, 1)} – {fmt(selectedPrediction?.interval?.upper, 1)} µg/m³
                </strong>
              </div>
            </section>

            <section className="city-forecast-board">
              <div className="surface-heading">
                <span>Ba thành phố</span>
                <strong>Dự báo cùng thời điểm</strong>
              </div>
              <div>
                {forecastRows.map((item) => {
                  const current = Number(cities.find((city) => city.city === item.city)?.profile.pm25 ?? 0);
                  return (
                    <button
                      key={item.city}
                      type="button"
                      className={item.city === selectedCity ? "active" : ""}
                      onClick={() => setSelectedCity(item.city)}
                      style={{ "--tone": item.category.color }}
                    >
                      <span>{item.city}</span>
                      <small>{fmt(current, 1)} hiện tại</small>
                      <b>{fmt(item.value, 1)}</b>
                      <em>{item.category.label}</em>
                    </button>
                  );
                })}
              </div>
            </section>
          </div>

          <div className="automatic-detail-grid">
            <Panel title="Diễn biến và mốc dự báo" eyebrow="96 giờ gần nhất">
              <ForecastBandChart
                rows={selectedHistory}
                prediction={selectedPrediction}
                metric="pm25"
                forecastLabel="t + 24h"
                tall
              />
            </Panel>
            <Panel title="Độ tin cậy" eyebrow="Model đang triển khai">
              <div className="forecast-confidence">
                <MetricPill label="Model" value={model?.name ?? "XGBoost"} />
                <MetricPill label="Test MAE" value={`${fmt(model?.metrics?.test_mae_ug_m3, 1)} µg/m³`} />
                <MetricPill label="Test R²" value={fmt(model?.metrics?.test_r2, 3)} />
                <MetricPill
                  label="Coverage 90%"
                  value={`${fmt((selectedPrediction?.interval?.empirical_test_coverage ?? 0) * 100, 1)}%`}
                />
              </div>
              <p className="panel-note">
                Đây là dự báo nồng độ PM2.5 theo giờ tại một điểm lưới đại diện, không phải AQI 24 giờ chính thức.
              </p>
            </Panel>
          </div>
          <ActivityPlanner
            city={selectedCity}
            currentPm25={selectedProfile?.pm25}
            prediction={selectedPrediction}
          />
        </div>
      ) : (
        <div className="manual-forecast-layout">
          <section className="manual-form-surface">
            <div className="surface-heading">
              <span>Kịch bản đầu vào</span>
              <strong>{selectedCity}</strong>
              <small>Các feature không hiển thị được giữ từ hồ sơ mới nhất của thành phố.</small>
            </div>

            <div className="manual-presets">
              <button type="button" onClick={() => applyPreset("current")}>
                <RefreshCw size={15} /> Dữ liệu hiện tại
              </button>
              <button type="button" onClick={() => applyPreset("pollution")}>
                <AlertTriangle size={15} /> Ô nhiễm tăng
              </button>
              <button type="button" onClick={() => applyPreset("ventilation")}>
                <Wind size={15} /> Gió thông thoáng
              </button>
            </div>

            <div className="manual-field-groups">
              {MANUAL_FORECAST_GROUPS.map((group) => (
                <fieldset key={group.title}>
                  <legend>{group.title}</legend>
                  <div className="manual-input-grid">
                    {group.fields.map(([key, label, unit, min, max, step]) => (
                      <label key={key} className="manual-input-field">
                        <span>{label}</span>
                        <div>
                          <input
                            type="number"
                            inputMode="decimal"
                            min={min}
                            max={max}
                            step={step}
                            value={manualInput[key] ?? ""}
                            aria-label={label}
                            onChange={(event) => {
                              setManualInput((current) => ({ ...current, [key]: event.target.value }));
                              setManualResult(null);
                            }}
                          />
                          <small>{unit}</small>
                        </div>
                      </label>
                    ))}
                  </div>
                </fieldset>
              ))}
            </div>
            <p className="manual-caveat">
              Kịch bản chỉ phân tích độ nhạy của model. Các feature ẩn vẫn lấy từ hồ sơ thành phố và kết quả không chứng minh quan hệ nhân quả.
            </p>

            {manualError && <p className="manual-error">{manualError}</p>}
            <button
              className="primary-action manual-run-button"
              type="button"
              onClick={runManualForecast}
              disabled={manualLoading}
            >
              <Sparkles size={18} />
              {manualLoading ? "Đang chạy model..." : "Dự đoán PM2.5 sau 24 giờ"}
            </button>
          </section>

          <section className="manual-output-surface" aria-live="polite">
            {!manualResult ? (
              <div className="manual-output-empty">
                <SlidersHorizontal size={34} />
                <h2>Nhập thông số rồi chạy dự đoán</h2>
                <p>
                  Kết quả sẽ hiển thị nồng độ PM2.5 tại t + 24 giờ, khoảng dự báo,
                  mức sức khỏe và chênh lệch với bản tin tự động.
                </p>
              </div>
            ) : (
              <>
                <div className="manual-result-head" style={{ "--tone": manualCategory.color }}>
                  <span>Kết quả kịch bản · {selectedCity}</span>
                  <strong>{fmt(manualValue, 1)}</strong>
                  <small>µg/m³ PM2.5 tại t + 24 giờ</small>
                  <b>{manualCategory.label}</b>
                  <p>{manualCategory.text}</p>
                </div>

                <div className="manual-result-comparison">
                  <div>
                    <span>Dự báo tự động</span>
                    <strong>{fmt(automaticValue, 1)}</strong>
                    <small>µg/m³</small>
                  </div>
                  <div>
                    <span>Kịch bản nhập tay</span>
                    <strong>{fmt(manualValue, 1)}</strong>
                    <small>µg/m³</small>
                  </div>
                  <div className={comparisonDelta >= 0 ? "higher" : "lower"}>
                    <span>Chênh lệch</span>
                    <strong>{comparisonDelta >= 0 ? "+" : ""}{fmt(comparisonDelta, 1)}</strong>
                    <small>µg/m³</small>
                  </div>
                </div>

                <div className="manual-result-interval">
                  <span>Khoảng dự báo 90%</span>
                  <strong>{fmt(manualResult.interval?.lower, 1)} – {fmt(manualResult.interval?.upper, 1)} µg/m³</strong>
                  <small>Đích: {fmtDate(manualResult.target_time)}</small>
                </div>

                <PredictionBriefing
                  profile={manualProfile}
                  prediction={manualResult}
                  model={model}
                  compact
                />
              </>
            )}
          </section>
        </div>
      )}
    </section>
  );
}

function KpiCard({ label, value, suffix, icon: Icon, tone = "mint" }) {
  const longValue = String(value ?? "").length > 18;
  return (
    <article className={`kpi-card ${tone}${longValue ? " long-value" : ""}`}>
      <div>
        <span>{label}</span>
        <div className="kpi-value">
          <strong>{value}</strong>
          {suffix && <small>{suffix}</small>}
        </div>
      </div>
      <Icon size={22} />
    </article>
  );
}

function Panel({ title, eyebrow, children }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          {eyebrow && <p className="eyebrow">{eyebrow}</p>}
          <h2>{title}</h2>
        </div>
      </div>
      {children}
    </section>
  );
}

function SelectBox({ label, icon: Icon, value, onChange, options, suffix = "" }) {
  return (
    <label className="select-box">
      <Icon size={18} />
      <select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
            {suffix}
          </option>
        ))}
      </select>
    </label>
  );
}

function PredictionBriefing({ profile, prediction, model, compact = false }) {
  const metrics = model?.metrics ?? {};
  const forecastValue = Number(prediction?.prediction_pm25 ?? profile?.pm25 ?? 0);
  const currentValue = Number(profile?.pm25 ?? 0);
  const rmse = Number(metrics.test_rmse_ug_m3 ?? 0);
  const lower = Number(prediction?.interval?.lower ?? Math.max(0, forecastValue - rmse));
  const upper = Number(prediction?.interval?.upper ?? forecastValue + rmse);
  const lowerCategory = categoryFromPm25(lower);
  const upperCategory = categoryFromPm25(upper);
  const forecast = normalizedPredictionCategory(prediction, forecastValue);
  const stableBucket = lowerCategory.key === upperCategory.key;
  const scaleMax = Math.max(80, upper + 18, currentValue + 18);
  const pct = (value) => `${Math.min(100, Math.max(0, (Number(value) / scaleMax) * 100))}%`;
  const drivers = [
    ["PM2.5 hiện tại", fmt(profile?.pm25, 1), "mốc gần nhất"],
    ["PM2.5 rolling 24h", fmt(profile?.pm25_roll_24h, 1), "nền ô nhiễm gần nhất"],
    ["PM2.5 lag 24h", fmt(profile?.pm25_lag_24h, 1), "chu kỳ cùng giờ hôm trước"],
    ["Trung vị cùng giờ 7 ngày", fmt(profile?.pm25_same_hour_median_7d, 1), "nền mùa vụ tuần"],
  ];

  return (
    <div className={`prediction-briefing${compact ? " compact" : ""}`}>
      <article className="prediction-band-card">
        <span>Khoảng dự đoán thực nghiệm</span>
        <strong>{fmt(lower, 1)} - {fmt(upper, 1)}</strong>
        <small>µg/m³ PM2.5 · conformal 90% theo thành phố</small>
        <div className="prediction-bar" style={{ "--low": pct(lower), "--high": pct(upper), "--point": pct(forecastValue), "--tone": forecast.color }}>
          <i />
          <b />
        </div>
      </article>

      <article className="prediction-risk-card" style={{ "--tone": upperCategory.color }}>
        <span>Rủi ro theo khoảng dự báo</span>
        <strong>{stableBucket ? forecast.label : `${lowerCategory.label} → ${upperCategory.label}`}</strong>
        <p>
          {stableBucket
            ? "Toàn bộ khoảng nằm trong cùng một dải tham chiếu sức khỏe."
            : "Khoảng dự báo cắt qua nhiều dải sức khỏe, nên đọc kết quả theo hướng thận trọng."}
        </p>
        <small>Độ bao phủ trên Test tại thành phố: {fmt((prediction?.interval?.empirical_test_coverage ?? 0) * 100, 1)}%</small>
      </article>

      <article className="prediction-driver-card">
        <span>Tín hiệu đầu vào đang dùng</span>
        <div className="driver-list">
          {drivers.map(([label, value, note]) => (
            <div key={label}>
              <small>{label}</small>
              <strong>{value}</strong>
              <em>{note}</em>
            </div>
          ))}
        </div>
      </article>
    </div>
  );
}

function ForecastBandChart({ rows = [], prediction, metric = "pm25", title = "", tall = false, forecastLabel = "" }) {
  const width = 900;
  const height = tall ? 360 : 240;
  const pad = { left: 48, right: 34, top: 24, bottom: 34 };
  const data = rows.slice(-96).map((row) => ({ time: row.datetime, value: Number(row[metric]) }));
  const values = data.map((item) => item.value).filter(Number.isFinite);
  if (prediction && metric === "pm25") values.push(Number(prediction.prediction_pm25));
  if (prediction?.interval && metric === "pm25") values.push(Number(prediction.interval.upper));
  const max = Math.max(60, Math.ceil(Math.max(...values, 0) / 10) * 10);
  const min = 0;
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const xFor = (index, count = data.length) => pad.left + (plotW * index) / Math.max(1, count - 1);
  const yFor = (value) => pad.top + plotH - ((value - min) / (max - min)) * plotH;
  const points = data.map((item, index) => `${xFor(index)},${yFor(item.value)}`).join(" ");
  const predValue = Number(prediction?.prediction_pm25);
  const last = data[data.length - 1];
  const forecastX = width - pad.right;
  const forecastY = Number.isFinite(predValue) ? yFor(predValue) : null;
  const lastX = data.length ? xFor(data.length - 1) : pad.left;
  const lastY = last ? yFor(last.value) : null;

  return (
    <div className="chart-box">
      {title && <h3>{title}</h3>}
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={prediction ? "Biểu đồ lịch sử và dự báo" : "Biểu đồ dữ liệu lịch sử"}>
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = pad.top + plotH * ratio;
          const label = max - (max - min) * ratio;
          return (
            <g key={ratio}>
              <line className="grid-line" x1={pad.left} x2={width - pad.right} y1={y} y2={y} />
              <text className="axis-label" x="12" y={y + 4}>
                {label.toFixed(0)}
              </text>
            </g>
          );
        })}
        <rect x={pad.left} y={yFor(Math.min(max, 9))} width={plotW} height={Math.max(0, yFor(0) - yFor(Math.min(max, 9)))} fill="rgba(78,222,163,.08)" />
        <rect x={pad.left} y={yFor(Math.min(max, 35.4))} width={plotW} height={Math.max(0, yFor(9) - yFor(Math.min(max, 35.4)))} fill="rgba(248,214,109,.08)" />
        <rect x={pad.left} y={yFor(Math.min(max, 55.4))} width={plotW} height={Math.max(0, yFor(35.4) - yFor(Math.min(max, 55.4)))} fill="rgba(255,159,67,.07)" />
        <polyline className="history-line" points={points} />
        {forecastY !== null && lastY !== null && (
          <>
            <line className="forecast-line" x1={lastX} y1={lastY} x2={forecastX} y2={forecastY} style={{ stroke: prediction.category.color }} />
            {prediction.interval && (
              <g className="interval-whisker" style={{ stroke: prediction.category.color }}>
                <line x1={forecastX} x2={forecastX} y1={yFor(Number(prediction.interval.upper))} y2={yFor(Number(prediction.interval.lower))} />
                <line x1={forecastX - 9} x2={forecastX + 9} y1={yFor(Number(prediction.interval.upper))} y2={yFor(Number(prediction.interval.upper))} />
                <line x1={forecastX - 9} x2={forecastX + 9} y1={yFor(Number(prediction.interval.lower))} y2={yFor(Number(prediction.interval.lower))} />
              </g>
            )}
            <circle cx={forecastX} cy={forecastY} r="7" fill={prediction.category.color} />
            <text className="forecast-label" x={Math.max(pad.left, forecastX - 96)} y={Math.max(18, forecastY - 12)}>
              {forecastLabel || "Dự báo"}
            </text>
          </>
        )}
        <text className="axis-label" x={pad.left} y={height - 12}>
          {metricLabel(metric)} · {data.length} mẫu gần nhất
        </text>
      </svg>
    </div>
  );
}

function CompareLineChart({ histories, cities, metric }) {
  const width = 1100;
  const height = 380;
  const pad = { left: 52, right: 26, top: 26, bottom: 38 };
  const series = cities.map((item) => ({
    city: item.city,
    rows: (histories[item.city] ?? []).slice(-96).map((row) => Number(row[metric])),
    color: normalizedPredictionCategory(null, item.profile.pm25).color,
  }));
  const allValues = series.flatMap((item) => item.rows).filter(Number.isFinite);
  const max = Math.max(60, Math.ceil(Math.max(...allValues, 0) / 10) * 10);
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const xFor = (index, count) => pad.left + (plotW * index) / Math.max(1, count - 1);
  const yFor = (value) => pad.top + plotH - (value / max) * plotH;

  return (
    <div className="chart-box">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Biểu đồ so sánh nhiều đô thị">
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = pad.top + plotH * ratio;
          return <line key={ratio} className="grid-line" x1={pad.left} x2={width - pad.right} y1={y} y2={y} />;
        })}
        {series.map((item) => {
          const points = item.rows.map((value, index) => `${xFor(index, item.rows.length)},${yFor(value)}`).join(" ");
          return <polyline key={item.city} className="compare-line" points={points} style={{ stroke: item.color }} />;
        })}
      </svg>
      <div className="chart-legend">
        {series.map((item) => (
          <span key={item.city}>
            <i style={{ background: item.color }} />
            {item.city}
          </span>
        ))}
      </div>
    </div>
  );
}

function CityCompareCard({ item }) {
  const profile = item.profile;
  const category = categoryFromPm25(profile.pm25);
  return (
    <article className="city-card">
      <div className="city-card-head">
        <div>
          <h2>{item.city}</h2>
          <span>{CITY_REGIONS[item.city]}</span>
        </div>
        <span className="badge" style={{ color: category.color, background: `${category.color}20` }}>
          {category.label}
        </span>
      </div>
      <AqiMiniGauge value={profile.pm25} color={category.color} />
      <div className="metric-strip">
        <MetricPill label="PM2.5" value={fmt(profile.pm25, 1)} />
        <MetricPill label="PM10" value={fmt(profile.pm10, 1)} />
        <MetricPill label="Nhiệt độ" value={`${fmt(profile.temp, 1)}°C`} />
        <MetricPill label="Gió" value={`${fmt(profile.wind_speed, 1)} km/h`} />
      </div>
    </article>
  );
}

function AqiMiniGauge({ value, color }) {
  return (
    <div className="mini-gauge" style={{ "--tone": color }}>
      <span />
      <strong>{fmt(value, 0)}</strong>
      <small>PM2.5</small>
    </div>
  );
}

function CompareTable({ cities }) {
  const rows = [
    ["PM2.5", (item) => item.profile.pm25, "pm25"],
    ["PM10", (item) => item.profile.pm10, "pollutant"],
    ["O₃", (item) => item.profile.o3, "pollutant"],
    ["Độ ẩm", (item) => item.profile.humidity, "humidity"],
    ["Nhiệt độ", (item) => item.profile.temp, "temp"],
    ["Gió", (item) => item.profile.wind_speed, "wind"],
  ];
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            {cities.map((item) => (
              <th key={item.city}>{item.city}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, getter, kind]) => (
            <tr key={label}>
              <td>{label}</td>
              {cities.map((item) => {
                const value = Number(getter(item));
                return (
                  <td key={item.city} style={{ background: heatColor(value, kind), color: "#08100d" }}>
                    {fmt(value, kind === "temp" ? 1 : 1)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MetricPill({ label, value }) {
  return (
    <span className="metric-pill">
      <small>{label}</small>
      <strong>{value}</strong>
    </span>
  );
}

function PollutantProfile({ profile }) {
  const max = Math.max(...POLLUTANTS.map(([key]) => Number(profile?.[key] || 0)), 1);
  return (
    <div className="pollutant-bars">
      {POLLUTANTS.map(([key, label, unit]) => {
        const value = Number(profile?.[key] || 0);
        const color = key === "pm25" ? categoryFromPm25(value).color : "#86a6ff";
        return (
          <div key={key}>
            <div>
              <span>{label}</span>
              <strong>
                {fmt(value, key === "co" ? 0 : 1)} {unit}
              </strong>
            </div>
            <i style={{ "--width": `${Math.max(5, (value / max) * 100)}%`, "--color": color }} />
          </div>
        );
      })}
    </div>
  );
}

function LoadingScreen() {
  return (
    <div className="loading-screen">
      <div className="loader" />
      <strong>Đang tải hệ thống dự báo PM2.5</strong>
      <span>Kết nối API, model và lịch sử PM2.5</span>
    </div>
  );
}

function ErrorScreen({ message, onRetry }) {
  return (
    <div className="loading-screen">
      <AlertTriangle size={32} />
      <strong>{message}</strong>
      <button className="primary-action" type="button" onClick={onRetry}>
        Thử lại
      </button>
    </div>
  );
}

function buildDailyCells(rows, metric) {
  const groups = new Map();
  rows.forEach((row) => {
    const date = new Date(row.datetime);
    const key = Number.isNaN(date.getTime()) ? row.datetime.slice(0, 10) : date.toISOString().slice(0, 10);
    const values = groups.get(key) ?? [];
    values.push(Number(row[metric] || 0));
    groups.set(key, values);
  });
  return Array.from(groups.entries()).slice(-35).map(([label, values]) => {
    const date = new Date(label);
    return {
      label,
      day: Number.isNaN(date.getTime()) ? label.slice(-2) : date.getDate(),
      value: values.reduce((sum, item) => sum + item, 0) / Math.max(1, values.length),
    };
  });
}

function calculateVolatility(rows, metric = "pm25") {
  const values = rows.map((row) => Number(row[metric])).filter(Number.isFinite);
  if (!values.length) return 0;
  const avg = values.reduce((sum, item) => sum + item, 0) / values.length;
  const variance = values.reduce((sum, item) => sum + (item - avg) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

function metricLabel(metric) {
  return {
    pm25: "PM2.5",
    pm10: "PM10",
    temp: "Nhiệt độ",
    humidity: "Độ ẩm",
    wind_speed: "Tốc độ gió",
  }[metric] ?? metric;
}

function metricUnit(metric) {
  return {
    pm25: "µg/m³",
    pm10: "µg/m³",
    temp: "°C",
    humidity: "%",
    wind_speed: "km/h",
  }[metric] ?? "";
}

function featureLabel(feature) {
  return {
    pm25: "PM2.5 hiện tại",
    pm25_lag_1h: "PM2.5 trễ 1 giờ",
    pm25_lag_3h: "PM2.5 trễ 3 giờ",
    pm25_lag_24h: "PM2.5 trễ 24 giờ",
    pm25_lag_48h: "PM2.5 trễ 48 giờ",
    pm25_lag_72h: "PM2.5 trễ 72 giờ",
    pm25_lag_168h: "PM2.5 cùng giờ tuần trước",
    pm25_delta_1h: "Biến động PM2.5 trong 1 giờ",
    pm25_delta_3h: "Biến động PM2.5 trong 3 giờ",
    pm25_roll_ratio_6h_24h: "Tỷ lệ nền PM2.5 6h / 24h",
    pm25_same_hour_mean_7d: "Trung bình cùng giờ 7 ngày",
    pm25_same_hour_median_7d: "Trung vị cùng giờ 7 ngày",
    factories_2km: "Nhà máy trong 2 km",
    factories_5km: "Nhà máy trong 5 km",
    factories_10km: "Nhà máy trong 10 km",
    factory_density_5km: "Mật độ nhà máy trong 5 km",
    pm25_same_hour_max_7d: "PM2.5 cao nhất cùng giờ trong 7 ngày",
    pm25_std_12h: "Độ biến động PM2.5 trong 12 giờ",
    pm25_std_168h: "Độ biến động PM2.5 trong 7 ngày",
    pm25_max_24h: "PM2.5 cao nhất trong 24 giờ",
    pm25_pm10_ratio: "Tỷ lệ PM2.5 / PM10",
    pm25_roll_24h: "PM2.5 trung bình 24 giờ",
    pm25_lag_12h: "PM2.5 trễ 12 giờ",
    pm25_delta_24h: "Biến động PM2.5 trong 24 giờ",
    wind_x: "Thành phần gió Đông - Tây",
    wind_y: "Thành phần gió Bắc - Nam",
    hour_cos: "Chu kỳ giờ trong ngày",
    day_sin: "Chu kỳ ngày trong năm (sin)",
    day_cos: "Chu kỳ ngày trong năm (cos)",
    "city_Hà Nội": "Thành phố: Hà Nội",
    "city_TP.HCM": "Thành phố: TP.HCM",
    "city_Đà Nẵng": "Thành phố: Đà Nẵng",
    temp: "Nhiệt độ",
    pm25_roll_6h: "PM2.5 trung bình 6h",
    pm25_roll_72h: "PM2.5 trung bình 72h",
    pressure: "Áp suất",
    co: "CO",
    hour: "Giờ trong ngày",
    "season_Đông": "Mùa đông",
    "season_Xuân": "Mùa xuân",
    is_weekend: "Cuối tuần",
    cloud_cover: "Mây che phủ",
    day_of_year: "Ngày trong năm",
    pm10: "PM10",
    day_of_week: "Thứ trong tuần",
    so2: "SO2",
  }[feature] ?? feature;
}

function heatColor(value, metric) {
  if (metric === "temp") {
    if (value >= 34) return "#fc7c78";
    if (value >= 30) return "#f8d66d";
    return "#4edea3";
  }
  if (metric === "humidity") {
    if (value >= 90) return "#86a6ff";
    if (value >= 75) return "#f8d66d";
    return "#4edea3";
  }
  if (metric === "wind" || metric === "wind_speed") {
    if (value <= 2) return "#fc7c78";
    if (value <= 6) return "#f8d66d";
    return "#4edea3";
  }
  if (value >= 55.4) return "#fc7c78";
  if (value >= 35.4) return "#ff9f43";
  if (value >= 9) return "#f8d66d";
  return "#4edea3";
}

function isLiveSource(status = "") {
  return ["live", "cache_fresh"].includes(status);
}

function sourceStatusLabel(status = "") {
  return {
    live: "Dữ liệu trực tiếp",
    cache_fresh: "Cache mới dưới 15 phút",
    cache_stale: "Cache cũ do nguồn lỗi",
    historical_fallback: "Đang dùng snapshot lịch sử",
  }[status] ?? "Không rõ trạng thái nguồn";
}

function shortHash(value = "") {
  if (!value) return "N/A";
  return value.length > 20 ? `${value.slice(0, 16)}…${value.slice(-8)}` : value;
}

function errorLabel(value = "") {
  return {
    missed_pollution_peak: "Model bỏ lỡ một đỉnh ô nhiễm đột ngột.",
    overpredicted_pollution: "Model dự báo cao hơn mức thực tế.",
    transition_or_unobserved_driver: "Giai đoạn chuyển tiếp hoặc có tác nhân chưa được quan sát.",
  }[value] ?? value;
}

function riskBucketLabel(value = "") {
  return {
    Good: "Tốt",
    Moderate: "Trung bình",
    USG: "Nhạy cảm",
    Unhealthy: "Xấu",
    "Very Unhealthy": "Rất xấu",
    Hazardous: "Nguy hại",
  }[value] ?? value;
}
