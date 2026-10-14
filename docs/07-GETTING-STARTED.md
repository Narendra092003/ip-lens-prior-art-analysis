# 07 — Getting Started in Visual Studio Code

This is the setup guide included in the project ZIP. It has no schedule: work through the current phase when you are ready. The separate beginner build guide is not part of the ZIP; the ordered phases are in [`19-BUILD-ORDER.md`](./19-BUILD-ORDER.md) and in Section 12 of the project specification.

## 1. Open the project folder

On this machine, the prepared clean workspace is:

```text
C:\Users\HP\Documents\Codex\2026-10-13\ip-lens-step-by-step
```

Open Visual Studio Code, choose **File → Open Folder…**, and select the folder containing `PROJECT_SPECIFICATION.md`. If starting on another computer, extract this project ZIP into a new folder and open the extracted project folder. Keep the existing `ip-lens` reference folder separate; do not build in it.

If Visual Studio Code asks whether you trust the folder, trust it only if it is the project folder you just created or reviewed.

## 2. Install the editor extensions

In Visual Studio Code, open **Extensions** from the left sidebar or press **Ctrl+Shift+X**. Install:

1. **Python**, published by Microsoft.
2. **GitHub Copilot** and **GitHub Copilot Chat**, if your account has access.

Sign in to GitHub in Copilot Chat. The Python extension helps the editor understand Python, but it is not itself the Python runtime. The project uses `uv` to install/manage the required Python version later.

- [Python in Visual Studio Code](https://code.visualstudio.com/docs/languages/python)
- [Set up Copilot in Visual Studio Code](https://code.visualstudio.com/docs/setup/copilot)

## 3. Start with one phase in AI Chat

Open `PROJECT_SPECIFICATION.md` in the editor. Open Copilot Chat and attach the specification plus the document for the current phase. For your first session, attach [`19-BUILD-ORDER.md`](./19-BUILD-ORDER.md) as well and paste:

```text
I am new to building software projects. Read PROJECT_SPECIFICATION.md and docs/19-BUILD-ORDER.md. Use the open folder as the project root. Implement Phase 1 only. Before changing files, explain the goal and list the files you plan to create or change. Keep the work limited to the folder structure and starter configuration described in the specification. Do not implement application behavior or skip to later phases. Do not copy code from the separate ip-lens reference folder. At the end, summarize what changed and wait for my review before continuing.
```

For each later phase, ask the assistant to read only the relevant specification section and phase. Review its proposed file list, inspect the changed files, and approve the next phase yourself.

## 4. Install project tools after the structure exists

After Phase 1 creates `pyproject.toml`, install `uv`. One documented Windows option is:

```powershell
winget install --id=astral-sh.uv -e
```

Close and reopen the VS Code terminal, then check the install:

```powershell
uv --version
```

Once `pyproject.toml` and `uv.lock` are ready, open a terminal in the project root and run:

```powershell
uv sync
```

`uv sync` creates the local project environment and installs its locked dependencies. If the required Python version is missing, `uv` can install and manage it; see the [official uv Python guide](https://docs.astral.sh/uv/guides/install-python/). In VS Code, press **Ctrl+Shift+P**, choose **Python: Select Interpreter**, and select the project's `.venv` when it appears.

The [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) lists current Windows installation options.

## 5. Configure Gemini when that phase is reached

Do not create or paste a key during the file-structure phase. When the Gemini integration phase is ready:

1. Copy `.env.example` to `.env` in the project root.
2. Put your Gemini key only in `.env`.
3. Confirm `.env` is ignored by Git.
4. Restart the API after changing configuration.

Never paste the key into AI Chat, screenshots, source code, or GitHub. The application sends the disclosure text and retrieved excerpts to the configured Gemini API for generation. Use fictional sample documents unless you have permission to send real material to that service. Read Google's [Gemini API key guidance](https://ai.google.dev/gemini-api/docs/api-key).

## 6. Run the app after implementation

After the API and Streamlit phases are complete, open two VS Code terminals in the project root. Start the API in the first:

```powershell
uv run uvicorn backend.app.main:app --reload --port 8001
```

Start Streamlit in the second:

```powershell
uv run streamlit run frontend/streamlit_app.py
```

Open the local address Streamlit prints. FastAPI's health endpoint is at `http://127.0.0.1:8001/health` and its interactive API page is at `http://127.0.0.1:8001/docs`. Start Streamlit in a second terminal; `API_BASE_URL` defaults to `http://127.0.0.1:8001`. Stop a running process with **Ctrl+C** in its terminal.

## Troubleshooting

| Symptom | What to try |
|---|---|
| Copilot Chat is missing | Install/enable the extensions and sign in with an account that has access. |
| `uv` is not recognized | Reopen the VS Code terminal after installation; if needed, follow the official uv installer instructions. |
| The AI tries to implement multiple phases | Ask it to stop, list the changes, and return to the single current phase. |
| Gemini configuration is missing | Check `.env` in the project root and restart the API. Never paste the key into chat. |
| The server command fails | Share the error without secrets and ask the assistant to explain it before editing files. |

