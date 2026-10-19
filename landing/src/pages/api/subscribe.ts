export const prerender = false;

import crypto from "node:crypto";

const DEFAULT_NOTICIAS_DB_ID = "1dF09CdfpLe6F7-8TI6hCYyacUzilMTsvIuaMCdZxltQ";

interface ServiceAccountCredentials {
  client_email: string;
  private_key: string;
  token_uri?: string;
}

function base64UrlEncode(input: string | Buffer): string {
  const buf = typeof input === "string" ? Buffer.from(input, "utf-8") : input;
  return buf
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function parseServiceAccount(rawGcpJson: string): ServiceAccountCredentials {
  let trimmed = rawGcpJson.trim();
  if (!trimmed.startsWith("{")) {
    trimmed = Buffer.from(trimmed, "base64").toString("utf-8");
  }
  const parsed = JSON.parse(trimmed);
  if (!parsed.client_email || !parsed.private_key) {
    throw new Error("GCP_JSON inválido: client_email ou private_key ausente.");
  }
  parsed.private_key = String(parsed.private_key).replace(/\\n/g, "\n");
  return parsed;
}

async function getGoogleAccessToken(creds: ServiceAccountCredentials): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  const tokenUri = creds.token_uri || "https://oauth2.googleapis.com/token";

  const header = base64UrlEncode(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const payload = base64UrlEncode(
    JSON.stringify({
      iss: creds.client_email,
      scope: "https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive",
      aud: tokenUri,
      iat: now,
      exp: now + 3600,
    })
  );

  const unsignedJwt = `${header}.${payload}`;
  const signer = crypto.createSign("RSA-SHA256");
  signer.update(unsignedJwt);
  signer.end();
  const signature = base64UrlEncode(signer.sign(creds.private_key));
  const jwt = `${unsignedJwt}.${signature}`;

  const resp = await fetch(tokenUri, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: jwt,
    }).toString(),
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Falha ao autenticar no Google OAuth2 (${resp.status}): ${errText}`);
  }

  const data = await resp.json();
  return data.access_token;
}

function deriveSubscriberName(email: string, providedName?: string): string {
  if (providedName && providedName.trim().length >= 2) {
    return providedName.trim();
  }
  const localPart = email.split("@")[0] || "Leitor";
  const cleaned = localPart
    .replace(/[._-]+/g, " ")
    .replace(/\d+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  if (!cleaned) return "Leitor ANJ";

  return cleaned
    .split(" ")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}

async function resolveSpreadsheetId(accessToken: string): Promise<string> {
  const envSheetId = (
    process.env.GOOGLE_SHEETS_ID ||
    process.env.GOOGLE_SHEET_ID ||
    (import.meta as any).env?.GOOGLE_SHEETS_ID ||
    ""
  ).trim();

  if (envSheetId) return envSheetId;

  // Tenta localizar "noticias_db" via Google Drive API, com fallback para o ID oficial da planilha
  try {
    const q = encodeURIComponent(
      "name = 'noticias_db' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
    );
    const driveResp = await fetch(
      `https://www.googleapis.com/drive/v3/files?q=${q}&fields=files(id,name)&pageSize=1`,
      { headers: { Authorization: `Bearer ${accessToken}` } }
    );
    if (driveResp.ok) {
      const driveData = await driveResp.json();
      if (driveData.files && driveData.files.length > 0 && driveData.files[0].id) {
        return driveData.files[0].id;
      }
    }
  } catch (e) {
    console.warn("⚠️ Aviso ao buscar noticias_db via Drive API, usando ID padrão:", e);
  }

  return DEFAULT_NOTICIAS_DB_ID;
}

