// Thin fetch wrapper. Errors carry the API's stable code for copy lookup.
export class ApiError extends Error {
  constructor(code, status) { super(code); this.code = code; this.status = status; }
}

async function call(method, path, body) {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.error || (res.status === 422 ? "invalid" : "generic"), res.status);
  return data;
}

export const api = {
  today: () => call("GET", "/today"),
  options: (easier) => call("GET", `/options?easier=${easier ? "true" : "false"}`),
  pick: (body) => call("POST", "/plans", body),
  unpick: (id) => call("DELETE", `/plans/${id}`),
  logOutcome: (id, body) => call("POST", `/logs/${id}/outcome`, body),
  freeze: (date) => call("POST", "/freezes", date ? { date } : {}),
  progress: (weeks = 8) => call("GET", `/progress?weeks=${weeks}`),
  history: (limit = 20) => call("GET", `/history?limit=${limit}`),
  titles: () => call("GET", "/titles"),
  setTier: (tier) => call("PUT", "/me/tier", { tier }),
};
