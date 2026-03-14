import "../chunk-BUSYA2B4.js";
import { isDevelopmentEnvironment } from "@clerk/shared/utils";
import { KEYLESS_DISABLED } from "../server/constants";
const canUseKeyless = isDevelopmentEnvironment() && !KEYLESS_DISABLED;
export {
  canUseKeyless
};
//# sourceMappingURL=feature-flags.js.map