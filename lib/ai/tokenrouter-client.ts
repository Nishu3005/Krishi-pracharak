import { prisma } from "@/lib/prisma";

if (typeof window !== "undefined") {
  throw new Error("TokenRouter client can only be used on the server.");
}

type TokenRouterInput = {
  systemPrompt: string;
  userPrompt: string;
  jsonSchemaDescription: string;
  featureName: string;
  inputSummary?: string;
};

type TokenRouterMetadata = {
  provider: "tokenrouter";
  model: string;
  featureName: string;
  rawResponse: unknown;
};

export type TokenRouterJsonResult<T> = {
  parsed: T;
  rawText: string;
  metadata: TokenRouterMetadata;
};

export class TokenRouterError extends Error {
  code: "missing_api_key" | "api_error" | "timeout" | "empty_output" | "invalid_json";
  rawText?: string;

  constructor(code: TokenRouterError["code"], message: string, rawText?: string) {
    super(message);
    this.name = "TokenRouterError";
    this.code = code;
    this.rawText = rawText;
  }
}

function modelName() {
  return process.env.OPENAI_MODEL || "auto:balance";
}

function timeoutMs() {
  const value = Number(process.env.TOKENROUTER_TIMEOUT_MS || 60000);
  return Number.isFinite(value) && value > 0 ? value : 60000;
}

function extractText(responseJson: any) {
  if (typeof responseJson?.output_text === "string") {
    return responseJson.output_text;
  }

  const outputText = responseJson?.output?.[0]?.content?.[0]?.text;
  if (typeof outputText === "string") {
    return outputText;
  }

  const choiceText = responseJson?.choices?.[0]?.message?.content;
  if (typeof choiceText === "string") {
    return choiceText;
  }

  return JSON.stringify(responseJson);
}

function parseJsonText<T>(text: string): T {
  const trimmed = text.trim();
  try {
    return JSON.parse(trimmed) as T;
  } catch {
    const match = trimmed.match(/\{[\s\S]*\}/);
    if (match) {
      try {
        return JSON.parse(match[0]) as T;
      } catch {
        // fall through to the explicit error below
      }
    }
    throw new TokenRouterError("invalid_json", "TokenRouter response could not be parsed as JSON.", text);
  }
}

async function writeAiLog(params: {
  feature: string;
  model: string;
  inputSummary: string;
  outputSummary?: string;
  status: string;
  errorMessage?: string;
}) {
  try {
    await prisma.aiGenerationLog.create({
      data: {
        feature: params.feature,
        provider: "tokenrouter",
        model: params.model,
        inputSummary: params.inputSummary,
        outputSummary: params.outputSummary,
        status: params.status,
        errorMessage: params.errorMessage
      }
    });
  } catch {
    // Logging must never convert an AI failure into a different app failure.
  }
}

export async function callTokenRouterJson<T>({
  systemPrompt,
  userPrompt,
  jsonSchemaDescription,
  featureName,
  inputSummary = featureName
}: TokenRouterInput): Promise<TokenRouterJsonResult<T>> {
  const apiKey = process.env.TOKENROUTER_API_KEY;
  const model = modelName();

  if (!apiKey) {
    const message = "TokenRouter API key missing. Real AI is required for this workflow.";
    await writeAiLog({ feature: featureName, model, inputSummary, status: "failed", errorMessage: message });
    throw new TokenRouterError("missing_api_key", message);
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs());
  const url = process.env.TOKENROUTER_BASE_URL || "https://api.tokenrouter.io/v1/responses";

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model,
        input: [
          {
            role: "system",
            content: `${systemPrompt}\n\nRequired JSON schema:\n${jsonSchemaDescription}`
          },
          {
            role: "user",
            content: userPrompt
          }
        ]
      }),
      signal: controller.signal
    });

    const responseBody = await response.text();
    if (!response.ok) {
      const message = `TokenRouter API failed with status ${response.status}.`;
      await writeAiLog({
        feature: featureName,
        model,
        inputSummary,
        outputSummary: responseBody.slice(0, 500),
        status: "failed",
        errorMessage: message
      });
      throw new TokenRouterError("api_error", message, responseBody);
    }

    let responseJson: unknown;
    try {
      responseJson = JSON.parse(responseBody);
    } catch {
      throw new TokenRouterError("invalid_json", "TokenRouter API response envelope was not JSON.", responseBody);
    }

    const rawText = extractText(responseJson);
    if (!rawText.trim()) {
      throw new TokenRouterError("empty_output", "TokenRouter returned an empty response.", responseBody);
    }

    const parsed = parseJsonText<T>(rawText);
    await writeAiLog({
      feature: featureName,
      model,
      inputSummary,
      outputSummary: rawText.slice(0, 500),
      status: "success"
    });

    return {
      parsed,
      rawText,
      metadata: {
        provider: "tokenrouter",
        model,
        featureName,
        rawResponse: responseJson
      }
    };
  } catch (error) {
    const tokenRouterError =
      error instanceof TokenRouterError
        ? error
        : error instanceof Error && error.name === "AbortError"
          ? new TokenRouterError("timeout", "TokenRouter API request timed out.")
          : new TokenRouterError("api_error", error instanceof Error ? error.message : "TokenRouter API failed.");

    await writeAiLog({
      feature: featureName,
      model,
      inputSummary,
      outputSummary: tokenRouterError.rawText?.slice(0, 500),
      status: "failed",
      errorMessage: tokenRouterError.message
    });
    throw tokenRouterError;
  } finally {
    clearTimeout(timer);
  }
}
