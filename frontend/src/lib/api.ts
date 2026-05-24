const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type SP500TickerSnapshot = {
  ticker: string;
  company_name: string;
  sector: string;
  filing_date: string;
  surprise: number;
  latest_reaction?: number | null;
};

export type SP500SurprisesResponse = {
  count: number;
  items: SP500TickerSnapshot[];
};

export type ProportionalityValues = {
  pct_diff_from_expected: number;
  expected_CAR: number;
  actual_CAR: number;
};

export type ProportionalityResponseEntry = ProportionalityValues & {
  regression_model: RegressionModelValues;
};

export type RegressionModelValues = {
  surprise_mean: number;
  surprise_sd: number;
  alpha: number;
  beta: number;
};

export type SP500TickerDetailResponse = {
  ticker: string;
  company_name: string;
  sector: string;
  filing_date: string;
  surprise: number;
  latest_reaction: number | null;
  reaction_by_date: Record<string, number>;
  reaction_error: string | null;
  proportionality: ProportionalityValues | null;
  regression_model: RegressionModelValues | null;
};

export type ReactionEndpointResponse = {
  ticker: string;
  reaction_data: Record<
    string,
    {
      reaction: Record<string, number> | string;
      surprise: number;
    }
  >;
};

export type ProportionalityEndpointResponse = Record<string, ProportionalityResponseEntry>;

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const details = await response.text();
    throw new Error(`Request failed (${response.status}): ${details}`);
  }

  return (await response.json()) as T;
}

async function fetchSP500SurprisesNetwork(): Promise<SP500TickerSnapshot[]> {
  const payload = await request<SP500SurprisesResponse>("/sp500/surprises");
  return payload.items;
}

export async function fetchSP500SurprisesFresh(): Promise<SP500TickerSnapshot[]> {
  return fetchSP500SurprisesNetwork();
}

export async function getSP500Surprises(): Promise<SP500TickerSnapshot[]> {
  return fetchSP500SurprisesNetwork();
}

export async function getTickerDetails(
  symbol: string,
  includeProportionality = false,
): Promise<SP500TickerDetailResponse> {
  const query = includeProportionality ? "?include_proportionality=true" : "";
  return request<SP500TickerDetailResponse>(
    `/sp500/${encodeURIComponent(symbol)}/details${query}`,
  );
}

export async function getTickerReaction(
  symbol: string,
  filingsDate: string,
): Promise<ReactionEndpointResponse> {
  const query = new URLSearchParams({
    filings_date: filingsDate,
    reaction_days_threshold: "3",
    surprise_threshold: "0",
  });

  return request<ReactionEndpointResponse>(
    `/${encodeURIComponent(symbol)}/reaction?${query.toString()}`,
  );
}

export async function getTickerProportionality(
  symbol: string,
  filingsDate: string,
): Promise<ProportionalityEndpointResponse> {
  const query = new URLSearchParams({ filings_date: filingsDate });
  return request<ProportionalityEndpointResponse>(
    `/${encodeURIComponent(symbol)}/proportionate?${query.toString()}`,
  );
}
