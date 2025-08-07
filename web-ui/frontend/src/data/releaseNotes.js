// Versioning System:
// MAJOR.MINOR.PATCH (Semantic Versioning)
// MAJOR (1.x.x): Breaking changes, major architecture shifts
// MINOR (x.X.x): New features, significant improvements
// PATCH (x.x.X): Bug fixes, minor improvements
// Starting from 1.0.0 on August 1, 2024 (project inception)

export const releaseNotes = [
  {
    id: "2024-08-07",
    version: "1.5.0",
    date: "August 7, 2024",
    title: "Release Notes & Feedback System",
    summary: "Introducing a public release notes page and user feedback mechanism",
    highlights: [
      "New release notes page at /release-notes showing version history and updates",
      "Semantic versioning system (MAJOR.MINOR.PATCH) for tracking changes",
      "Footer with GitHub issue reporting link for user feedback",
      "Easy access via 'Updates' link in the navigation bar"
    ],
    details: {
      features: [
        "Public-facing release notes with expandable details",
        "Chronological version history with highlights and technical details",
        "Direct GitHub integration for issue reporting",
        "Mobile-responsive release notes display"
      ],
      improvements: [
        "Better communication of new features and updates to users",
        "Standardized versioning following semantic versioning principles",
        "Improved user engagement through feedback mechanism"
      ]
    }
  },
  {
    id: "2024-08-06",
    version: "1.4.0",
    date: "August 6, 2024",
    title: "Player Stats & Health Tracking",
    summary: "Comprehensive MLB player statistics with automated health scoring",
    highlights: [
      "Track all 750+ active MLB players with daily batting and pitching statistics from real games",
      "Automatic player health grades (A-F) based on injury status and playing time patterns",
      "Automated data collection runs 3 times daily (6 AM, 1 PM, 10 PM ET) via GitHub Actions",
      "Successfully mapped 1,583 Yahoo player IDs (79% coverage) using fuzzy name matching"
    ],
    details: {
      features: [
        "Real-time MLB statistics from official MLB Stats API via PyBaseball",
        "Intelligent health scoring algorithm based on games played and injury reports",
        "Enhanced fuzzy matching for players with Jr./Sr./III suffixes",
        "Comprehensive data quality validation and reporting"
      ],
      improvements: [
        "GitHub Actions automation for production data collection",
        "Improved error handling for D1 database operations",
        "Better handling of column name differences between environments"
      ]
    }
  },
  {
    id: "2024-08-05-hotfix",
    version: "1.3.1",
    date: "August 5, 2024",
    title: "Transaction Display Hotfix",
    summary: "Emergency fix for transaction search functionality",
    highlights: [
      "Fixed critical bug where transaction searches were returning empty results",
      "Reverted problematic ORDER BY clause that was incompatible with GROUP BY",
      "Restored transaction explorer functionality for all users"
    ],
    details: {
      bugFixes: [
        "Reverted transaction ordering logic to use subquery approach",
        "Fixed date handling in transaction queries",
        "Resolved SQL compatibility issues between SQLite and D1"
      ]
    }
  },
  {
    id: "2024-08-04",
    version: "1.3.0",
    date: "August 4, 2024",
    title: "Data Pipeline Consolidation",
    summary: "Major backend improvements reducing codebase complexity by 60%",
    highlights: [
      "Consolidated 10+ scripts per module down to 2-3 standardized scripts",
      "Added comprehensive draft results collection with keeper designation support",
      "Implemented automated foreign key dependency management for database imports",
      "Standardized job logging across all data collection pipelines"
    ],
    details: {
      features: [
        "Draft results collection with automatic snake/auction detection",
        "Automated foreign key constraint resolution during imports",
        "Data quality validation scripts for all pipelines"
      ],
      improvements: [
        "Reduced codebase from 30+ scripts to 12 core modules",
        "Standardized backfill + update pattern across all pipelines",
        "Enhanced error handling and retry logic with exponential backoff"
      ]
    }
  },
  {
    id: "2024-08-03",
    version: "1.2.0",
    date: "August 3, 2024",
    title: "Production Deployment & Draft Analytics",
    summary: "Enhanced deployment standards and complete draft tracking",
    highlights: [
      "View and analyze complete draft results for your league",
      "Automatic detection of snake vs auction draft formats",
      "Implemented mandatory pre-deployment checklist to prevent configuration errors",
      "Established feature branch workflow requirement for all new development"
    ],
    details: {
      features: [
        "One-click draft import after your league draft completes",
        "Player enrichment with current team and position eligibility",
        "Support for keeper designations and draft pick trading"
      ],
      improvements: [
        "Mandatory git status check before deployments",
        "Automatic .env.local handling during production builds",
        "Feature branch enforcement with protected main branch",
        "Enhanced sync_to_production script reliability"
      ],
      bugFixes: [
        "Fixed production builds accidentally using development API endpoints",
        "Resolved CORS configuration issues in production"
      ]
    }
  },
  {
    id: "2024-08-01",
    version: "1.0.0",
    date: "August 1, 2024",
    title: "Initial Production Release",
    summary: "GKL League Analytics goes live on Cloudflare",
    highlights: [
      "Production deployment on Cloudflare Pages (goldenknightlounge.com)",
      "Real-time transaction tracking with comprehensive job logging",
      "Daily lineup collection and analysis for all 18 teams",
      "React-based web UI with player spotlight features"
    ],
    details: {
      features: [
        "Transaction explorer with advanced filtering and search",
        "Daily lineups view with team-by-team breakdown",
        "Player spotlight pages showing usage patterns",
        "Manager analytics and transaction insights",
        "Cloudflare Workers API with D1 database integration"
      ],
      improvements: [
        "Dual database support (SQLite for development, D1 for production)",
        "OAuth2 authentication for Yahoo Fantasy Sports API",
        "Comprehensive error logging and monitoring"
      ]
    }
  }
];