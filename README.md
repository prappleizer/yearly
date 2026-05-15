# YearView

A year-at-a-glance calendar for planning travel and major events. Designed to complement detailed calendars like Google Calendar by giving you a big-picture overview.

## Features

- **Multi-zoom view**: See 1, 2, 4, 6, or 12 months at once
- **Infinite scroll**: Navigate through time seamlessly
- **Quick navigation**: Jump to any month with the mini-map navigator
- **Event creation**: Click and drag to select date ranges, or right-click for context menu
- **Shift+click**: Select start and end dates across month boundaries
- **Tags**: Organize events with color-coded tags
- **Travel tracking**: Mark events as "in-town" or "travel/out of town"
- **Preliminary events**: Mark tentative events (shown translucent)
- **Conflict detection**: Highlights days with both in-town and travel events
- **Statistics**: See travel days and tag breakdowns in the sidebar
- **Filtering**: Toggle visibility by tag or travel status
- **Export**: Export your year as a text agenda

## Quick Start

```bash
# Install dependencies
npm install

# Start the server
npm start

# Or with auto-reload during development
npm run dev
```

Then open http://localhost:3000 in your browser.

## Usage

### Creating Events

1. **Click and drag** on the calendar to select a date range
2. **Right-click** on any day and choose "New Event"
3. **Shift+click** two dates to select a range (useful across month boundaries)

### Navigating

- Use the **zoom buttons** (1mo, 2mo, etc.) to change how many months are visible
- **Scroll** up/down to move through time
- Use the **mini-map** in the top-right to jump to any month
- Click **Today** to return to the current date

### Managing Tags

- Click **+ Add** in the Tags section to create new tags
- Click the **pencil icon** on a tag to edit or delete it
- Use **checkboxes** to show/hide events with specific tags

### Filtering

- Toggle **Travel/Out of town** to show/hide travel events
- Toggle **In town** to show/hide local events
- Toggle **Preliminary events** to show/hide tentative plans

### Export

Click **Export Year as Text** to download a plain-text agenda of all events for the currently selected year.

## Data Storage

Data is stored in `data/yearview.db` (SQLite database). This file is created automatically on first run.

## Tech Stack

- **Backend**: Node.js + Express
- **Database**: SQLite (via sql.js)
- **Frontend**: Alpine.js + Tailwind CSS (via CDN)

## File Structure

```
yearview/
├── src/
│   ├── server.js      # Express server and API routes
│   └── db/
│       └── index.js   # Database initialization and helpers
├── public/
│   └── index.html     # Single-page application
├── data/
│   └── yearview.db    # SQLite database (created on first run)
└── package.json
```
