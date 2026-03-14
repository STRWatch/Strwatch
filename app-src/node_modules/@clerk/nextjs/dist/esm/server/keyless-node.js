import "../chunk-BUSYA2B4.js";
import { createKeylessService, createNodeFileStorage } from "@clerk/shared/keyless";
import { createClerkClientWithOptions } from "./createClerkClient";
import { nodeCwdOrThrow, nodeFsOrThrow, nodePathOrThrow } from "./fs/utils";
function createFileStorage() {
  const fs = nodeFsOrThrow();
  const path = nodePathOrThrow();
  const cwd = nodeCwdOrThrow();
  return createNodeFileStorage(fs, path, {
    cwd,
    frameworkPackageName: "@clerk/nextjs"
  });
}
let keylessServiceInstance = null;
function keyless() {
  if (!keylessServiceInstance) {
    const client = createClerkClientWithOptions({});
    keylessServiceInstance = createKeylessService({
      storage: createFileStorage(),
      api: {
        async createAccountlessApplication(requestHeaders) {
          try {
            return await client.__experimental_accountlessApplications.createAccountlessApplication({
              requestHeaders
            });
          } catch {
            return null;
          }
        },
        async completeOnboarding(requestHeaders) {
          try {
            return await client.__experimental_accountlessApplications.completeAccountlessApplicationOnboarding({
              requestHeaders
            });
          } catch {
            return null;
          }
        }
      },
      framework: "nextjs"
    });
  }
  return keylessServiceInstance;
}
export {
  keyless
};
//# sourceMappingURL=keyless-node.js.map