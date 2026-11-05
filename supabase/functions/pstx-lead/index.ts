// Package Store TX lead intake. Public endpoint (no JWT): the site's forms POST here.
// Writes to public.pstx_leads with the service role. The table has RLS on and no policies,
// so nothing is readable or writable with the public key.
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.45.4";

const ALLOWED = ["https://packagestoretx.com", "https://www.packagestoretx.com"];
const TYPES = ["valuation", "audit", "buyer", "contact"];
// Zapier catch hook for the pstx-lead-alert workflow (email justin@ and jeff@packagestoretx.com + Slack DM).
// The deployed function carries the real URL; the public repo copy reads it from the environment.
const ALERT_HOOK = Deno.env.get("PSTX_ALERT_HOOK") || "__ALERT_HOOK__";

function labelize(k: string) {
  return k.replace(/^(contact|buy|audit|value|gate|calc|quick)-form-|^(contact|buy|audit|gate|calc|q)-/, "").replace(/[-_]/g, " ")
    .replace(/^./, (c) => c.toUpperCase());
}

function cors(origin: string | null) {
  const o = origin && ALLOWED.includes(origin) ? origin : ALLOWED[0];
  return {
    "Access-Control-Allow-Origin": o,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "content-type",
    "Vary": "Origin",
  };
}

function pick(obj: Record<string, unknown>, suffix: string): string {
  for (const [k, v] of Object.entries(obj)) {
    if ((k === suffix || k.endsWith("-" + suffix)) && typeof v === "string") return v.trim();
  }
  return "";
}

async function sha(s: string) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return Array.from(new Uint8Array(d)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

Deno.serve(async (req) => {
  const h = cors(req.headers.get("origin"));
  if (req.method === "OPTIONS") return new Response(null, { headers: h });
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405, headers: h });

  let body: Record<string, unknown>;
  try {
    const raw = await req.text();
    if (raw.length > 8000) return new Response("Too large", { status: 413, headers: h });
    body = JSON.parse(raw);
  } catch {
    return new Response("Bad JSON", { status: 400, headers: h });
  }

  const type = String(body.type || "");
  const name = pick(body, "name");
  const phone = pick(body, "phone");
  const email = pick(body, "email");
  if (!TYPES.includes(type) || !name || name.length > 200 || phone.replace(/\D/g, "").length < 10 || phone.length > 40) {
    return new Response(JSON.stringify({ ok: false, error: "invalid" }), { status: 422, headers: { ...h, "content-type": "application/json" } });
  }
  if (email && (email.length > 254 || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email))) {
    return new Response(JSON.stringify({ ok: false, error: "email" }), { status: 422, headers: { ...h, "content-type": "application/json" } });
  }

  const details: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(body)) {
    if (["type"].includes(k) || /(^|-)(name|phone|email)$/.test(k)) continue;
    if (typeof v === "string" || typeof v === "number") details[k] = typeof v === "string" ? v.slice(0, 2000) : v;
  }

  const ip = req.headers.get("x-forwarded-for")?.split(",")[0].trim() || "";
  const ip_hash = ip ? await sha(ip + "pstx") : null;
  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

  if (ip_hash) {
    const since = new Date(Date.now() - 10 * 60 * 1000).toISOString();
    const { count } = await db.from("pstx_leads").select("id", { count: "exact", head: true }).eq("ip_hash", ip_hash).gte("created_at", since);
    if ((count ?? 0) >= 5) return new Response(JSON.stringify({ ok: false, error: "rate" }), { status: 429, headers: { ...h, "content-type": "application/json" } });
  }

  const { data: row, error } = await db.from("pstx_leads").insert({
    lead_type: type, name, phone, email: email || null, details, ip_hash,
    user_agent: (req.headers.get("user-agent") || "").slice(0, 300),
  }).select("id, created_at").single();
  if (error) return new Response(JSON.stringify({ ok: false }), { status: 500, headers: { ...h, "content-type": "application/json" } });

  // Alert Justin and Jeffrey. A failed alert never fails the visitor's submission; alerted_at stays null so it can be retried.
  if (ALERT_HOOK.startsWith("https://")) {
    try {
      const details_text = Object.entries(details).filter(([, v]) => String(v).trim() !== "")
        .map(([k, v]) => `${labelize(k)}: ${v}`).join("\n");
      const r = await fetch(ALERT_HOOK, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ id: row.id, created_at: row.created_at, lead_type: type, name, phone, email, details_text }),
      });
      if (r.ok) await db.from("pstx_leads").update({ alerted_at: new Date().toISOString() }).eq("id", row.id);
    } catch (_) { /* alert retry is handled by the freshness watchdog */ }
  }
  return new Response(JSON.stringify({ ok: true }), { headers: { ...h, "content-type": "application/json" } });
});
