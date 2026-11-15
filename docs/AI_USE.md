# Use of AI in Perigee

## Statement

Perigee was built by our team with help from AI tools: Claude Code (Anthropic) and OpenAI Codex. We used them to help implement the backend and the frontend, and to help edit our demo video. The idea and approach were our own, and our team directed the project throughout. We monitored the AI tools while they worked, then went back and reviewed what they produced: we read the code, tested the app, and checked that the science and the explanations made sense before we kept anything.

The cartoon telescope and the opening rocket with its separate exhaust were made with OpenAI image generation and are labelled "AI illustration" in the app. They are decorative artwork, not engineering models or observations. Perigee itself runs no AI. Every image in an investigation is a real NASA SPHEREx observation, and dates, wavelengths, positions and quality flags are computed directly from the archive data.

## Tools and what they were used for

| Tool | Used for |
|---|---|
| Claude Code (Anthropic) | Helping implement the FastAPI backend, the SPHEREx data processing, the React frontend and the tests |
| OpenAI Codex | Helping with the frontend design and user interface |
| OpenAI image generation | The decorative cartoon telescope and rocket/exhaust ([provenance](../qa/landing-motion/ASSET.md)), labelled "AI illustration" in the app |
| AI-assisted editing | Editing the demo video |

## No AI in the app

The deployed app contains no AI model and calls no AI service. The backend depends only on FastAPI, Starlette, Pydantic, httpx, anyio, Astropy, NumPy, Pillow and certifi, and the frontend only on React. The case explanations are fixed text written in advance, not generated while the app runs.

## Where the acknowledgment appears

- This file and the "Use of AI" section of the [README](../README.md).
- Commit metadata: AI-assisted commits carry a `Co-Authored-By` trailer naming the AI tool.
- The app labels the landing illustration "AI illustration".
- The "Use of SI" answer on the Space Apps project page.

The Space Apps [submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/) asks teams to state where and how AI tools were used, and requires AI-generated images or video to carry a visible watermark. Screenshots and recordings of the app itself are not generated imagery.
