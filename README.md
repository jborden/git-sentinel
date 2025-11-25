# Site Reliability Agent

## Prerequisites

- Conda (installed via Miniconda or Anaconda)
- Ollama (for local LLM inference)
- Langfuse (for tracing)


## Step 0: Run Langfuse

Clone the latest langfuse (in another dir)
```
git clone https://github.com/langfuse/langfuse
```

Run langfuse
```
cd langfuse
docker-compose up
```

Go and setup an org and project. Generate api keys and place them in the
`.env`. The agent will read the auth from this

## Step 1: Install Ollama and Conda

```
brew install miniconda
```
note: This will take some time 

Download and install from [ollama.ai](https://ollama.ai)

Then pull the Mistral model:
```bash
ollama pull qwen3-coder:30b
```

Start Ollama (it runs as a background service):
```bash
ollama serve
```

This will start Ollama on `http://localhost:11434`. Keep this running in a separate terminal.

## Step 2: Create Conda Environment

```bash
conda env create -f environment.yml
conda activate git-sentinel
```

## Step 3: Verify Setup

Test that everything is connected:

```bash
python -c "from langchain_community.llms import Ollama; llm = Ollama(model='qwen3-coder:30b'); print(llm.invoke('Say hello'))"
```

You should see: `Hello!` (or similar)

If this fails, make sure Ollama is running with `ollama serve` in another terminal.

## Step 4: Run the "services" scripts

Create a repo e.g. `sentinel_test_repo`

```
mkdir sentinel_test_repo
cd sentinel_test_repo
git init .
```

point the sentinel at it:
```
./sentinel_cli.py ../sentinel_test_repo
```

# Step 5: Make some changes to the repo

First, add these to your `.gitignore`, this will prevent git from commiting
the artifacts made by this tool.

```
*.__quarantined__
REMEDIATION_*.md
```

The agent will:
1. Monitor the git repo
2. Isolate an offending file and place it in: <filename>.__quarantined__
3. Come up with a remediation plan and place in REMEDIATION_<filename>.md

### Test cases

Create a repo e.g. `sentinel_test_repo`

#### AWS Credentials
Copy something like:
```python
# Database Configuration
# DO NOT COMMIT THIS FILE

db_host = "prod-db.example.com"
db_port = 5432
db_user = "admin"

# TODO: Move this to environment variables later
aws_access_key_id = "AKIAIOSFODNN7EXAMPLE" 
aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

Into a file like `database_config.py`. The file will be quarantined and a remediation
plan will be given.

#### Data privacy violation

Copy this into `marketing_export.csv`
```
id,first_name,last_name,email,status
101,John,Doe,john.doe@example.com,active
102,Jane,Smith,jane.smith@test-company.org,inactive
103,Bob,Jones,bjones1985@gmail.com,active
104,Alice,Wong,alice.wong@university.edu,active
105,Charlie,Brown,cbrown@peanuts.net,pending
```

#### Private Key
Copy this into `server_backup.key`
```
-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDwy+5...
(This is a fake key block for testing purposes)
...ab8384hsu382928374h3847
-----END PRIVATE KEY-----
```




# Structure

```
.
├── environment.yml              # Conda environment definition
├── auth_service.py              # Writes to auth_service.log
├── db_service.py                # Writes to db_service.log
├── sre_agent.py                 # The actual agent
├── sre_tools.py                 # Tools available to the agent
├── sre_cli.py                   # Wrapper for running the agent
└── README.md                    # This file
```

# Debugging

Tracing is done through langfuse. If the service is running, you 
can view at http://localhost:3000

## Troubleshooting

**"Cannot connect to Ollama"**
- Make sure Ollama is running: `ollama serve` in a separate terminal

**"mistral: model not found"**
- Pull the model: `ollama pull qwen3-coder:30b`

**Tool execution errors**
- Check the generated script for syntax errors
- Some tools may require specific permissions on your system
- Use `--no-dry-run` carefully on first attempts

**Agent generates weird plans**
- This is normal! The model is learning. Try rephrasing your request.
- The agent improves with larger models. Consider `ollama pull neural-chat` for more reasoning.

## Next Steps

### Extending the Agent

Add new tools by creating functions decorated with `@tool`:
```python
@tool
def my_new_tool(arg: str) -> str:
    """Description of what this tool does."""
    # implementation
    return result
```

Then add it to `create_tools_list()`.

### Using Different Models

Edit `.py` and change the model:
```python
llm = ChatOllama(model="neural-chat", temperature=0.3)
```
See [ollama.ai/library](https://ollama.ai/library) for options.

## Performance Tips

- The first run is slowest (model loading). Subsequent runs are faster.
- Larger models think better but are slower. `qwen3-coder:30b` is a good balance.
- For faster iteration during development, use smaller models like `orca-mini`.
- Tool results over 500 chars are truncated to keep context size down.
