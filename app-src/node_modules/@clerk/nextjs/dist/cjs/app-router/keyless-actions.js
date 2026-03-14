"use strict";
"use server";
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
var keyless_actions_exports = {};
__export(keyless_actions_exports, {
  createOrReadKeylessAction: () => createOrReadKeylessAction,
  deleteKeylessAction: () => deleteKeylessAction,
  syncKeylessConfigAction: () => syncKeylessConfigAction
});
module.exports = __toCommonJS(keyless_actions_exports);
var import_headers = require("next/headers");
var import_navigation = require("next/navigation");
var import_errorThrower = require("../server/errorThrower");
var import_headers_utils = require("../server/headers-utils");
var import_keyless = require("../server/keyless");
var import_keyless_log_cache = require("../server/keyless-log-cache");
var import_keyless_node = require("../server/keyless-node");
var import_feature_flags = require("../utils/feature-flags");
const keylessCookieConfig = {
  secure: false,
  httpOnly: false,
  sameSite: "lax"
};
async function syncKeylessConfigAction(args) {
  const { claimUrl, publishableKey, secretKey, returnUrl } = args;
  const cookieStore = await (0, import_headers.cookies)();
  const request = new Request("https://placeholder.com", { headers: await (0, import_headers.headers)() });
  const keylessCookie = await (0, import_keyless.getKeylessCookieValue)((name) => {
    var _a;
    return (_a = cookieStore.get(name)) == null ? void 0 : _a.value;
  });
  const pksMatch = (keylessCookie == null ? void 0 : keylessCookie.publishableKey) === publishableKey;
  const sksMatch = (keylessCookie == null ? void 0 : keylessCookie.secretKey) === secretKey;
  if (pksMatch && sksMatch) {
    return;
  }
  cookieStore.set(
    await (0, import_keyless.getKeylessCookieName)(),
    JSON.stringify({ claimUrl, publishableKey, secretKey }),
    keylessCookieConfig
  );
  if ((0, import_headers_utils.detectClerkMiddleware)(request)) {
    (0, import_navigation.redirect)(`/clerk-sync-keyless?returnUrl=${returnUrl}`, import_navigation.RedirectType.replace);
  }
  return;
}
async function createOrReadKeylessAction() {
  var _a;
  if (!import_feature_flags.canUseKeyless) {
    return null;
  }
  let result;
  try {
    result = await (0, import_keyless_node.keyless)().getOrCreateKeys();
  } catch {
    result = null;
  }
  if (!result) {
    import_errorThrower.errorThrower.throwMissingPublishableKeyError();
    return null;
  }
  (_a = import_keyless_log_cache.clerkDevelopmentCache) == null ? void 0 : _a.log({
    cacheKey: result.publishableKey,
    msg: (0, import_keyless_log_cache.createKeylessModeMessage)(result)
  });
  const { claimUrl, publishableKey, secretKey, apiKeysUrl } = result;
  void (await (0, import_headers.cookies)()).set(
    await (0, import_keyless.getKeylessCookieName)(),
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
  if (!import_feature_flags.canUseKeyless) {
    return;
  }
  try {
    await (0, import_keyless_node.keyless)().removeKeys();
  } catch {
  }
}
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  createOrReadKeylessAction,
  deleteKeylessAction,
  syncKeylessConfigAction
});
