# PRD: GKL Rule Committee Module

*Synced from Notion on 2025-08-03 15:18:11*

*Page ID: 2441a736-211e-81e9-bba1-d8a0f0218360*

---

**Author:** Senior Product Manager

**Date:** August 3, 2025

**Status:** Draft

**Version:** 1.0

## Executive Summary

The GKL Rule Committee module will provide automated monitoring and enforcement capabilities for custom league rules that cannot be enforced by Yahoo Fantasy Baseball's platform. This feature will systematically track potential rule violations, alert the commissioner to investigate, and maintain an audit trail of enforcement actions. By automating the detection of violations for rules like keeper eligibility, IL use, next year keeper values, keeper selection and nomination, and NA roster compliance this module will ensure fair play and reduce the administrative burden on the commissioner while maintaining the integrity of our unique league structure.

## Problem Statement

### Current State

- Manual tracking of custom rules relies on "honor system and peer accountability"

- No systematic way to detect rule violations

- Commissioner must manually review all transactions and roster moves

- No audit trail of rule enforcement decisions

- Disputes arise from inconsistent enforcement or missed violations

- Time-consuming manual verification of keeper eligibility

### Desired State

- Automated detection of potential rule violations

- Real-time alerts to commissioner for investigation

- Comprehensive audit trail of all enforcement actions

- Clear visibility of custom rules for all managers

- Consistent and transparent rule enforcement

- Historical record of violations and resolutions

## User Personas

### Primary: League Commissioner

**Goals:** Enforce rules fairly and consistently with minimal manual effort

**Pain Points:** Time-consuming manual reviews, missing violations, handling disputes

**Needs:** Automated alerts, investigation tools, decision logging

### Secondary: League Managers

**Goals:** Understand rules clearly, avoid violations, ensure fair play

**Pain Points:** Unclear about custom rules, inconsistent enforcement

**Needs:** Rule visibility, violation notifications, enforcement transparency

### Tertiary: League Analyst

**Goals:** Track rule compliance trends, identify problematic patterns

**Pain Points:** No historical data on violations

**Needs:** Violation analytics, pattern identification

## Feature Overview

### Core Capabilities

1. **Rule Definition System** - Codify all custom GKL rules

1. **Violation Detection Engine** - Automated monitoring of league activity

1. **Commissioner Dashboard** - Alert center and investigation tools

1. **Enforcement Logging** - Track decisions and outcomes

1. **Manager Notifications** - Alerts for violations and resolutions

1. **Rule Reference Center** - Easy access to all custom rules

## User Stories

### Must Have (P0)

- As a commissioner, I want to receive alerts when a potential rule violation occurs so that I can investigate promptly

- As a commissioner, I want to log the outcome of rule violation investigations so that I maintain an audit trail

- As a manager, I want to view all custom league rules so that I can ensure compliance

- As a commissioner, I want automated detection of keeper eligibility violations so that I don't have to manually verify each keeper

### Should Have (P1)

- As a commissioner, I want to see a history of all rule violations and resolutions so that I can ensure consistent enforcement

- As a commissioner, I want to export violation reports so that I can share with the league

- As a commissioner, I want to track patterns of violations by manager so that I can identify repeat offenders

### Nice to Have (P2)

- As a manager, I want to see my compliance score so that I know how well I follow rules

- As a commissioner, I want automated rule enforcement for certain violations so that I can reduce manual work

- As a league analyst, I want to see rule violation trends over time so that I can suggest rule modifications

## Technical Requirements

### Rule Engine

```python
# Example rule definitions
RULES = {
    "keeper_cost": {
        "formula": "last_year_value + 10",
        "max_keepers": 3,
        "restrictions": ["no_three_same_type"]
    },
    "na_roster": {
        "max_slots": 2,
        "eligibility": "milb_only",
        "verification": "yahoo_na_designation"
    }
}
```

### Data Requirements

- Transaction history (adds, drops, trades)

- Roster snapshots (daily)

- Keeper declarations

- Draft values (historical)

- Player MLB/MiLB status

- Commissioner decisions log

### Database Schema

```sql
-- Rule violations table
CREATE TABLE rule_violations (
    id INTEGER PRIMARY KEY,
    rule_id VARCHAR(50),
    team_id INTEGER,
    violation_date DATE,
    violation_details JSON,
    status VARCHAR(20), -- 'pending', 'confirmed', 'dismissed'
    commissioner_notes TEXT,
    resolution_date DATE,
    created_at TIMESTAMP
);

-- Rule enforcement log
CREATE TABLE enforcement_actions (
    id INTEGER PRIMARY KEY,
    violation_id INTEGER,
    action_taken VARCHAR(100),
    commissioner_id INTEGER,
    action_date TIMESTAMP,
    notes TEXT
);
```

### Performance Requirements

- Rule checks execute within 2 seconds of triggering event

- Dashboard loads in < 1 second

- Historical reports generate in < 5 seconds

## UI/UX Requirements

### Commissioner Dashboard

- **Alert Center**: Real-time violation alerts with severity indicators

- **Investigation View**: Transaction details, rule specifics, team history

- **Decision Logger**: Form to record investigation outcome

- **Analytics Panel**: Violation trends, team compliance scores

### Manager Interface

- **Rule Reference**: Searchable rule documentation

- **Compliance Status**: Current week adds, keeper eligibility, etc.

- **Violation History**: Personal violation record with resolutions

### Mobile Considerations

- Responsive design for commissioner alerts

- Mobile-friendly rule reference

- Push notifications for urgent violations

### Visual Design Mockups

Complete interactive mockups are available showing the following views:

1. **Commissioner Dashboard**

1. **Investigation View**

