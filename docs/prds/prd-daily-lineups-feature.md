# PRD: Daily Lineups Feature

*Synced from Notion on 2025-08-03 15:18:16*

*Page ID: 2431a736-211e-81a9-9b13-d36af56b4da8*

---

**Author:** Senior Product Manager

**Date:** August 2, 2025

**Status:** Implemented

**Version:** 1.0

---

## Executive Summary

The Daily Lineups feature will provide comprehensive historical roster analysis capabilities for fantasy baseball managers. By ingesting and processing daily roster data from Yahoo Fantasy Baseball, this feature will enable users to discover patterns, optimize lineup decisions, and gain competitive insights from historical lineup data across their league.

## Problem Statement

### Current State

- Managers lack visibility into historical lineup decisions and patterns

- No systematic way to analyze opponent lineup tendencies

- Unable to identify optimal roster utilization strategies

- Missing insights on bench usage and player deployment

### Desired State

- Complete historical record of daily lineups for all teams

- Analytical tools to identify patterns and trends

- Actionable insights for roster optimization

- Competitive intelligence on opponent strategies

## User Personas

### Primary: Active Fantasy Manager

- **Goals:** Optimize daily lineup decisions, gain competitive edge

- **Pain Points:** Time-consuming manual tracking, lack of historical context

- **Needs:** Quick insights, pattern recognition, strategic recommendations

### Secondary: League Analyst

- **Goals:** Understand league-wide trends, create content/reports

- **Pain Points:** Fragmented data, manual compilation

- **Needs:** Comprehensive data access, visualization tools

## Feature Overview

### Core Capabilities

1. **Historical Lineup Viewer**

1. **Player Usage Analytics**

1. **Team Strategy Insights**

1. **Comparative Analysis**

1. **Search & Discovery**

## User Stories

### Must Have (P0)

1. **As a manager, I want to view any team's lineup for any past date** so that I can understand their roster decisions.

1. **As a manager, I want to see a player's start/sit history** so that I can identify usage patterns.

### Should Have (P1)

1. **As a manager, I want to see optimal lineup analysis** so that I know if I left points on the bench.

1. **As a manager, I want to export lineup data** so that I can perform custom analysis.

### Nice to Have (P2)

1. **As a manager, I want lineup recommendations** based on historical patterns.

1. **As a manager, I want to see weather impact** on lineup decisions.

## Technical Requirements

### Data Ingestion

1. **API Integration**

1. **Data Processing**

1. **Storage Schema**

1. **Performance Requirements**

### UI/UX Requirements

1. **Navigation**

1. **Key Views**

1. **Interactive Elements**

1. **Mobile Considerations**

## Visual Mockups

### 1. Main Daily Lineups View

The primary interface shows a grid of team lineups for any selected date. Key features:

- Date picker and team filter controls

- Grid layout showing all team lineups side-by-side

- Visual indicators for new additions (green "NEW" badge)

- Player status badges (DTD, IL)

- Bench section clearly separated

- Actual game performance shown inline

### 2. Player Usage Timeline

Individual player usage patterns over time:

- Start rate percentages and splits (vs LHP/RHP)

- Visual timeline showing started (green) vs benched (red) days

- Usage statistics summary cards

- Filterable by date range and team ownership

### 3. Search and Discovery

Powerful search interface:

- Player name autocomplete

- Position-based filtering

- Quick access to usage history

- Export functionality for detailed analysis

### 4. Full Season Timeline View

Player usage patterns across the entire season with performance metrics:

- Row-based timeline showing March through October

- Visual segments for Started, Benched, On Another Roster, Not Owned, and Injured statuses

- Aggregate performance statistics for each usage status

- Progressive display that expands as season progresses

- Hover tooltips with specific dates and context

