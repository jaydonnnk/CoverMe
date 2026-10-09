export const usd = (cents: number) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);
export const usdc = (units: number) => `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 4 }).format(units / 1e6)} USDC`;
export const short = (value: string) => value.length > 22 ? `${value.slice(0, 10)}…${value.slice(-6)}` : value;
export const failureLabel = (rule: string) => ({ over_request_max: "Amount exceeds signed maximum", over_per_item: "Amount exceeds per-item limit", over_monthly: "Amount exceeds monthly limit", shop_not_allowed: "Shop is not allowed", wrong_address: "Address does not match saved destination" }[rule] || rule.replaceAll("_", " "));
