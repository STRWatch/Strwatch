import "../../chunk-BUSYA2B4.js";
import { headers } from "next/headers";
import React from "react";
import { canUseKeyless } from "../../utils/feature-flags";
import { mergeNextClerkPropsWithEnv } from "../../utils/mergeNextClerkPropsWithEnv";
import { onlyTry } from "../../utils/only-try";
import { ClientClerkProvider } from "../client/ClerkProvider";
import { deleteKeylessAction } from "../keyless-actions";
async function getKeylessStatus(params) {
  let [shouldRunAsKeyless, runningWithClaimedKeys, locallyStoredPublishableKey] = [false, false, ""];
  if (canUseKeyless) {
    locallyStoredPublishableKey = await import("../../server/keyless-node.js").then((mod) => {
      var _a;
      return ((_a = mod.keyless().readKeys()) == null ? void 0 : _a.publishableKey) || "";
    }).catch(() => "");
    runningWithClaimedKeys = Boolean(params.publishableKey) && params.publishableKey === locallyStoredPublishableKey;
    shouldRunAsKeyless = !params.publishableKey || runningWithClaimedKeys;
  }
  return {
    shouldRunAsKeyless,
    runningWithClaimedKeys
  };
}
const KeylessProvider = async (props) => {
  const { rest, runningWithClaimedKeys, __internal_scriptsSlot, children } = props;
  const newOrReadKeys = await import("../../server/keyless-node.js").then((mod) => mod.keyless().getOrCreateKeys()).catch(() => null);
  const { clerkDevelopmentCache, createConfirmationMessage, createKeylessModeMessage } = await import("../../server/keyless-log-cache.js");
  if (!newOrReadKeys) {
    return /* @__PURE__ */ React.createElement(
      ClientClerkProvider,
      {
        ...mergeNextClerkPropsWithEnv(rest),
        disableKeyless: true,
        __internal_scriptsSlot
      },
      children
    );
  }
  const clientProvider = /* @__PURE__ */ React.createElement(
    ClientClerkProvider,
    {
      ...mergeNextClerkPropsWithEnv({
        ...rest,
        publishableKey: newOrReadKeys.publishableKey,
        __internal_keyless_claimKeylessApplicationUrl: newOrReadKeys.claimUrl,
        __internal_keyless_copyInstanceKeysUrl: newOrReadKeys.apiKeysUrl,
        // Explicitly use `null` instead of `undefined` here to avoid persisting `deleteKeylessAction` during merging of options.
        __internal_keyless_dismissPrompt: runningWithClaimedKeys ? deleteKeylessAction : null
      }),
      __internal_scriptsSlot
    },
    children
  );
  if (runningWithClaimedKeys) {
    try {
      const keylessService = await import("../../server/keyless-node.js").then((mod) => mod.keyless());
      await (clerkDevelopmentCache == null ? void 0 : clerkDevelopmentCache.run(() => keylessService.completeOnboarding(), {
        cacheKey: `${newOrReadKeys.publishableKey}_complete`,
        onSuccessStale: 24 * 60 * 60 * 1e3
        // 24 hours
      }));
    } catch {
    }
    clerkDevelopmentCache == null ? void 0 : clerkDevelopmentCache.log({
      cacheKey: `${newOrReadKeys.publishableKey}_claimed`,
      msg: createConfirmationMessage()
    });
    return clientProvider;
  }
  const KeylessCookieSync = await import("../client/keyless-cookie-sync.js").then((mod) => mod.KeylessCookieSync);
  const headerStore = await headers();
  const host = headerStore.get("x-forwarded-host");
  const proto = headerStore.get("x-forwarded-proto");
  const claimUrl = new URL(newOrReadKeys.claimUrl);
  if (host && proto) {
    onlyTry(() => claimUrl.searchParams.set("return_url", new URL(`${proto}://${host}`).href));
  }
  clerkDevelopmentCache == null ? void 0 : clerkDevelopmentCache.log({
    cacheKey: newOrReadKeys.publishableKey,
    msg: createKeylessModeMessage({ ...newOrReadKeys, claimUrl: claimUrl.href })
  });
  return /* @__PURE__ */ React.createElement(KeylessCookieSync, { ...newOrReadKeys }, clientProvider);
};
export {
  KeylessProvider,
  getKeylessStatus
};
//# sourceMappingURL=keyless-provider.js.map