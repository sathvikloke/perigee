# Perigee deployment handoff

## Current setup

The Vercel project exists. The repository-filtered Vercel project listing returns it for `https://github.com/sathvikloke/perigee`. No deployment exists yet; the repository contains planning and research rather than an implemented application. Creating the project does not make the web app live.

- Dashboard: https://vercel.com/sathviklokes-projects/perigee
- Project: `perigee`
- Project ID: `prj_7JhA3Inkh0euYF4UVwhyDYJusAfQ`
- Team: `sathviklokes-projects`
- Team ID: `team_blm7QlnXb2J53PuzDBnv9TcO`
- Repository: https://github.com/sathvikloke/perigee
- Intended production branch: `main`; verify the actual Git and build settings before the first deployment.
- Deployment owner: Suhrit, coordinating with Akshobya and Aditya.

These IDs identify resources; they are not credentials. Do not put tokens or signing secrets in this file.

## First deployment

Follow [the integration contract](INTEGRATION_CONTRACT.md). The preferred setup is React/TypeScript/Vite in `frontend/` plus Python/FastAPI in `backend/`, deployed together using Vercel Services. Services is Beta. Check its current configuration documentation when creating `vercel.json`; use the schema supported by the actual project and CLI.

Validate the smallest shell first. Route `/api/(.*)` to the Python service before the frontend catch-all, and make the backend handle the original path received. Check the frontend, a direct frontend URL, `/api/v1/health`, a catalog response and one small asset. Inspect response content types; frontend HTML returned at an API URL is a failure.

Then deploy one bounded archive search and one processed frame. Measure cold-start behavior, request duration, response size and the packaged Python dependencies. Exclude raw FITS, the research environment and download directories from the deployment. Do not assume a successful local run establishes deployed performance.

If Services blocks progress for more than 30 minutes, coordinate a two-project Vercel fallback with one explicit frontend API origin. Keep the same API contract. Verify CORS from the deployed frontend and record both project URLs. Do not add a persistent worker, database or queue without an actual measured need and coordinated contract change.

## Configuration and release checks

Use backend-only environment configuration for the frame-token signing secret. Keep an example configuration containing names and descriptions, never real values. Preview and production environments may differ; test the environment intended for the public demonstration. Use supported Python and package versions, and commit the appropriate dependency lockfiles through their owners.

Treat local filesystem writes as temporary request scratch space. Small curated assets can be packaged read-only. Optional caching must tolerate a miss and must not become the only copy of user-authored evidence or job state. Browser evidence cards remain local in this version.

Before marking a release ready, test the public URL without a team login, including a curated investigation, a non-preset coordinate search, a frame result and an evidence export. Preserve the last verified working deployment while checking its replacement. Record the actual deployment URL, commit and remaining limitations here after implementation.

Official references: [Vercel Services](https://vercel.com/docs/services), [Python runtime](https://vercel.com/docs/functions/runtimes/python), [Functions limits](https://vercel.com/docs/functions/limitations), [Deployment Protection](https://vercel.com/docs/deployment-protection).