[Interactive mockups available in the attached HTML artifact showing detailed UI/UX flows]

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Lineups Mockups</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .mockup-section {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 40px;
            padding: 30px;
        }
        h1 {
            color: #1a1a1a;
            margin-bottom: 40px;
        }
        h2 {
            color: #2c3e50;
            margin-bottom: 20px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        .mockup {
            border: 2px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            background: #fafafa;
        }
        .nav-bar {
            background: #2c3e50;
            color: white;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            display: flex;
            gap: 20px;
            align-items: center;
        }
        .nav-item {
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
        }
        .nav-item.active {
            background: #3498db;
        }
        .controls {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .control-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        select, input[type="date"] {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .lineup-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .lineup-card {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            background: white;
        }
        .lineup-card h3 {
            margin: 0 0 15px 0;
            color: #2c3e50;
            font-size: 18px;
        }
        .position-row {
            display: flex;
            justify-content: space-between;
            padding: 8px;
            border-bottom: 1px solid #f0f0f0;
            align-items: center;
        }
        .position-row:last-child {
            border-bottom: none;
        }
        .position {
            font-weight: bold;
            color: #666;
            width: 40px;
        }
        .player-name {
            flex: 1;
            color: #333;
        }
        .player-stats {
            font-size: 12px;
            color: #888;
        }
        .bench-section {
            margin-top: 20px;
            padding-top: 15px;
            border-top: 2px solid #e0e0e0;
        }
        .bench-title {
            font-weight: bold;
            color: #666;
            margin-bottom: 10px;
        }
        .badge {
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
            margin-left: 8px;
        }
        .[badge.new](http://badge.new/) {
            background: #27ae60;
            color: white;
        }
        .badge.dtd {
            background: #f39c12;
            color: white;
        }
        .timeline {
            display: flex;
            gap: 2px;
            margin-top: 10px;
            height: 40px;
            align-items: center;
        }
        .timeline-day {
            width: 20px;
            height: 20px;
            border-radius: 3px;
            cursor: pointer;
        }
        .timeline-day.started {
            background: #27ae60;
        }
        .timeline-day.benched {
            background: #e74c3c;
        }
        .timeline-day.not-owned {
            background: #ddd;
        }
        .player-usage-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            margin-bottom: 20px;
        }
        .usage-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .stat-box {
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #3498db;
        }
        .stat-label {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
        .comparison-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        .vs-divider {
            text-align: center;
            font-size: 24px;
            font-weight: bold;
            color: #666;
            margin: 20px 0;
        }
        .highlight {
            background: #fff3cd;
        }
        .filter-pills {
            display: flex;
            gap: 8px;
            margin-top: 10px;
        }
        .pill {
            padding: 6px 12px;
            border-radius: 20px;
            background: #e9ecef;
            font-size: 12px;
            cursor: pointer;
        }
        .pill.active {
            background: #3498db;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Daily Lineups Feature - Visual Mockups</h1>

        <!-- Mockup 1: Main Daily Lineups View -->
        <div class="mockup-section">
            <h2>1. Main Daily Lineups View</h2>
            <div class="mockup">
                <div class="nav-bar">
                    <div class="nav-item">Transactions</div>
                    <div class="nav-item active">Daily Lineups</div>
                    <div class="nav-item">Matchups</div>
                    <div class="nav-item">Standings</div>
                </div>
                
                <div class="controls">
                    <div class="control-group">
                        <label>Date:</label>
                        <input type="date" value="2025-06-15">
                    </div>
                    <div class="control-group">
                        <label>Team:</label>
                        <select>
                            <option>All Teams</option>
                            <option>Bash Brothers</option>
                            <option>Diamond Dynasty</option>
                            <option>Homer's Heroes</option>
                        </select>
                    </div>
                    <div class="control-group">
                        <label>View:</label>
                        <select>
                            <option>Grid View</option>
                            <option>List View</option>
                            <option>Compare View</option>
                        </select>
                    </div>
                </div>

                <div class="lineup-grid">
                    <div class="lineup-card">
                        <h3>Bash Brothers</h3>
                        <div class="position-row">
                            <span class="position">C</span>
                            <span class="player-name">Will Smith</span>
                            <span class="player-stats">2-4, HR, 3 RBI</span>
                        </div>
                        <div class="position-row">
                            <span class="position">1B</span>
                            <span class="player-name">Freddie Freeman</span>
                            <span class="player-stats">3-5, 2B, 2 R</span>
                        </div>
                        <div class="position-row">
                            <span class="position">2B</span>
                            <span class="player-name">Ozzie Albies</span>
                            <span class="player-stats">1-4, SB</span>
                        </div>
                        <div class="position-row">
                            <span class="position">3B</span>
                            <span class="player-name">Manny Machado <span class="badge new">NEW</span></span>
                            <span class="player-stats">2-4, HR, 2 RBI</span>
                        </div>
                        <div class="position-row">
                            <span class="position">SS</span>
                            <span class="player-name">Bo Bichette</span>
                            <span class="player-stats">0-3, BB</span>
                        </div>
                        <div class="position-row">
                            <span class="position">OF</span>
                            <span class="player-name">Ronald Acuña Jr.</span>
                            <span class="player-stats">4-5, 2 HR, 5 RBI</span>
                        </div>
                        <div class="position-row">
                            <span class="position">OF</span>
                            <span class="player-name">Juan Soto</span>
                            <span class="player-stats">2-3, 2 BB</span>
                        </div>
                        <div class="position-row">
                            <span class="position">OF</span>
                            <span class="player-name">Kyle Tucker</span>
                            <span class="player-stats">1-4, RBI</span>
                        </div>
                        <div class="position-row">
                            <span class="position">UTIL</span>
                            <span class="player-name">Yordan Alvarez</span>
                            <span class="player-stats">3-4, 2B, 2 RBI</span>
                        </div>
                        
                        <div class="bench-section">
                            <div class="bench-title">BENCH</div>
                            <div class="position-row">
                                <span class="position">B</span>
                                <span class="player-name">Mike Trout <span class="badge dtd">DTD</span></span>
                                <span class="player-stats">Did not play</span>
                            </div>
                            <div class="position-row">
                                <span class="position">B</span>
                                <span class="player-name">Marcus Semien</span>
                                <span class="player-stats">2-4, HR, 2 RBI</span>
                            </div>
                        </div>
                    </div>

                    <div class="lineup-card">
                        <h3>Diamond Dynasty</h3>
                        <div class="position-row">
                            <span class="position">C</span>
                            <span class="player-name">Salvador Perez</span>
                            <span class="player-stats">1-3, RBI</span>
                        </div>
                        <div class="position-row">
                            <span class="position">1B</span>
                            <span class="player-name">Vladimir Guerrero Jr.</span>
                            <span class="player-stats">2-5, 2B</span>
                        </div>
                        <!-- Additional players... -->
                    </div>
                </div>
            </div>
        </div>

        <!-- Mockup 2: Player Usage Timeline -->
        <div class="mockup-section">
            <h2>2. Player Usage Timeline View</h2>
            <div class="mockup">
                <div class="player-usage-card">
                    <h3>Mike Trout - Usage Analysis</h3>
                    <div class="usage-stats">
                        <div class="stat-box">
                            <div class="stat-value">72%</div>
                            <div class="stat-label">Start Rate When Healthy</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">85%</div>
                            <div class="stat-label">Start Rate vs LHP</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">OF</div>
                            <div class="stat-label">Primary Position</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">12</div>
                            <div class="stat-label">Bench Decisions</div>
                        </div>
                    </div>
                    
                    <h4 style="margin-top: 30px;">June 2025 Start/Sit Pattern</h4>
                    <div class="timeline">
                        <div class="timeline-day started" title="June 1 - Started"></div>
                        <div class="timeline-day started" title="June 2 - Started"></div>
                        <div class="timeline-day benched" title="June 3 - Benched"></div>
                        <div class="timeline-day started" title="June 4 - Started"></div>
                        <div class="timeline-day started" title="June 5 - Started"></div>
                        <div class="timeline-day benched" title="June 6 - Benched (DTD)"></div>
                        <div class="timeline-day benched" title="June 7 - Benched (DTD)"></div>
                        <div class="timeline-day started" title="June 8 - Started"></div>
                        <div class="timeline-day started" title="June 9 - Started"></div>
                        <div class="timeline-day started" title="June 10 - Started"></div>
                        <div class="timeline-day started" title="June 11 - Started"></div>
                        <div class="timeline-day benched" title="June 12 - Benched"></div>
                        <div class="timeline-day started" title="June 13 - Started"></div>
                        <div class="timeline-day started" title="June 14 - Started"></div>
                        <div class="timeline-day started" title="June 15 - Started"></div>
                    </div>
                    <div style="margin-top: 10px; font-size: 12px; color: #666;">
                        Legend: <span style="color: #27ae60;">■ Started</span> | <span style="color: #e74c3c;">■ Benched</span> | <span style="color: #ddd;">■ Not Owned</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Mockup 3: Head-to-Head Comparison -->
        <div class="mockup-section">
            <h2>3. Head-to-Head Lineup Comparison</h2>
            <div class="mockup">
                <h3 style="text-align: center;">Week 10 Matchup - June 15, 2025</h3>
                
                <div class="comparison-container">
                    <div class="lineup-card">
                        <h3>Bash Brothers</h3>
                        <div class="position-row highlight">
                            <span class="position">C</span>
                            <span class="player-name">Will Smith</span>
                            <span class="player-stats">2-4, HR, 3 RBI</span>
                        </div>
                        <div class="position-row">
                            <span class="position">1B</span>
                            <span class="player-name">Freddie Freeman</span>
                            <span class="player-stats">3-5, 2B, 2 R</span>
                        </div>
                        <!-- Additional positions... -->
                        <div class="bench-section">
                            <div class="bench-title">KEY BENCH DECISION</div>
                            <div class="position-row" style="background: #ffe6e6;">
                                <span class="position">B</span>
                                <span class="player-name">Marcus Semien</span>
                                <span class="player-stats">2-4, HR, 2 RBI</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="lineup-card">
                        <h3>Diamond Dynasty</h3>
                        <div class="position-row">
                            <span class="position">C</span>
                            <span class="player-name">Salvador Perez</span>
                            <span class="player-stats">1-3, RBI</span>
                        </div>
                        <div class="position-row highlight">
                            <span class="position">1B</span>
                            <span class="player-name">Vladimir Guerrero Jr.</span>
                            <span class="player-stats">4-5, 2 HR, 5 RBI</span>
                        </div>
                        <!-- Additional positions... -->
                    </div>
                </div>
                
                <div class="vs-divider">Categories Won: 6-4 (Bash Brothers)</div>
            </div>
        </div>

        <!-- Mockup 4: Search and Filter Interface -->
        <div class="mockup-section">
            <h2>4. Search and Discovery Interface</h2>
            <div class="mockup">
                <div style="margin-bottom: 20px;">
                    <input type="text" placeholder="Search for a player..." style="width: 300px; padding: 10px; font-size: 16px;">
                </div>
                
                <div class="filter-pills">
                    <div class="pill active">All Positions</div>
                    <div class="pill">C</div>
                    <div class="pill">1B</div>
                    <div class="pill">2B</div>
                    <div class="pill">3B</div>
                    <div class="pill">SS</div>
                    <div class="pill">OF</div>
                    <div class="pill">SP</div>
                    <div class="pill">RP</div>
                </div>
                
                <h4 style="margin-top: 20px;">Search Results: "Trout"</h4>
                <div class="player-usage-card">
                    <h4>Mike Trout - Bash Brothers</h4>
                    <div style="font-size: 14px; color: #666;">
                        Last Started: June 15, 2025 | Start Rate: 72% | Primary: OF
                    </div>
                    <div style="margin-top: 10px;">
                        <button style="padding: 8px 16px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer;">View Full Usage History</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
```

## Implementation Phases

### Phase 1: MVP (4 weeks)

- Basic lineup viewer

- Date/team navigation

- Current season data only

### Phase 2: Analytics (3 weeks)

- Player usage patterns

- Start/sit percentages

- Basic search functionality

### Phase 3: Advanced Features (4 weeks)

- Historical backfill

- Optimal lineup analysis

- Export capabilities

### Phase 4: Intelligence (3 weeks)

- Pattern detection

- Recommendations engine

## Risks & Mitigations

[Unsupported block type: table]

## Dependencies

- Yahoo Fantasy API access

- Authentication system

- Database infrastructure

- MLB data integration (pybaseball)

- Frontend framework (Node.js)

## Open Questions

1. How far back should historical data go? (All available years vs last 5)

1. Should we store projected lineups or only actual?

1. Integration with existing transaction data?

1. Real-time updates during games?

## Appendix

### Competitive Analysis

- FantasyPros: Limited historical lineup data

- Baseball Monster: Focus on current season only

- Razzball: Manual tracking tools only

### Data Sources

- Primary: Yahoo Fantasy Sports API

- Secondary: MLB Stats API (for player status)

- Tertiary: Weather APIs (future enhancement)
