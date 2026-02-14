# Rito Dashboard

Web-based management interface for Rito AI V2.0.

## Features

- 📊 **Dashboard**: System overview with metrics
- 🧠 **Persona Editor**: Edit system prompts and personalities
- 📜 **History Viewer**: Browse memories, actions, and logs
- 👥 **Relationship Manager**: Manage user relationships and notes
- 🔍 **Search**: Search across all logs and memories
- ⚙️ **Settings**: Configuration management (coming soon)

## Usage

### Starting the Dashboard

```powershell
cd c:/Users/nobuk/Desktop/新しいフォルダー
streamlit run dashboard/app.py
```

The dashboard will open in your browser at `http://localhost:8501`

### Key Functions

#### Persona Editor
- Select and edit AI personalities
- Update system prompts in real-time
- Activate/deactivate personas

#### Relationship Manager
- View all registered users
- Adjust relationship levels (0-100)
- Set relationship types (master, friend, stranger, etc.)
- Edit AI-generated notes about each user

#### Search
- Search across memories, action logs, and master actions
- Filter by table type
- View timestamped results

#### Settings
- **API Configuration**: Edit Discord Bot Token, Ollama URL, Bluesky credentials
- **Database Management**: Clear logs (with confirmation)
- **.env Editor**: GUI for environment variables

#### Diagnostics
- **System Health Check**: Test all components (Database, Ollama, Adapters)
- **Status Indicators**: Visual ✅/❌ for each component
- **Fix Suggestions**: Automatic troubleshooting tips

## Requirements

Already included in `requirements.txt`:
- streamlit>=1.30.0
- pandas>=2.0.0
