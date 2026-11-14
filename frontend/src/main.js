// DEPLOYMENT PLACEHOLDER - replaced by worker 01 at integration.
// Calls the same-origin API prefix the real client will use.
const el = document.getElementById("health");
fetch("/api/v1/health")
  .then(async (r) => {
    el.textContent = `${r.status} ${r.headers.get("content-type")} ${await r.text()}`;
  })
  .catch((e) => {
    el.textContent = `request failed: ${e}`;
  });
