# AI-generated fixes experiment

Goal: test the verifier on fixes produced by real AI tools, not written by hand.

## Inputs

`inputs/a01.py` to `inputs/a08.py`: eight vulnerable Python files (the same code as the "before" side of the hand-built cases). `cases.csv` lists each case and the Bandit test ID the fix should remove (the target).

## Procedure (same for every case and every tool)

1. Open a **new chat** (no earlier messages).
2. Paste the prompt from `prompt.txt`, then a blank line, then the full content of the input file.
3. Copy the code block from the reply **exactly as it is**. Do not edit it, even if it looks wrong.
4. Save it as `outputs/<tool>/<case>.py`, for example `outputs/gemini/a01.py`.
5. Fill in one row in `log.csv`: the model name shown by the tool, the date, and a short note (for example "also removed the password", or "reply had no code block").

Tools:
- `gemini`: Gemini app (Google AI Pro, student plan). Write the model name exactly as the app shows it.
- `copilot`: GitHub Copilot Chat in VS Code. Write the model name shown in the chat model picker.

If a tool refuses or gives no code, write that in `notes` and leave the output file out.