1. **Rules Reference**

1. **Manager Compliance View**

1. **Violation History & Analytics**

[See Appendix D for complete visual mockups]

## Rule Detection Specifications

### Keeper Eligibility (Rule 8)

- **Trigger**: Keeper declaration submission

- **Checks**:

- **Alert**: Any violation found


**$0 Keeper Rule (Rule 8d)**:

- This is where the MLB experience restriction applies

- A player can only be kept for $0 if they have ZERO days of MLB playing experience

- This is separate from the NA roster slot rule

### Trade Veto Process (Rule 7)

- **Trigger**: Trade acceptance

- **Action**: Create vote poll

- **Monitor**: Vote count and quorum

- **Alert**: Commissioner when voting closes

## Implementation Phases

### Phase 1: Core Infrastructure (3 weeks)

- Rule engine framework

- Violation detection for adds/keepers

- Basic commissioner dashboard

- Database schema implementation

### Phase 2: Advanced Detection (2 weeks)

- NA roster monitoring

- Trade veto automation

- Manager notifications

- Rule reference center

### Phase 3: Analytics & Reporting (2 weeks)

- Violation analytics

- Compliance scoring

- Export functionality

- Historical reports

### Phase 4: Automation (1 week)

- Auto-enforcement options

- Slack/Discord integrations

- Advanced alerting rules

## Success Metrics

**Primary:**

- 95% of rule violations detected automatically

- 80% reduction in commissioner time spent on rule enforcement

**Secondary:**

- 100% of violations have logged resolutions

- < 5 disputes per season about rule enforcement

**User Satisfaction:**

- Commissioner satisfaction score > 4.5/5

- Manager clarity on rules score > 4.0/5

## Risk Assessment

### Technical Risks

- **Data Quality**: Incomplete transaction history

- **False Positives**: Incorrect violation detection

### User Risks

- **Over-automation**: Loss of league character

- **Privacy Concerns**: Violation history visibility

## Dependencies

- Yahoo Fantasy API for transaction data

- Existing roster tracking system

- Historical draft value data

- Commissioner account permissions

## Future Considerations

### Advanced Features

- Machine learning for violation prediction

- Natural language rule interpretation

- Cross-league rule sharing

- Custom rule builder interface

### Integration Opportunities

- League constitution management

- Automated penalty enforcement

- Season-long compliance tracking

- Rule change proposal system

## Appendix

### A. Sample Violation Alert

```json
{
  "violation_id": "vio_2025_001",
  "rule": "na_roster_compliance",
  "rule_name": "NA Roster Compliance (Rule 4)",
  "team": "Trout Fishing",
  "team_id": "458.l.6966.t.7",
  "detected_at": "2025-08-03T10:15:00Z",
  "details": {
    "player_name": "Mookie Betts",
    "player_id": "mlb.p.9333",
    "current_slot": "NA",
    "mlb_games_played": 1234,
    "yahoo_status": "NA",
    "violation_reason": "Player has MLB experience but is in NA slot"
  },
  "severity": "high",
  "status": "pending",
  "suggested_actions": [
    "Move player to active roster or bench",
    "Drop player if roster is full",
    "24-hour grace period to correct"
  ],
  "notification_sent": true,
  "grace_period_expires": "2025-08-04T10:15:00Z"
}
```

### B. Keeper Validation Logic

```python
def validate_keeper_declaration(keeper_list, team_id, season):
    violations = []
    
    # Check max 3 keepers
    if len(keeper_list) > 3:
        violations.append("Exceeds 3 keeper limit")
    
    # Check pitcher/hitter balance
    positions = [k['position'] for k in keeper_list]
    if positions.count('P') == 3 or positions.count('H') == 3:
        violations.append("Cannot keep 3 of same type")
    
    # Validate costs
    for keeper in keeper_list:
        if keeper['cost'] == 0:
            # Validate $0 keeper criteria
            if not validate_zero_keeper(keeper, team_id, season):
                violations.append(f"{keeper['name']} not eligible for $0")
        else:
            # Check cost = previous + $10
            expected = get_previous_cost(keeper['player_id']) + 10
            if keeper['cost'] != expected:
                violations.append(f"{keeper['name']} cost should be ${expected}")
    
    return violations
```

### C. Commissioner Dashboard Mockup

```javascript
+----------------------------------+
|     GKL Rule Committee           |
+----------------------------------+
| Active Violations: 3             |
|                                  |   
| [!] Trout Fishing                |
|     Invalid NA Roster Player     |
|     M. Betts has MLB experience  |
|     [Investigate] [Dismiss]      |
|                                  |
| [i] Dynasty Destroyers           |
|     Keeper Declaration Invalid   |
|     3 pitchers selected          |
|     [Investigate] [Dismiss]      |
+----------------------------------+
```

### D. Visual Design Mockups

The complete visual design system for the GKL Rule Committee module includes five comprehensive views that follow the established GKL League Analytics design patterns:

### Design System Consistency

- Navigation matches existing application (white background, blue active tabs)

- Card components use consistent shadows and border radius (8px)

- Color palette aligns with current design:

### Key Visual Elements

- **Priority Badges**: Color-coded for violation severity

- **Status Indicators**: Clear visual states for all violations

- **Data Tables**: Consistent with transaction explorer design

- **Form Elements**: Standard input styling with focus states

