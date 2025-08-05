# Development Documentation File Rename Mapping

## Naming Convention
`[type]-[subject]-[description]-[date].md`

Types:
- **plan**: Implementation plans
- **guide**: How-to guides and tutorials
- **report**: Completion reports, summaries
- **analysis**: Technical analysis, investigations
- **checklist**: Step-by-step checklists
- **template**: Reusable templates
- **review**: Review summaries

## Architecture Directory

| Current Name | New Name | Reason |
|-------------|----------|---------|
| DATABASE_SEPARATION.md | analysis-database-separation-2025.md | Clear type and timeframe |
| deployment_structure_analysis.md | analysis-deployment-structure.md | Consistent format |
| IMPLEMENTATION_PLAN_SQLITE_STABILITY.md | plan-sqlite-stability-implementation.md | Clear type prefix |
| league_keys_implementation.md | plan-league-keys-implementation.md | Clear type prefix |
| NOTION_SETUP.md | guide-notion-integration-setup.md | More descriptive |

## Deployment Directory

| Current Name | New Name | Reason |
|-------------|----------|---------|
| CLOUDFLARE_INTEGRATION.md | guide-cloudflare-integration.md | Clear type |
| DEPLOYMENT_CHECKLIST.md | checklist-deployment-steps.md | Clear type |
| DEPLOYMENT_STATUS.md | report-deployment-status-2025.md | Add date context |
| README_DEPLOYMENT.md | guide-deployment-overview.md | More descriptive |
| test_deployment.md | guide-test-deployment-process.md | More descriptive |
| TEST_GITHUB_ACTIONS.md | guide-github-actions-testing.md | Clear subject |

## Guides Directory

| Current Name | New Name | Reason |
|-------------|----------|---------|
| auth_docs.md | guide-yahoo-auth-setup.md | More specific |
| daily_lineups_quickstart.md | guide-daily-lineups-quickstart.md | Add type prefix |
| DEPLOYMENT_GUIDE.md | guide-production-deployment.md | More specific |
| enable_github_actions.md | guide-github-actions-enable.md | Consistent format |
| PRODUCTION_SETUP.md | guide-production-environment-setup.md | More descriptive |
| QUICK_START.md | guide-development-quickstart.md | More specific |
| SAFE_CREDENTIAL_SETUP.md | guide-credentials-secure-setup.md | Clear subject |
| SECURITY_ACTION_PLAN.md | plan-security-improvements-2025.md | Clear type and date |
| SECURITY_SETUP.md | guide-security-configuration.md | Clear purpose |
| setup_cloudflare.md | guide-cloudflare-initial-setup.md | More specific |
| setup_github_secrets_TEMPLATE.md | template-github-secrets-setup.md | Clear type |
| setup-custom-domain.md | guide-custom-domain-setup.md | Consistent format |

## Implemented Directory

| Current Name | New Name | Reason |
|-------------|----------|---------|
| cloudflare_directory_reorganization.md | report-cloudflare-reorganization-2025.md | Clear type and date |
| DATA_IMPORT_COMPLETE.md | report-data-import-completion-2025.md | More descriptive |
| data_pipeline_reorganization.md | report-pipeline-reorganization-2025.md | Clear type and date |
| DEPLOYMENT_COMPLETE.md | report-deployment-completion-2025.md | Add date context |
| DEPLOYMENT_SUMMARY.md | summary-deployment-results-2025.md | Clear type |
| GITHUB_ACTIONS_FIXED.md | report-github-actions-fixes-2025.md | Clear type and date |
| HOME_PAGE_FIX.md | report-homepage-bugfix-2025.md | More descriptive |
| PLAYER_CARDS_FIX.md | report-player-cards-bugfix-2025.md | More descriptive |
| PLAYERS_PAGE_FIX.md | report-players-page-bugfix-2025.md | More descriptive |
| player-stats-pipeline-improvements-implementation-plan.md | plan-player-stats-improvements-2025-08.md | Shorten, add date |
| stage1_completion.md | report-stage1-completion-2025.md | Clear type and date |
| stage2_completion.md | report-stage2-completion-2025.md | Clear type and date |
| stage3_completion.md | report-stage3-completion-2025.md | Clear type and date |
| TEST_RESULTS.md | report-testing-results-2025.md | Clear type and date |
| WEBSITE_DATA_ISSUE_RESOLVED.md | report-website-data-fix-2025.md | Shorter, clearer |
| WORKFLOW_FIXES_APPLIED.md | report-workflow-fixes-2025.md | Clear type and date |

## In-Progress Directory

| Current Name | New Name | Reason |
|-------------|----------|---------|
| draft-values-implementation-plan.md | Keep as-is (recently created) | Already follows pattern |
| implementation_plan.md | plan-general-implementation.md | Too generic, needs context |
| improved-transaction-timestamps-implementation-plan.md | Keep as-is (active work) | Developer is using this |
| INCREMENTAL_UPDATES.md | plan-incremental-update-strategy.md | Clear type and purpose |
| stage2-frontend-completion-summary.md | Keep as-is (active work) | Related to timestamps |

## Planned Directory

| Current Name | New Name | Reason |
|-------------|----------|---------|
| IMMEDIATE_NEXT_STEPS.md | plan-immediate-tasks-2025-08.md | Add date context |
| NEXT_STEPS.md | plan-future-enhancements.md | More descriptive |
| SCHEDULE_REFERENCE.md | reference-development-schedule.md | Clear type |
| URGENT_SECURITY_FIX.md | plan-security-urgent-fixes.md | Clear urgency |

## Root Level Files

| Current Name | New Name | Reason |
|-------------|----------|---------|
| LOCAL_DEVELOPMENT_SETUP.md | guide-local-development-setup.md | Clear type |
| documentation-review-2025-08-05.md | review-documentation-2025-08-05.md | Already good format |
| REORGANIZATION_SUMMARY.md | summary-codebase-reorganization-2025.md | Clear type and scope |
| player-spotlight-draft-values-implementation-plan.md | Should be in implemented/ | Misplaced file |

## Benefits of New Convention

1. **Predictable**: Easy to understand what a file contains
2. **Searchable**: Can grep for all plans, guides, reports, etc.
3. **Sortable**: Files naturally group by type
4. **Temporal**: Important docs have date context
5. **Consistent**: Single naming pattern throughout