async function saveToNoticiasDb(
  rawGcpJson: string,
  email: string,
  nome?: string
): Promise<{ status: "created" | "reactivated" | "already_active"; sheetTitle: string }> {
  const creds = parseServiceAccount(rawGcpJson);
  const accessToken = await getGoogleAccessToken(creds);
  const spreadsheetId = await resolveSpreadsheetId(accessToken);

  // 1. Descobre o nome real da primeira aba (sheet1)
  const metaResp = await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${spreadsheetId}?fields=sheets.properties.title`,
    { headers: { Authorization: `Bearer ${accessToken}` } }
  );
  if (!metaResp.ok) {
    const errText = await metaResp.text();
    throw new Error(`Erro ao abrir planilha noticias_db (${metaResp.status}): ${errText}`);
  }
  const metaData = await metaResp.json();
  const sheetTitle: string = metaData?.sheets?.[0]?.properties?.title || "Sheet1";

  // 2. Lê todas as linhas da primeira aba para obter cabeçalhos reais e checar duplicidade
  const rangeAll = `${sheetTitle}!A1:Z5000`;
  const valuesResp = await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${spreadsheetId}/values/${encodeURIComponent(rangeAll)}`,
    { headers: { Authorization: `Bearer ${accessToken}` } }
  );
  if (!valuesResp.ok) {
    const errText = await valuesResp.text();
    throw new Error(`Erro ao ler linhas de noticias_db (${valuesResp.status}): ${errText}`);
  }
  const valuesData = await valuesResp.json();
  const rows: string[][] = valuesData.values || [];

  const defaultHeaders = [
    "Nome",
    "Email",
    "Economia",
    "IA",
    "Fofoca",
    "Politica",
    "Cinema",
    "Mundo",
    "Wellness",
    "Ciencia",
  ];
  const headers: string[] =
    rows.length > 0 && rows[0].length > 0
      ? rows[0].map((h) => String(h).trim())
      : defaultHeaders;

  const emailLower = email.trim().toLowerCase();
  const nomeFinal = deriveSubscriberName(emailLower, nome);

  const emailColIdx = Math.max(
    headers.findIndex((h) => h.toLowerCase() === "email" || h.toLowerCase() === "e-mail"),
    1
  );

  // 3. Verifica se o e-mail já está cadastrado na planilha
  for (let i = 1; i < rows.length; i++) {
    const row = rows[i] || [];
    const existingEmail = String(row[emailColIdx] || "").trim().toLowerCase();
    if (existingEmail === emailLower) {
      // Verifica se estava cancelado (com "Não" em todos os cadernos) ou sem nome
      const updatedRow = headers.map((h, idx) => {
        if (h.toLowerCase() === "nome") return String(row[idx] || "").trim() || nomeFinal;
        if (h.toLowerCase() === "email" || h.toLowerCase() === "e-mail") return emailLower;
        const valAtual = String(row[idx] || "").trim();
        if (!valAtual || valAtual.toLowerCase() === "não" || valAtual.toLowerCase() === "nao") {
          return "Sim";
        }
        return valAtual;
      });

      const needsUpdate = updatedRow.some((val, idx) => val !== String(row[idx] || "").trim());
      if (needsUpdate) {
        const rowNumber = i + 1;
        const updateRange = `${sheetTitle}!A${rowNumber}`;
        await fetch(
          `https://sheets.googleapis.com/v4/spreadsheets/${spreadsheetId}/values/${encodeURIComponent(
            updateRange
          )}?valueInputOption=USER_ENTERED`,
          {
            method: "PUT",
            headers: {
              Authorization: `Bearer ${accessToken}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ values: [updatedRow] }),
          }
        );
        return { status: "reactivated", sheetTitle };
      }

      return { status: "already_active", sheetTitle };
    }
  }

  // 4. Monta nova linha alinhada aos cabeçalhos reais da planilha noticias_db
  const novaLinha = headers.map((h) => {
    const hLower = h.toLowerCase();
    if (hLower === "nome") return nomeFinal;
    if (hLower === "email" || hLower === "e-mail") return emailLower;
    return "Sim";
  });

  const appendRange = `${sheetTitle}!A1`;
  const appendResp = await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${spreadsheetId}/values/${encodeURIComponent(
      appendRange
    )}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ values: [novaLinha] }),
    }
  );

  if (!appendResp.ok) {
    const errText = await appendResp.text();
    throw new Error(`Falha ao gravar assinante em noticias_db (${appendResp.status}): ${errText}`);
  }

  return { status: "created", sheetTitle };
}

export async function POST({ request }: { request: Request }) {
  try {
    const body = await request.json();
    const email = body?.email?.trim();
    const nome = body?.nome?.trim();

    if (!email || !email.includes("@")) {
      return new Response(
        JSON.stringify({ success: false, error: "E-mail inválido." }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    const gcpJson =
      process.env.GCP_JSON || (import.meta as any).env?.GCP_JSON || "";
    const webhookUrl =
      process.env.GOOGLE_SHEETS_WEBHOOK_URL ||
      process.env.WEBHOOK_SUBSCRIBE_URL ||
      (import.meta as any).env?.GOOGLE_SHEETS_WEBHOOK_URL ||
      "";
    const resendApiKey =
      process.env.RESEND_API_KEY || (import.meta as any).env?.RESEND_API_KEY || "";

    let savedToSheets = false;
    let sheetsStatus: "created" | "reactivated" | "already_active" | "webhook" | null = null;

    // 1. Conexão Direta com Google Sheets API (noticias_db) via GCP_JSON (Opção 2)
    if (gcpJson) {
      const result = await saveToNoticiasDb(gcpJson, email, nome);
      savedToSheets = true;
      sheetsStatus = result.status;
    } else if (webhookUrl) {
      // Fallback caso um Webhook do Google Apps Script esteja configurado
      const whResp = await fetch(webhookUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nome: deriveSubscriberName(email, nome),
          email,
          origem: "landing_page_astro",
          data: new Date().toISOString(),
        }),
      });
      if (!whResp.ok) {
        throw new Error(`Webhook retornou status ${whResp.status}`);
      }
      savedToSheets = true;
      sheetsStatus = "webhook";
    } else {
      return new Response(
        JSON.stringify({
          success: false,
          error:
            "Configuração pendente: adicione a variável GCP_JSON nas Environment Variables do projeto na Vercel para gravar na planilha noticias_db.",
        }),
        { status: 500, headers: { "Content-Type": "application/json" } }
      );
    }

    // 2. Dispara e-mail de boas-vindas via Resend (se configurado e se não for já ativo)
    if (resendApiKey && sheetsStatus !== "already_active") {
      try {
        const resendFrom =
          process.env.RESEND_FROM ||
          (import.meta as any).env?.RESEND_FROM ||
          "All News Journal <onboarding@resend.dev>";
        await fetch("https://api.resend.com/emails", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${resendApiKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            from: resendFrom,
            to: email,
            subject: "Bem-vindo ao All News Journal",
            html: `<p>Olá, <strong>${deriveSubscriberName(email, nome)}</strong>!</p><p>Sua inscrição no <strong>All News Journal</strong> foi confirmada na nossa base oficial. A partir de amanhã, você receberá nossa edição executiva pontualmente às 06:15 com os resumos e o podcast matinal.</p>`,
          }),
        });
      } catch (e) {
        console.warn("⚠️ Falha ao disparar boas-vindas Resend:", e);
      }
    }

    return new Response(
      JSON.stringify({
        success: savedToSheets,
        status: sheetsStatus,
        message:
          sheetsStatus === "already_active"
            ? "Este e-mail já está ativo na lista de assinantes!"
            : "Inscrição confirmada com sucesso na planilha noticias_db!",
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  } catch (error: any) {
    console.error("❌ Erro em /api/subscribe:", error);
    return new Response(
      JSON.stringify({
        success: false,
        error: error?.message || "Erro interno ao salvar assinatura na planilha.",
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}

