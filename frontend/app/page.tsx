"use client";

import { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const API_BASE = "http://localhost:8000";

interface HistoryData {
  Date: string;
  Open?: number;
  High?: number;
  Low?: number;
  Close?: number;
  Volume?: number;
}

interface SurpriseData {
  ticker: string;
  surprise: Record<string, number>;
}

interface ReactionData {
  ticker: string;
  reaction_data: Record<
    string,
    {
      reaction: Record<string, number> | number | string;
      surprise: number;
    }
  >;
}

interface ProportionateData {
  pct_diff_from_expected: number | null;
  expected_CAR: number;
  actual_CAR: number;
}

interface PEData {
  ticker: string;
  pe: number | null;
  forward_pe: number | null;
}

interface EarningsData {
  ticker: string;
  last_earnings_date: string;
}

export default function Dashboard() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string>("");
  const [searchInput, setSearchInput] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  // Data states
  const [historyData, setHistoryData] = useState<HistoryData[]>([]);
  const [surpriseData, setSurpriseData] = useState<SurpriseData | null>(null);
  const [reactionData, setReactionData] = useState<ReactionData | null>(null);
  const [proportionateData, setProportionateData] =
    useState<ProportionateData | null>(null);
  const [peData, setPEData] = useState<PEData | null>(null);
  const [earningsData, setEarningsData] = useState<EarningsData | null>(null);

  // Fetch supported tickers on mount
  useEffect(() => {
    const fetchTickers = async () => {
      try {
        const res = await fetch(`${API_BASE}/supported_tickers`);
        const data = await res.json();
        setTickers(data.tickers || []);
      } catch (err) {
        console.error("Failed to fetch tickers:", err);
      }
    };
    fetchTickers();
  }, []);

  // Fetch all data for selected ticker
  useEffect(() => {
    if (!selectedTicker) {
      setHistoryData([]);
      setSurpriseData(null);
      setReactionData(null);
      setProportionateData(null);
      setPEData(null);
      setEarningsData(null);
      return;
    }

    const fetchAllData = async () => {
      setLoading(true);
      setError("");
      try {
        const [history, surprise, reaction, pe, earnings] = await Promise.all([
          fetch(`${API_BASE}/${selectedTicker}/history?start=2024-01-01&end=2026-05-01`).then(
            (r) => r.json()
          ),
          fetch(`${API_BASE}/${selectedTicker}/surprise`).then((r) => r.json()),
          fetch(
            `${API_BASE}/${selectedTicker}/reaction?num_day_return=3&market_index=SPY`
          ).then((r) => r.json()),
          fetch(`${API_BASE}/${selectedTicker}/pe`).then((r) => r.json()),
          fetch(`${API_BASE}/${selectedTicker}/earnings_last`).then((r) => r.json()),
        ]);

        setHistoryData(history.data || []);
        setSurpriseData(surprise);
        setReactionData(reaction);
        setPEData(pe);
        setEarningsData(earnings);

        // Fetch proportionate data with first available filing date
        if (surprise?.surprise && Object.keys(surprise.surprise).length > 0) {
          const filingDate = Object.keys(surprise.surprise)[0];
          try {
            const prop = await fetch(
              `${API_BASE}/${selectedTicker}/proportionate?filings_date=${filingDate}`
            ).then((r) => r.json());
            setProportionateData(prop);
          } catch (err) {
            console.warn("Failed to fetch proportionate data:", err);
          }
        }
      } catch (err) {
        setError(`Failed to fetch data: ${err}`);
      } finally {
        setLoading(false);
      }
    };

    fetchAllData();
  }, [selectedTicker]);

  // Filter tickers based on search
  const filteredTickers = tickers.filter((t) =>
    t.toLowerCase().includes(searchInput.toLowerCase())
  );

  const formatPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined) return "N/A";
    return `${(value * 100).toFixed(2)}%`;
  };

  const formatNumber = (value: number | null | undefined, decimals = 2) => {
    if (value === null || value === undefined) return "N/A";
    return value.toFixed(decimals);
  };

  const getSurpriseColor = (value: number | null | undefined) => {
    if (value === null || value === undefined) return "neutral";
    return value > 0 ? "positive" : value < 0 ? "negative" : "neutral";
  };

  return (
    <main>
      <div className="dashboard">
        {/* Header */}
        <div className="dashboard-header">
          <h1>📊 Market Reaction Dashboard</h1>
          <p style={{ marginTop: 0, color: "var(--muted)" }}>
            Analyze earnings surprises and market reactions
          </p>
        </div>

        {/* Search Section */}
        <div className="search-section">
          <input
            type="text"
            className="search-input"
            placeholder="Search tickers..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <button
            className="button primary"
            onClick={() => {
              if (filteredTickers.length > 0) {
                setSelectedTicker(filteredTickers[0]);
              }
            }}
          >
            Search
          </button>
        </div>

        {/* Ticker List */}
        <div className="ticker-list">
          {filteredTickers.slice(0, 12).map((ticker) => (
            <button
              key={ticker}
              className={`ticker-button ${
                selectedTicker === ticker ? "active" : ""
              }`}
              onClick={() => setSelectedTicker(ticker)}
            >
              {ticker}
            </button>
          ))}
        </div>

        {error && <div className="error">{error}</div>}

        {selectedTicker && (
          <>
            {loading ? (
              <div className="loading">Loading data for {selectedTicker}...</div>
            ) : (
              <>
                {/* Historical Price Chart */}
                {historyData.length > 0 && (
                  <div className="card">
                    <h2>Historical Prices</h2>
                    <div className="chart-container">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={historyData}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis
                            dataKey="Date"
                            tick={{ fontSize: 12 }}
                            interval={Math.floor(historyData.length / 6)}
                          />
                          <YAxis tick={{ fontSize: 12 }} />
                          <Tooltip
                            formatter={(value: number) => value.toFixed(2)}
                          />
                          <Legend />
                          <Line
                            type="monotone"
                            dataKey="Close"
                            stroke="var(--primary)"
                            dot={false}
                            isAnimationActive={false}
                          />
                          <Line
                            type="monotone"
                            dataKey="Open"
                            stroke="var(--muted)"
                            dot={false}
                            isAnimationActive={false}
                            opacity={0.5}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                <div className="grid">
                  {/* Surprise Metrics */}
                  {surpriseData && (
                    <div className="card">
                      <h2>Earnings Surprise</h2>
                      <div className="stats-grid">
                        {Object.entries(surpriseData.surprise).map(
                          ([date, value]) => (
                            <div key={date} className="stat-box">
                              <div className="stat-label">{date}</div>
                              <div
                                className={`metric-value ${getSurpriseColor(value)}`}
                              >
                                {formatPercent(value)}
                              </div>
                            </div>
                          )
                        )}
                      </div>
                      {Object.values(surpriseData.surprise).length === 0 && (
                        <p style={{ color: "var(--muted)" }}>
                          No surprise data available
                        </p>
                      )}
                    </div>
                  )}

                  {/* P/E Ratios */}
                  {peData && (
                    <div className="card">
                      <h2>Valuation Metrics</h2>
                      <div className="metric">
                        <span className="metric-label">
                          Trailing P/E Ratio
                        </span>
                        <span className="metric-value">
                          {formatNumber(peData.pe)}
                        </span>
                      </div>
                      <div className="metric">
                        <span className="metric-label">Forward P/E Ratio</span>
                        <span className="metric-value">
                          {formatNumber(peData.forward_pe)}
                        </span>
                      </div>
                      {earningsData && (
                        <div className="metric">
                          <span className="metric-label">
                            Last Earnings Date
                          </span>
                          <span className="metric-value">
                            {earningsData.last_earnings_date}
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Reaction Data */}
                {reactionData && (
                  <div className="card">
                    <h2>Market Reaction (CAR)</h2>
                    {Object.entries(reactionData.reaction_data).map(
                      ([filingDate, data]) => {
                        const reaction = data.reaction;
                        const reactionArray = Array.isArray(reaction)
                          ? reaction
                          : typeof reaction === "object"
                            ? Object.entries(reaction).map(([date, value]) => ({
                                date,
                                car: value,
                              }))
                            : [];

                        return (
                          <div key={filingDate}>
                            <p>
                              <strong>Filing Date:</strong> {filingDate}
                            </p>
                            {reactionArray.length > 0 && (
                              <div className="chart-container">
                                <ResponsiveContainer width="100%" height="100%">
                                  <BarChart
                                    data={reactionArray}
                                    margin={{ left: -20 }}
                                  >
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis
                                      dataKey="date"
                                      tick={{ fontSize: 12 }}
                                    />
                                    <YAxis tick={{ fontSize: 12 }} />
                                    <Tooltip formatter={(value: number) =>
                                      value.toFixed(4)
                                    } />
                                    <Bar
                                      dataKey="car"
                                      fill="var(--primary)"
                                      radius={[4, 4, 0, 0]}
                                    />
                                  </BarChart>
                                </ResponsiveContainer>
                              </div>
                            )}
                          </div>
                        );
                      }
                    )}
                  </div>
                )}

                {/* Proportionate Analysis */}
                {proportionateData && (
                  <div className="card">
                    <h2>Model vs. Reality</h2>
                    <p style={{ marginBottom: 20, color: "var(--muted)" }}>
                      Expected vs. Actual Cumulative Abnormal Return (CAR)
                    </p>
                    <div className="proportionate-comparison">
                      <div className="comparison-box">
                        <div className="comparison-label">Expected CAR</div>
                        <div
                          className="comparison-value"
                          style={{
                            color:
                              proportionateData.expected_CAR > 0
                                ? "var(--success)"
                                : proportionateData.expected_CAR < 0
                                  ? "var(--error)"
                                  : "var(--text)",
                          }}
                        >
                          {formatPercent(proportionateData.expected_CAR)}
                        </div>
                      </div>
                      <div className="comparison-box">
                        <div className="comparison-label">Actual CAR</div>
                        <div
                          className="comparison-value"
                          style={{
                            color:
                              proportionateData.actual_CAR > 0
                                ? "var(--success)"
                                : proportionateData.actual_CAR < 0
                                  ? "var(--error)"
                                  : "var(--text)",
                          }}
                        >
                          {formatPercent(proportionateData.actual_CAR)}
                        </div>
                      </div>
                      <div className="comparison-box">
                        <div className="comparison-label">Difference</div>
                        {proportionateData.pct_diff_from_expected !== null ? (
                          <>
                            <div
                              className="comparison-value"
                              style={{
                                color:
                                  proportionateData.pct_diff_from_expected > 0
                                    ? "var(--success)"
                                    : proportionateData.pct_diff_from_expected <
                                        0
                                      ? "var(--error)"
                                      : "var(--text)",
                              }}
                            >
                              {formatPercent(
                                proportionateData.pct_diff_from_expected
                              )}
                            </div>
                            <div
                              className={`comparison-diff ${proportionateData.pct_diff_from_expected > 0 ? "positive" : proportionateData.pct_diff_from_expected < 0 ? "negative" : "neutral"}`}
                            >
                              {proportionateData.pct_diff_from_expected > 0
                                ? "Outperformed"
                                : proportionateData.pct_diff_from_expected < 0
                                  ? "Underperformed"
                                  : "In line"}
                            </div>
                          </>
                        ) : (
                          <div className="comparison-value">N/A</div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </>
        )}

        {!selectedTicker && (
          <div style={{ textAlign: "center", marginTop: 60 }}>
            <p style={{ fontSize: "1.1rem", color: "var(--muted)" }}>
              Select a ticker to get started
            </p>
          </div>
        )}
      </div>
    </main>
  );
}