"use server";
import { cookies, headers } from "next/headers";
import { redirect, RedirectType } from "next/navigation";
import { errorThrower } from "../server/errorThrower";
import { detectClerkMiddleware } from "../server/headers-utils";
import { getKeylessCookieName, getKeylessCookieValue } from "../server/keyless";
import { clerkDevelopmentCache, createKeylessModeMessage } from "../server/keyless-log-cache";
import { keyless } from "../server/keyless-node";
import { canUseKeyless } from "../utils/feature-flags";
const keylessCookieConfig = {
  secure: false,
  httpOnly: false,
  sameSite: "lax"
};
async function syncKeylessConfigAction(args) {
  const { claimUrl, publishableKey, secretKey, returnUrl } = args;
  const cookieStore = await cookies();
  const request = new Request("https://placeholder.com", { headers: await headers() });
  const keylessCookie = await getKeylessCookieValue((name) => {
    var _a;
    return (_a = cookieStore.get(name)) == null ? void 0 : _a.value;
  });
  const pksMatch = (keylessCookie == null ? void 0 : keylessCookie.publishableKey) === publishableKey;
  const sksMatch = (keylessCookie == null ? void 0 : keylessCookie.secretKey) === secretKey;
  if (pksMatch && sksMatch) {
    return;
  }
  cookieStore.set(
    await getKeylessCookieName(),
    JSON.stringify({ claimUrl, publishableKey, secretKey }),
    keylessCookieConfig
  );
  if (detectClerkMiddleware(request)) {
    redirect(`/clerk-sync-keyless?returnUrl=${returnUrl}`, RedirectType.replace);
  }
  return;
}
async function createOrReadKeylessAction() {
  var _a;
  if (!canUseKeyless) {
    return null;
  }
  let result;
  try {
    result = await keyless().getOrCreateKeys();
  } catch {
    result = null;
  }
  if (!result) {
    errorThrower.throwMissingPublishableKeyError();
    return null;
  }
  (_a = clerkDevelopmentCache) == null ? void 0 : _a.log({
    cacheKey: result.publishableKey,
    msg: createKeylessModeMessage(result)
  });
  const { claimUrl, publishableKey, secretKey, apiKeysUrl } = result;
  void (await cookies()).set(
    await getKeylessCookieName(),
    JSON.stringify({ claimUrl, publishableKey, secretKey }),
    keylessCookieConfig
  );
  return {
    claimUrl,
    publishableKey,
    apiKeysUrl
  };
}
async function deleteKeylessAction() {
  if (!canUseKeyless) {
    return;
  }
  try {
    await keyless().removeKeys();
  } catch {
  }
}
export {
  createOrReadKeylessAction,
  deleteKeylessAction,
  syncKeylessConfigAction
};
