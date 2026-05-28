Health Assistant Setup Guide

<!-- Create a virtual python environment -->
uv python pin 3.11.8
uv venv
source .venv/bin/activate

<!-- Create db command for first run -->
createdb health_assistant

<!-- How to set it up -->
uv pip install -r requirements.txt


Create a .env file in healthassistant/ and add .env in .gitignore

<!-- Install Homebrew -->
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

<!-- Install postgres -->
brew install postgresql@16
brew services start postgresql@16
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
createdb health_assistant

<!-- Add DATABASE URL -->
DATABASE_URL=postgresql+psycopg2://anshulkansal@localhost:5432/health_assistant

.venv/bin/uvicorn app.main:app --reload