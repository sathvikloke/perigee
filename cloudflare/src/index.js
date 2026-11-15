// Worker entry. Only the default export lives here: the Workers runtime treats
// every named export of the main module as an entrypoint. Logic: ./app.js.
import { handle } from "./app.js";

export default {
  fetch(request, env) {
    return handle(request, env);
  },
};
