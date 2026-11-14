# Individual AI coding prompts

Each file is a complete, individualized master prompt of approximately 18,000 words. The opening assignment, file ownership, ordered work packets and acceptance criteria are specific to its owner. The shared contract, project context and reference scenarios are included so every coding agent has the same facts. The long reference is not a requirement to implement every feature or test every scenario.

## Start with your file

Accept the repository invitation if needed, clone or open this repository in your coding environment, and give the agent this instruction with your filename:

> Read `prompts/YOUR_NAME.md` completely, inspect the current repository and my assigned issue, then carry out my workstream. Follow the current integration contract, preserve teammates' work, and implement and verify the first useful slice before expanding scope. Use the role's acceptance criteria for the final handoff.

If the coding tool cannot access files, paste the complete prompt from your individual email. The repository is private; sign into the invited GitHub account to open its links. Do not paste all six prompts into one agent or ask every person to build the whole application.

| Teammate | Workstream | Master prompt | Words | GitHub task | Assignment status |
|---|---|---|---:|---|---|
| Sathvik Loke (`sathvikloke`) | Scientific validation, investigation content and integration leadership | [SATHVIK.md](SATHVIK.md) | 18,778 | [#1](https://github.com/sathvikloke/perigee/issues/1) | Assigned |
| Sagar Raut (`s1g6r`) | NASA archive and scientific image pipeline | [SAGAR.md](SAGAR.md) | 18,689 | [#2](https://github.com/sathvikloke/perigee/issues/2) | Assigned |
| Akshobya Rao (`AkshobyaRaoSWE`) | Frontend and visual experience | [AKSHOBYA.md](AKSHOBYA.md) | 18,786 | [#3](https://github.com/sathvikloke/perigee/issues/3) | Owner named; invitation pending |
| Aditya R (`adityaraut09`) | Backend API and bounded request orchestration | [ADITYA.md](ADITYA.md) | 18,675 | [#4](https://github.com/sathvikloke/perigee/issues/4) | Assigned |
| Suhrit Bestavemula (`suhritb`) | Backend platform, asset serving and Vercel deployment | [SUHRIT.md](SUHRIT.md) | 18,673 | [#5](https://github.com/sathvikloke/perigee/issues/5) | Owner named; invitation pending |
| Neeraj Movva (`movvaneeraj`) | Focused QA, usability and demo support | [NEERAJ.md](NEERAJ.md) | 18,667 | [#6](https://github.com/sathvikloke/perigee/issues/6) | Owner named; invitation pending |

## Shared boundaries

- Only **Sathvik and Sagar** need the full original NASA dataset. The other roles use small development fixtures and the shared API.
- **Akshobya** owns the frontend. **Aditya** owns API models and request orchestration. **Suhrit** owns platform integration, catalog/assets serving and Vercel deployment.
- **Neeraj** has a short minimum QA track; optional checks do not block the core team.
- The product is a **responsive web app**, usable from desktop and mobile browsers. No native mobile app or runtime AI model is required.
- Use the [integration contract](../docs/INTEGRATION_CONTRACT.md) for interfaces and the [deployment handoff](../docs/DEPLOYMENT.md) for the existing Vercel project. A project has been created; the application still needs implementation and its first deployment.
- Existing raw research data remain local. Build processing code and generated application assets from scratch.

The [manifest](PROMPT_MANIFEST.json) records exact word counts, byte sizes and SHA-256 hashes. Counts use whitespace-separated words in each complete Markdown file. The standalone [operating guide](OPERATING_GUIDE.md) and [handoff recipes](HANDOFF_RECIPES.md) are also embedded in every prompt.
