# 🌬️ Air Quality Tracker

A command-line tool that fetches real-time and historical air quality data from the **OpenAQ API** and compares readings against **WHO Air Quality Guidelines (2021)**. Tracks PM2.5, PM10, NO₂, O₃, CO, and SO₂ with AQI scoring.

## Features

- Fetches live data from OpenAQ — an open-source platform aggregating air quality data worldwide
- Calculates US AQI from PM2.5 concentrations
- Compares all pollutants against WHO 2021 daily limits
- Visual progress bars showing % of WHO threshold reached
- Exports JSON reports for further analysis
- Demo mode with realistic sample data (no API key needed)

## Demo

```
══════════════════════════════════════════════════════════════════════
  🌬️  AIR QUALITY TRACKER
  Location: Halifax (demo)  |  Period: Last 7 days  |  2024-11-01
══════════════════════════════════════════════════════════════════════

  🟢  Overall AQI (PM2.5 based): 42 — Good
      Air quality is satisfactory.

  ✅ PM2.5 (Fine Particles)
     Mean: 8.4 µg/m³  |  Min: 0.2  |  Max: 28.1  |  n=168
     [█████████████░░░░░░░░░░░░░░░░░] 56% of WHO daily limit (15.0 µg/m³)

  ✅ Nitrogen Dioxide (NO₂)
     Mean: 12.3 µg/m³  |  Min: 1.1  |  Max: 41.7  |  n=168
     [████████████████████░░░░░░░░░░] 49% of WHO daily limit (25.0 µg/m³)
```

## Installation

No external dependencies — uses Python standard library only.

```bash
git clone https://github.com/parkersarris/air-quality-tracker
cd air-quality-tracker
python tracker.py
```

## Usage

```bash
# Run demo with sample data
python tracker.py

# Fetch live data for Halifax
python tracker.py --city "Halifax"

# Analyze 14 days and export
python tracker.py --city "Toronto" --days 14 --export report.json

# List example cities
python tracker.py --list-cities
```

## Pollutants Tracked

| Pollutant | WHO Daily Limit | Unit |
|-----------|----------------|------|
| PM2.5 | 15 µg/m³ | µg/m³ |
| PM10 | 45 µg/m³ | µg/m³ |
| NO₂ | 25 µg/m³ | µg/m³ |
| O₃ | 100 µg/m³ | µg/m³ |
| CO | 4,000 µg/m³ | µg/m³ |
| SO₂ | 40 µg/m³ | µg/m³ |

Guidelines sourced from [WHO Global Air Quality Guidelines (2021)](https://www.who.int/publications/i/item/9789240034228).

## Data Source

[OpenAQ](https://openaq.org/) — an open-source platform providing access to air quality data from government monitoring stations around the world.

## Background

Built as a personal project exploring the intersection of environmental monitoring and open data. Motivated by coursework in Environmental Engineering at Dalhousie University.
