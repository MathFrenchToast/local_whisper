# Local Server Setup & LLM Integration

This document explains how to configure and run the local ASR server with the optional LLM post-processing layer.

## 1. Prerequisites

- **ASR Server**: Ensure you have installed the requirements (`pip install -r requirements.txt`).
- **Ollama**: To use local LLM processing, install Ollama from [ollama.com](https://ollama.com).

## 2. Configuring Ollama

To use Ollama with this project, you need to pull a compatible model. We recommend `llama3` or `mistral`.

```bash
# Pull the model
ollama pull llama3
```

The API will be available at `http://localhost:11434/v1` by default, which is compatible with the OpenAI format used by this project.

## 3. Running the Server with LLM

To enable the LLM cleaning step, you must set the `LLM_ENABLED` environment variable to `true`.

### Basic Command (Ollama)
```bash
LLM_ENABLED=true LLM_MODEL=llama3 ./start_server.sh
```

### Advanced Configuration
You can customize the connection using environment variables:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `LLM_ENABLED` | Enable/Disable LLM post-processing | `false` |
| `LLM_URL` | Base URL for the LLM API | `http://localhost:11434/v1` |
| `LLM_MODEL` | Model name to use | `llama3` |
| `LLM_API_KEY` | API Key (use 'ollama' for local) | `ollama` |

**Example for OpenAI (Cloud):**
```bash
LLM_ENABLED=true \
LLM_URL=https://api.openai.com/v1 \
LLM_API_KEY=sk-your-key \
LLM_MODEL=gpt-4o \
./start_server.sh
```

## 4. Customizing the Prompt

The LLM behavior is controlled by `system_prompt.txt` at the root of the project. You can modify this file to:
- Change the transcription cleaning rules.
- Add or remove specific punctuation commands.
- Translate the output automatically.

If the file does not exist, a default internal prompt is used.

## 5. Troubleshooting

- **Server is slow**: LLM processing adds latency. Using a smaller model (like `phi3` or `tinyllama`) or a GPU will improve response times.
- **Connection Error**: Ensure Ollama is running (`ollama serve`) and the `LLM_URL` is correct.
- **No changes in text**: Check the server logs to see if the LLM is correctly called or if it's falling back to original text due to an error.