- **Responsive Grid**: Adapts from desktop to mobile views

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GKL Rule Committee - Complete Design System</title>
    <style>
        /* Base styles matching GKL League Analytics design system */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f7;
            color: #1d1d1f;
            line-height: 1.5;
        }
        
        /* Navigation styles matching current app */
        .nav-container {
            background: white;
            border-bottom: 1px solid #e5e7eb;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .nav-inner {
            max-width: 1280px;
            margin: 0 auto;
            padding: 0 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 64px;
        }
        
        .nav-left {
            display: flex;
            align-items: center;
            gap: 3rem;
        }
        
        .nav-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #1d1d1f;
        }
        
        .nav-links {
            display: flex;
            gap: 0;
        }
        
        .nav-link {
            padding: 0.75rem 1.5rem;
            color: #6b7280;
            text-decoration: none;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
            font-size: 0.875rem;
        }
        
        .nav-link:hover {
            color: #374151;
        }
        
        .nav-link.active {
            color: #3b82f6;
            border-bottom-color: #3b82f6;
        }
        
        .nav-right {
            color: #6b7280;
            font-size: 0.875rem;
        }
        
        /* Container styles */
        .main-container {
            max-width: 1280px;
            margin: 0 auto;
            padding: 2rem 1rem;
        }
        
        /* Card styles matching current design */
        .card {
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .card-header {
            padding: 1rem 1.5rem;
            border-bottom: 1px solid #e5e7eb;
            font-weight: 600;
            font-size: 1.125rem;
        }
        
        .card-body {
            padding: 1.5rem;
        }
        
        /* Stats card matching current design */
        .stat-card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .stat-value {
            font-size: 2.5rem;
            font-weight: 600;
            line-height: 1;
            margin-bottom: 0.5rem;
        }
        
        .stat-label {
            color: #6b7280;
            font-size: 0.875rem;
        }
        
        /* Button styles */
        .btn {
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-size: 0.875rem;
            font-weight: 500;
            border: none;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-block;
        }
        
        .btn-primary {
            background-color: #3b82f6;
            color: white;
        }
        
        .btn-primary:hover {
            background-color: #2563eb;
        }
        
        .btn-secondary {
            background: white;
            color: #374151;
            border: 1px solid #d1d5db;
        }
        
        .btn-secondary:hover {
            background-color: #f9fafb;
        }
        
        .btn-danger {
            background-color: #dc2626;
            color: white;
        }
        
        .btn-danger:hover {
            background-color: #b91c1c;
        }
        
        .btn-warning {
            background-color: #f59e0b;
            color: white;
        }
        
        .btn-warning:hover {
            background-color: #d97706;
        }
        
        /* Table styles */
        .table-container {
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        thead {
            background-color: #f9fafb;
        }
        
        th {
            text-align: left;
            padding: 0.75rem 1.5rem;
            font-size: 0.75rem;
            font-weight: 500;
            text-transform: uppercase;
            color: #6b7280;
            border-bottom: 1px solid #e5e7eb;
        }
        
        td {
            padding: 1rem 1.5rem;
            font-size: 0.875rem;
            border-bottom: 1px solid #e5e7eb;
        }
        
        tr:hover {
            background-color: #f9fafb;
        }
        
        /* Badge styles */
        .badge {
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        
        .badge-red {
            background-color: #fee2e2;
            color: #dc2626;
        }
        
        .badge-orange {
            background-color: #fed7aa;
            color: #ea580c;
        }
        
        .badge-yellow {
            background-color: #fef3c7;
            color: #f59e0b;
        }
        
        .badge-green {
            background-color: #d1fae5;
            color: #059669;
        }
        
        .badge-blue {
            background-color: #dbeafe;
            color: #3b82f6;
        }
        
        .badge-gray {
            background-color: #f3f4f6;
            color: #6b7280;
        }
        
        /* Alert styles */
        .alert {
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid;
            margin-bottom: 1.5rem;
        }
        
        .alert-danger {
            background-color: #fef2f2;
            border-color: #fecaca;
            color: #dc2626;
        }
        
        .alert-warning {
            background-color: #fffbeb;
            border-color: #fde68a;
            color: #d97706;
        }
        
        .alert-info {
            background-color: #eff6ff;
            border-color: #bfdbfe;
            color: #2563eb;
        }
        
        /* Form styles */
        .form-group {
            margin-bottom: 1rem;
        }
        
        .form-label {
            display: block;
            font-size: 0.875rem;
            font-weight: 500;
            color: #374151;
            margin-bottom: 0.5rem;
        }
        
        .form-input,
        .form-select,
        .form-textarea {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 0.875rem;
            transition: border-color 0.2s;
        }
        
        .form-input:focus,
        .form-select:focus,
        .form-textarea:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        
        /* Grid utilities */
        .grid {
            display: grid;
            gap: 1rem;
        }
        
        .grid-cols-1 {
            grid-template-columns: repeat(1, 1fr);
        }
        
        .grid-cols-2 {
            grid-template-columns: repeat(2, 1fr);
        }
        
        .grid-cols-3 {
            grid-template-columns: repeat(3, 1fr);
        }
        
        .grid-cols-4 {
            grid-template-columns: repeat(4, 1fr);
        }
        
        /* Utility classes */
        .mb-2 { margin-bottom: 0.5rem; }
        .mb-4 { margin-bottom: 1rem; }
        .mb-6 { margin-bottom: 1.5rem; }
        .mb-8 { margin-bottom: 2rem; }
        
        .text-sm { font-size: 0.875rem; }
        .text-base { font-size: 1rem; }
        .text-lg { font-size: 1.125rem; }
        .text-xl { font-size: 1.25rem; }
        .text-2xl { font-size: 1.5rem; }
        .text-3xl { font-size: 1.875rem; }
        
        .font-medium { font-weight: 500; }
        .font-semibold { font-weight: 600; }
        .font-bold { font-weight: 700; }
        
        .text-gray-500 { color: #6b7280; }
        .text-gray-600 { color: #4b5563; }
        .text-gray-700 { color: #374151; }
        .text-gray-900 { color: #111827; }
        
        /* Mockup frame */
        .mockup-section {
            margin-bottom: 3rem;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
        }
        
        .mockup-header {
            background: #2c3e50;
            color: white;
            padding: 0.75rem 1.5rem;
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .grid-cols-2,
            .grid-cols-3,
            .grid-cols-4 {
                grid-template-columns: 1fr;
            }
            
            .nav-links {
                display: none;
            }
        }
    </style>
</head>
<body>
    <!-- Mockup 1: Commissioner Dashboard -->
    <div class="mockup-section">
        <div class="mockup-header">GKL Rule Committee - Commissioner Dashboard</div>
        
        <!-- Navigation -->
        <nav class="nav-container">
            <div class="nav-inner">
                <div class="nav-left">
                    <div class="nav-title">GKL League Analytics</div>
                    <div class="nav-links">
                        <a href="#" class="nav-link">Home</a>
                        <a href="#" class="nav-link">Transactions</a>
                        <a href="#" class="nav-link">Daily Lineups</a>
                        <a href="#" class="nav-link">Analytics</a>
                        <a href="#" class="nav-link">Managers</a>
                        <a href="#" class="nav-link active">Rule Committee</a>
                    </div>
                </div>
                <div class="nav-right">Fantasy Baseball Analytics</div>
            </div>
        </nav>
        
        <!-- Main Content -->
        <div class="main-container">
            <!-- Page Header -->
            <div class="mb-8">
                <h1 class="text-3xl font-bold mb-2">Rule Committee</h1>
                <p class="text-gray-600">Monitor and enforce custom GKL league rules</p>
            </div>
            
            <!-- Commissioner Alert -->
            <div class="alert alert-danger">
                <div style="display: flex; align-items: start; gap: 0.75rem;">
                    <svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.293 7.293z" clip-rule="evenodd"/>
                    </svg>
                    <div>
                        <div class="font-semibold">3 Active Violations Require Review</div>
                        <div class="text-sm" style="margin-top: 0.25rem;">New violations detected in the last 24 hours that need commissioner investigation.</div>
                    </div>
                </div>
            </div>
            
            <!-- Stats Grid -->
            <div class="grid grid-cols-4 mb-8">
                <div class="stat-card">
                    <div class="stat-value" style="color: #dc2626;">3</div>
                    <div class="stat-label">Active Violations</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color: #059669;">7</div>
                    <div class="stat-label">Resolved This Week</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color: #111827;">42</div>
                    <div class="stat-label">Season Total</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color: #3b82f6;">94.2%</div>
                    <div class="stat-label">Compliance Rate</div>
                </div>
            </div>
            
            <!-- Main Content Grid -->
            <div class="grid" style="grid-template-columns: 2fr 1fr; gap: 1.5rem;">
                <!-- Active Violations -->
                <div class="card">
                    <div class="card-header">Active Violations</div>
                    <div class="card-body" style="display: flex; flex-direction: column; gap: 1rem;">
                        
                        <!-- Violation 1: NA Roster -->
                        <div style="border: 1px solid #fecaca; border-radius: 8px; padding: 1rem; background-color: #fef2f2;">
                            <div style="display: flex; justify-content: space-between;">
                                <div style="flex: 1;">
                                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                                        <span class="badge badge-red">High Priority</span>
                                        <span class="text-sm text-gray-500">2 hours ago</span>
                                    </div>
                                    <h4 class="text-base font-semibold mb-2">Invalid NA Roster Player</h4>
                                    <p class="text-sm text-gray-600">Trout Fishing has Mookie Betts in NA slot</p>
                                    <p class="text-sm text-gray-500" style="margin-top: 0.5rem;">Mookie Betts has 1,234 MLB games played</p>
                                </div>
                                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                                    <button class="btn btn-danger">Investigate</button>
                                    <button class="btn btn-secondary">Dismiss</button>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Violation 2: Keeper Declaration -->
                        <div style="border: 1px solid #fed7aa; border-radius: 8px; padding: 1rem; background-color: #fff7ed;">
                            <div style="display: flex; justify-content: space-between;">
                                <div style="flex: 1;">
                                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                                        <span class="badge badge-orange">Medium Priority</span>
                                        <span class="text-sm text-gray-500">5 hours ago</span>
                                    </div>
                                    <h4 class="text-base font-semibold mb-2">Keeper Declaration Invalid</h4>
                                    <p class="text-sm text-gray-600">Dynasty Destroyers selected 3 pitchers as keepers</p>
                                    <p class="text-sm text-gray-500" style="margin-top: 0.5rem;">Keepers: Cole ($45), deGrom ($38), Bieber ($25)</p>
                                </div>
                                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                                    <button class="btn btn-warning">Investigate</button>
                                    <button class="btn btn-secondary">Dismiss</button>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Violation 3: $0 Keeper -->
                        <div style="border: 1px solid #fef3c7; border-radius: 8px; padding: 1rem; background-color: #fffbeb;">
                            <div style="display: flex; justify-content: space-between;">
                                <div style="flex: 1;">
                                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                                        <span class="badge badge-yellow">Low Priority</span>
                                        <span class="text-sm text-gray-500">1 day ago</span>
                                    </div>
                                    <h4 class="text-base font-semibold mb-2">$0 Keeper Eligibility</h4>
                                    <p class="text-sm text-gray-600">Sho(hei) Me The Money declared invalid $0 keeper</p>
                                    <p class="text-sm text-gray-500" style="margin-top: 0.5rem;">Player has MLB experience - not eligible for $0</p>
                                </div>
                                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                                    <button class="btn" style="background-color: #f59e0b; color: white;">Investigate</button>
                                    <button class="btn btn-secondary">Dismiss</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Sidebar -->
                <div style="display: flex; flex-direction: column; gap: 1.5rem;">
                    <!-- Quick Actions -->
                    <div class="card">
                        <div class="card-header">Quick Actions</div>
                        <div class="card-body" style="display: flex; flex-direction: column; gap: 0.75rem;">
                            <button class="btn btn-secondary" style="width: 100%;">View All Rules</button>
                            <button class="btn btn-secondary" style="width: 100%;">Violation History</button>
                            <button class="btn btn-secondary" style="width: 100%;">Export Report</button>
                            <button class="btn btn-secondary" style="width: 100%;">Team Compliance</button>
                        </div>
                    </div>
                    
                    <!-- Top Violators -->
                    <div class="card">
                        <div class="card-header">Season Violations by Team</div>
                        <div class="card-body">
                            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                                <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
                                    <span class="font-medium">Dynasty Destroyers</span>
                                    <span class="text-gray-500">6 violations</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
                                    <span class="font-medium">Trout Fishing</span>
                                    <span class="text-gray-500">5 violations</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
                                    <span class="font-medium">Sho(hei) Me The Money</span>
                                    <span class="text-gray-500">4 violations</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
                                    <span class="font-medium">Frank In The House</span>
                                    <span class="text-gray-500">3 violations</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
                                    <span class="font-medium">Big Daddy's Funk</span>
                                    <span class="text-gray-500">2 violations</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Mockup 2: Investigation View -->
    <div class="mockup-section">
        <div class="mockup-header">GKL Rule Committee - Investigation View</div>
        
        <!-- Navigation (same as above) -->
        <nav class="nav-container">
            <div class="nav-inner">
                <div class="nav-left">
                    <div class="nav-title">GKL League Analytics</div>
                    <div class="nav-links">
                        <a href="#" class="nav-link">Home</a>
                        <a href="#" class="nav-link">Transactions</a>
                        <a href="#" class="nav-link">Daily Lineups</a>
                        <a href="#" class="nav-link">Analytics</a>
                        <a href="#" class="nav-link">Managers</a>
                        <a href="#" class="nav-link active">Rule Committee</a>
                    </div>
                </div>
                <div class="nav-right">Fantasy Baseball Analytics</div>
            </div>
        </nav>
        
        <!-- Main Content -->
        <div class="main-container">
            <!-- Breadcrumb -->
            <nav class="mb-4">
                <ol style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem;">
                    <li><a href="#" style="color: #3b82f6; text-decoration: none;">Rule Committee</a></li>
                    <li style="color: #9ca3af;">/</li>
                    <li style="color: #6b7280;">Investigation</li>
                </ol>
            </nav>
            
            <!-- Investigation Header -->
            <div class="card mb-6" style="background-color: #fef2f2;">
                <div class="card-body">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h1 class="text-2xl font-bold">Invalid NA Roster Player</h1>
                            <p class="text-sm text-gray-600" style="margin-top: 0.25rem;">Violation ID: VIO-2025-002</p>
                        </div>
                        <span class="badge badge-red">Pending Investigation</span>
                    </div>
                </div>
            </div>
            
            <div class="grid" style="grid-template-columns: 2fr 1fr; gap: 1.5rem;">
                <!-- Left Column -->
                <div style="display: flex; flex-direction: column; gap: 1.5rem;">
                    <!-- Violation Details -->
                    <div class="card">
                        <div class="card-header">Violation Details</div>
                        <div class="card-body">
                            <dl class="grid grid-cols-2" style="gap: 1rem;">
                                <div>
                                    <dt class="text-sm font-medium text-gray-500">Rule Violated</dt>
                                    <dd class="text-sm" style="margin-top: 0.25rem;">NA Roster Compliance (Rule 4)</dd>
                                </div>
                                <div>
                                    <dt class="text-sm font-medium text-gray-500">Team</dt>
                                    <dd class="text-sm" style="margin-top: 0.25rem;">Trout Fishing</dd>
                                </div>
                                <div>
                                    <dt class="text-sm font-medium text-gray-500">Detection Time</dt>
                                    <dd class="text-sm" style="margin-top: 0.25rem;">Aug 3, 2025 at 10:15 AM ET</dd>
                                </div>
                                <div>
                                    <dt class="text-sm font-medium text-gray-500">Severity</dt>
                                    <dd class="text-sm" style="margin-top: 0.25rem;">High - MLB experienced player</dd>
                                </div>
                                <div style="grid-column: span 2;">
                                    <dt class="text-sm font-medium text-gray-500">Description</dt>
                                    <dd class="text-sm" style="margin-top: 0.25rem;">Mookie Betts is currently in an NA roster slot but has 1,234 MLB games played. NA slots are only for MiLB players with no MLB experience.</dd>
                                </div>
                            </dl>
                        </div>
                    </div>
                    
                    <!-- Player History -->
                    <div class="card">
                        <div class="card-header">Player History - Mookie Betts</div>
                        <div class="table-container">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Date</th>
                                        <th>MLB Games</th>
                                        <th>Yahoo Status</th>
                                        <th>Roster Slot</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td>Jul 1, 2025</td>
                                        <td>1,220</td>
                                        <td><span class="badge badge-gray">Active</span></td>
                                        <td>RF</td>
                                    </tr>
                                    <tr>
                                        <td>Jul 15, 2025</td>
                                        <td>1,230</td>
                                        <td><span class="badge badge-gray">Active</span></td>
                                        <td>IL</td>
                                    </tr>
                                    <tr style="background-color: #fef2f2;">
                                        <td><strong>Aug 1, 2025</strong></td>
                                        <td><strong>1,234</strong></td>
                                        <td><span class="badge badge-red">NA</span></td>
                                        <td style="color: #dc2626;"><strong>NA SLOT</strong></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
                
                <!-- Right Column -->
                <div style="display: flex; flex-direction: column; gap: 1.5rem;">
                    <!-- Commissioner Actions -->
                    <div class="card">
                        <div class="card-header">Commissioner Actions</div>
                        <div class="card-body">
                            <form>
                                <div class="form-group">
                                    <label class="form-label">Decision</label>
                                    <select class="form-select">
                                        <option>Select action...</option>
                                        <option>Confirm Violation</option>
                                        <option>Dismiss - False Positive</option>
                                        <option>Dismiss - Extenuating Circumstances</option>
                                        <option>Defer - Need More Information</option>
                                    </select>
                                </div>
                                
                                <div class="form-group">
                                    <label class="form-label">Enforcement Action</label>
                                    <select class="form-select">
                                        <option>Select enforcement...</option>
                                        <option>Force Roster Move</option>
                                        <option>Issue Warning</option>
                                        <option>Apply Penalty</option>
                                        <option>No Action Required</option>
                                    </select>
                                </div>
                                
                                <div class="form-group">
                                    <label class="form-label">Commissioner Notes</label>
                                    <textarea class="form-textarea" rows="4" placeholder="Document your decision reasoning..."></textarea>
                                </div>
                                
                                <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-top: 1rem;">
                                    <button type="button" class="btn btn-primary">Submit Decision</button>
                                    <button type="button" class="btn btn-secondary">Save as Draft</button>
                                </div>
                            </form>
                        </div>
                    </div>
                    
                    <!-- Team History -->
                    <div class="card">
                        <div class="card-header">Team Violation History</div>
                        <div class="card-body">
                            <div>
                                <p class="font-semibold">Trout Fishing</p>
                                <p class="text-sm text-gray-500">5 total violations this season</p>
                            </div>
                            <div style="margin-top: 1rem; display: flex; flex-direction: column; gap: 0.5rem;">
                                <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
                                    <span class="text-gray-600">NA Roster</span>
                                    <span class="font-medium">3</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
                                    <span class="text-gray-600">Keeper Rules</span>
                                    <span class="font-medium">1</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.875rem;">
                                    <span class="text-gray-600">Trade Veto</span>
                                    <span class="font-medium">1</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Mockup 3: Rules Reference -->
    <div class="mockup-section">
        <div class="mockup-header">GKL Rule Committee - Rules Reference</div>
        
        <!-- Navigation (same) -->
        <nav class="nav-container">
            <div class="nav-inner">
                <div class="nav-left">
                    <div class="nav-title">GKL League Analytics</div>
                    <div class="nav-links">
                        <a href="#" class="nav-link">Home</a>
                        <a href="#" class="nav-link">Transactions</a>
                        <a href="#" class="nav-link">Daily Lineups</a>
                        <a href="#" class="nav-link">Analytics</a>
                        <a href="#" class="nav-link">Managers</a>
                        <a href="#" class="nav-link active">Rule Committee</a>
                    </div>
                </div>
                <div class="nav-right">Fantasy Baseball Analytics</div>
            </div>
        </nav>
        
        <!-- Main Content -->
        <div class="main-container">
            <!-- Page Header -->
            <div class="mb-8">
                <h1 class="text-3xl font-bold mb-2">GKL Custom Rules Reference</h1>
                <p class="text-gray-600">Complete documentation of all custom league rules and enforcement guidelines</p>
            </div>
            
            <!-- Search -->
            <div class="mb-6">
                <div style="max-width: 32rem;">
                    <input type="search" class="form-input" placeholder="Search rules..." style="padding-left: 2.5rem;">
                    <svg style="position: absolute; left: 0.75rem; top: 0.5rem; width: 1.25rem; height: 1.25rem; color: #9ca3af;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                    </svg>
                </div>
            </div>
            
            <!-- Rules Grid -->
            <div class="grid grid-cols-2" style="gap: 1.5rem;">
                <!-- Rule 4: NA Roster -->
                <div class="card">
                    <div class="card-header" style="background-color: #f9fafb;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>Rule 4: NA Roster Spots</span>
                            <span class="badge badge-green">Automatically Enforced</span>
                        </div>
                    </div>
                    <div class="card-body">
                        <div style="display: flex; flex-direction: column; gap: 1rem;">
                            <div>
                                <h4 class="text-sm font-semibold text-gray-900">Rule Text</h4>
                                <p class="text-sm text-gray-600" style="margin-top: 0.25rem;">NA spots are to be used for MiLB players only</p>
                            </div>
                            <div>
                                <h4 class="text-sm font-semibold text-gray-900">Enforcement</h4>
                                <ul class="text-sm text-gray-600" style="margin-top: 0.25rem; padding-left: 1.25rem; list-style: disc;">
                                    <li>Player must be designated by Yahoo as "NA"</li>
                                    <li>Daily roster checks for violations</li>
                                    <li>24-hour grace period to correct</li>
                                </ul>
                            </div>
                            <div>
                                <h4 class="text-sm font-semibold text-gray-900">Detection Method</h4>
                                <p class="text-sm text-gray-600" style="margin-top: 0.25rem;">Check if player has any MLB game experience</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Rule 8: Keepers -->
                <div class="card">
                    <div class="card-header" style="background-color: #f9fafb;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>Rule 8: Keepers</span>
                            <span class="badge badge-yellow">Commissioner Review</span>
                        </div>
                    </div>
                    <div class="card-body">
                        <div style="display: flex; flex-direction: column; gap: 1rem;">
                            <div>
                                <h4 class="text-sm font-semibold text-gray-900">Rule Text</h4>
                                <p class="text-sm text-gray-600" style="margin-top: 0.25rem;">Maximum of 3 Keepers is permissible</p>
                            </div>
                            <div>
                                <h4 class="text-sm font-semibold text-gray-900">Key Provisions</h4>
                                <ul class="text-sm text-gray-600" style="margin-top: 0.25rem; padding-left: 1.25rem; list-style: disc;">
                                    <li>Cost to keep is last year's draft value + $10</li>
                                    <li>Cannot keep 3 Pitchers or 3 Offense players</li>
                                    <li>$0 keeper allowed if criteria met</li>
                                    <li>Due 1 week prior to draft</li>
                                </ul>
                            </div>
                            <div>
                                <h4 class="text-sm font-semibold text-gray-900">Enforcement</h4>
                                <p class="text-sm text-gray-600" style="margin-top: 0.25rem;">Commissioner validates all keeper submissions</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Rule 7: Trade Vetoes -->
                <div class="card">
                    <div class="card-header" style="background-color: #f9fafb;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>Rule 7: Trade Vetoes</span>
                            <span class="badge badge-blue">Voting Required</span>
                        </div>
                    </div>
                    <div class="card-body">
                        <div style="display: flex; flex-direction: column; gap: 1rem;">
                            <div>
                                <h4 class="text-sm font-semibold text-gray-900">Rule Text</h4>
                                <p class="text-sm text-gray-600" style="margin-top: 0.25rem;">Commissioner-enforced with league vote</p>
                            </div>
                            <div>
                                <h4 class="text-sm font-semibold text-gray-900">Process</h4>
                                <ul class="text-sm text-gray-600" style="margin-top: 0.25rem; padding-left: 1.25rem; list-style: disc;">
                                    <li>League votes via poll during consideration period</li>
                                    <li>Simple majority decides</li>
                                    <li>Quorum is 50% of Managers</li>
                                    <li>Trade allowed if quorum not met</li>
                                </ul>
                            </div>
                            <div>
                                <h4 class="text-sm font-semibold text-gray-900">Commissioner Role</h4>
                                <p class="text-sm text-gray-600" style="margin-top: 0.25rem;">Create poll, track votes, execute decision</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Rule 8d: $0 Keepers -->
                <div class="card">
                    <div class="card-header" style="background-color: #f9fafb;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>Rule 8d: $0 Keeper Eligibility</span>
                            <span class="badge badge-yellow">Commissioner Review</span>
                        </div>
                    </div>
                    <div class="card-body">
                        <div style="display: flex; flex-direction: column; gap: 1rem;">
                            <div>
                                <h4 class="text-sm font-semibold text-gray-900">Rule Text</h4>
                                <p class="text-sm text-gray-600" style="margin-top: 0.25rem;">Managers may keep one player for $0 if criteria met</p>
                            </div>
                            <div>
                                <h4 class="text-sm font-semibold text-gray-900">Criteria</h4>
                                <ul class="text-sm text-gray-600" style="margin-top: 0.25rem; padding-left: 1.25rem; list-style: disc;">
                                    <li>Player was kept for $0 previous year or went undrafted</li>
                                    <li>Player was on manager's roster at season end</li>
                                    <li>Player has never appeared in an MLB game</li>
                                </ul>
                            </div>
                            <div>
                                <h4 class="text-sm font-semibold text-gray-900">Verification</h4>
                                <p class="text-sm text-gray-600" style="margin-top: 0.25rem;">MLB game logs checked against player history</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Mockup 4: Manager Compliance View -->
    <div class="mockup-section">
        <div class="mockup-header">GKL Rule Committee - Manager Compliance View</div>
        
        <!-- Navigation (same) -->
        <nav class="nav-container">
            <div class="nav-inner">
                <div class="nav-left">
                    <div class="nav-title">GKL League Analytics</div>
                    <div class="nav-links">
                        <a href="#" class="nav-link">Home</a>
                        <a href="#" class="nav-link">Transactions</a>
                        <a href="#" class="nav-link">Daily Lineups</a>
                        <a href="#" class="nav-link">Analytics</a>
                        <a href="#" class="nav-link">Managers</a>
                        <a href="#" class="nav-link active">Rule Committee</a>
                    </div>
                </div>
                <div class="nav-right">Fantasy Baseball Analytics</div>
            </div>
        </nav>
        
        <!-- Main Content -->
        <div class="main-container">
            <!-- Page Header -->
            <div class="mb-8">
                <h1 class="text-3xl font-bold mb-2">My Compliance Status</h1>
                <p class="text-gray-600">Track your rule compliance and avoid violations</p>
            </div>
            
            <!-- Compliance Score Card -->
            <div class="card mb-6">
                <div class="card-body">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h3 class="text-lg font-semibold">Season Compliance Score</h3>
                            <p class="text-sm text-gray-500" style="margin-top: 0.25rem;">Based on violations and league activity</p>
                        </div>
                        <div style="text-align: right;">
                            <div class="text-3xl font-bold" style="color: #059669;">96.4%</div>
                            <p class="text-sm text-gray-500">2 violations this season</p>
                        </div>
                    </div>
                    <div style="margin-top: 1rem;">
                        <div style="width: 100%; background-color: #e5e7eb; border-radius: 9999px; height: 0.5rem;">
                            <div style="width: 96.4%; background-color: #059669; height: 0.5rem; border-radius: 9999px;"></div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Current Status Grid -->
            <div class="grid grid-cols-3 mb-6" style="gap: 1rem;">
                <div class="stat-card">
                    <div class="stat-value" style="color: #059669; font-size: 2rem;">✓</div>
                    <div class="stat-label">NA Roster Status</div>
                    <div class="text-sm font-medium" style="margin-top: 0.25rem;">Compliant</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-value" style="color: #3b82f6; font-size: 2rem;">42</div>
                    <div class="stat-label">Days to Keeper Deadline</div>
                    <div class="text-sm font-medium" style="margin-top: 0.25rem;">Feb 15, 2026</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-value" style="color: #6b7280; font-size: 2rem;">3</div>
                    <div class="stat-label">Keeper Slots Available</div>
                    <div class="text-sm font-medium" style="margin-top: 0.25rem;">0 declared</div>
                </div>
            </div>
            
            <!-- Violation History -->
            <div class="card">
                <div class="card-header">My Violation History</div>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Rule</th>
                                <th>Status</th>
                                <th>Resolution</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>May 15, 2025</td>
                                <td>NA Roster Compliance</td>
                                <td><span class="badge badge-red">Confirmed</span></td>
                                <td>Player moved to active roster</td>
                            </tr>
                            <tr>
                                <td>Apr 3, 2025</td>
                                <td>Keeper Declaration</td>
                                <td><span class="badge badge-green">Dismissed</span></td>
                                <td>Rule clarification - no violation</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Mockup 5: Violation History & Analytics -->
    <div class="mockup-section">
        <div class="mockup-header">GKL Rule Committee - Violation History & Analytics</div>
        
        <!-- Navigation (same) -->
        <nav class="nav-container">
            <div class="nav-inner">
                <div class="nav-left">
                    <div class="nav-title">GKL League Analytics</div>
                    <div class="nav-links">
                        <a href="#" class="nav-link">Home</a>
                        <a href="#" class="nav-link">Transactions</a>
                        <a href="#" class="nav-link">Daily Lineups</a>
                        <a href="#" class="nav-link">Analytics</a>
                        <a href="#" class="nav-link">Managers</a>
                        <a href="#" class="nav-link active">Rule Committee</a>
                    </div>
                </div>
                <div class="nav-right">Fantasy Baseball Analytics</div>
            </div>
        </nav>
        
        <!-- Main Content -->
        <div class="main-container">
            <!-- Page Header -->
            <div class="mb-8">
                <h1 class="text-3xl font-bold mb-2">Violation History & Analytics</h1>
                <p class="text-gray-600">Complete record of all rule violations and enforcement actions</p>
            </div>
            
            <!-- Filters -->
            <div class="card mb-6">
                <div class="card-body">
                    <div class="grid grid-cols-4" style="gap: 1rem;">
                        <div class="form-group" style="margin: 0;">
                            <label class="form-label">Team</label>
                            <select class="form-select">
                                <option>All Teams</option>
                                <option>Dynasty Destroyers</option>
                                <option>Trout Fishing</option>
                                <option>Sho(hei) Me The Money</option>
                            </select>
                        </div>
                        <div class="form-group" style="margin: 0;">
                            <label class="form-label">Rule</label>
                            <select class="form-select">
                                <option>All Rules</option>
                                <option>NA Roster Compliance</option>
                                <option>Keeper Eligibility</option>
                                <option>Trade Veto</option>
                            </select>
                        </div>
                        <div class="form-group" style="margin: 0;">
                            <label class="form-label">Status</label>
                            <select class="form-select">
                                <option>All Statuses</option>
                                <option>Confirmed</option>
                                <option>Dismissed</option>
                                <option>Pending</option>
                            </select>
                        </div>
                        <div class="form-group" style="margin: 0;">
                            <label class="form-label">Date Range</label>
                            <select class="form-select">
                                <option>This Season</option>
                                <option>Last 30 Days</option>
                                <option>Last 90 Days</option>
                                <option>All Time</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Violations Table -->
            <div class="card">
                <div class="card-header">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Violation Records</span>
                        <button class="btn btn-secondary">Export CSV</button>
                    </div>
                </div>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Team</th>
                                <th>Rule</th>
                                <th>Details</th>
                                <th>Status</th>
                                <th>Commissioner</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Aug 3, 2025</td>
                                <td>Trout Fishing</td>
                                <td>NA Roster</td>
                                <td>M. Betts in NA slot</td>
                                <td><span class="badge badge-orange">Pending</span></td>
                                <td>-</td>
                                <td><a href="#" style="color: #3b82f6;">View</a></td>
                            </tr>
                            <tr>
                                <td>Aug 2, 2025</td>
                                <td>Dynasty Destroyers</td>
                                <td>Keeper Rules</td>
                                <td>3 pitchers selected</td>
                                <td><span class="badge badge-orange">Pending</span></td>
                                <td>-</td>
                                <td><a href="#" style="color: #3b82f6;">View</a></td>
                            </tr>
                            <tr>
                                <td>Jul 28, 2025</td>
                                <td>Sho(hei) Me The Money</td>
                                <td>$0 Keeper</td>
                                <td>Invalid player selection</td>
                                <td><span class="badge badge-red">Confirmed</span></td>
                                <td>Commissioner</td>
                                <td><a href="#" style="color: #3b82f6;">View</a></td>
                            </tr>
                            <tr>
                                <td>Jul 15, 2025</td>
                                <td>Frank In The House</td>
                                <td>NA Roster</td>
                                <td>Player graduated to MLB</td>
                                <td><span class="badge badge-green">Dismissed</span></td>
                                <td>Commissioner</td>
                                <td><a href="#" style="color: #3b82f6;">View</a></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
```
