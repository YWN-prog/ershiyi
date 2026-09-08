# AGENTS.md

This document is intended for AI agents and human collaborators working in this repository. It describes the project overview and the working conventions that must be followed.

## Project Overview

**QzoneArchive (空间归档)** is a cross-platform desktop / mobile tool that securely archives QQ Zone feeds, photos, videos, and interaction records to the local machine.

- **Tech Stack**: Tauri 2 + Rust backend; Vue 3 + TypeScript + Vite + PrimeVue 4 + Pinia frontend; SQLite local storage
- **Core Features**: Complete archiving (own feeds / friend feeds / messages), resumable transfer, rate protection, interaction restoration, HTML export, media timeline, dark mode
- **Target Platforms**: Windows / macOS / Linux desktop + Android mobile
- **License**: GPLv3

## Architecture

### Data Source

Archiving is based on QQ Zone's **mobile interaction list API** (`mobile.qzone.qq.com/get_feeds`). This endpoint returns all interaction notifications for the current account — including new feeds posted by friends, likes, comments, replies, and messages. The application extracts the original feed content from these notifications and stores it in the local database.

**Feeds that have never been liked or commented on cannot be recovered**, because they never appear in the interaction list.

### Login Methods

- **QR Code Login**: Invokes QQ Zone's mobile scan-to-login flow; never touches the password.
- **Web Login** (desktop only): Opens an independent window loading the QQ login page, then extracts login credentials via the WebView Cookie API.

Login credentials (cookies) are stored **only in the Rust backend memory** and are never written to the console or logs.

### Project Structure

```
├── src/                    # Vue frontend
│   ├── views/              # Page components
│   │   ├── DashboardView   # Overview (stats + interaction ranking)
│   │   ├── ArchivesView    # Archived content (browse by category, search, export)
│   │   ├── MediaView       # Media timeline
│   │   ├── TasksView       # Archiving tasks
│   │   ├── SettingsView    # Settings
│   │   ├── ContactsView    # Contacts
│   │   ├── QzoneView       # QQ Zone view
│   │   └── RecycleBinView  # Recycle bin
│   ├── components/         # Reusable components
│   ├── stores/             # Pinia state management
│   ├── utils/              # Utility functions and types
│   ├── layouts/            # Layout components
│   ├── router/             # Vue Router configuration
│   └── styles/             # Global styles
├── src-tauri/              # Rust backend
│   └── src/
│       ├── main.rs         # Entry point
│       ├── lib.rs          # Tauri command registration
│       ├── qlogin.rs       # QQ login (QR code + web)
│       ├── qzone.rs        # QQ Zone API client
│       └── archive.rs      # Archiving engine + database
└── src-tauri/capabilities/ # Tauri permission configuration
```

