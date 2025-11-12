
# Getting Started
It's recommended to run this repository in GitHub Codespaces (in GitHub, press the green 'Code' button and then Codespaces). If you prefer to work in VS Code or another IDE, you need to manually run these commands:

```
pip install -U pip uv
uv venv
source .venv/bin/activate
uv pip install --extra-index-url https://europe-west3-python.pkg.dev/rasa-releases/rasa-pro-python/simple rasa-pro
uv pip install -r requirements.txt
```

Create a file called `.env` containing your license key:
```
RASA_LICENSE=<the Rasa license key you received when creating your developer account>
```

---

## Installation
**Train the Rasa model**

   ```bash
   rasa train
   ```

---

## Running the Application

You can run the application in two ways:

### Option 1: Using the convenience script

```bash
./run.sh
```

This script will:

- Start the Rasa server with proper CORS settings on port 5005
- Start the Flask server (frontend) on port 5000
- Press `Ctrl+C` to stop both servers

### Option 2: Starting servers manually

1. **Start the Flask server**

   ```bash
   python app.py
   ```

2. **Start the Rasa server (in a separate terminal)**

   ```bash
   rasa run --enable-api --cors "*"
   ```

   > **IMPORTANT**: The `--cors "*"` parameter is essential for the frontend to communicate with the Rasa API. Without it, you'll encounter CORS errors in your browser.

3. **Access the application**

   Open your browser and navigate to `<your-codespace-id-xxxxx>-5000.app.github.dev` if you are running the app in Github codespaces, or `http://localhost:5000` if you are running it locally.

---
