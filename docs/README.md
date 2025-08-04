# GKL League Analytics Documentation

## Documentation Philosophy

This project maintains a clear separation between two types of documentation:

1. **Development Documentation** (`/development-docs/`) - Generated during development sessions
2. **Permanent Documentation** (`/permanent-docs/`) - Authoritative project references

## Directory Structure

### 📂 `/development-docs/`
**Purpose**: Documentation generated during active development sessions

Contains documentation created while implementing features, fixing bugs, or making architectural decisions during development work. This includes:

- **`/implemented/`** - Completed features and fixes from development sessions
- **`/in-progress/`** - Documentation for ongoing development work
- **`/planned/`** - Plans and specifications created during development
- **`/guides/`** - How-to guides written during implementation
- **`/architecture/`** - Technical decisions made during development
- **`/deployment/`** - Deployment processes and status tracking

These documents are working documents that capture the development process and may be archived when no longer relevant.

### 📚 `/permanent-docs/`
**Purpose**: Authoritative project documentation

Contains comprehensive documentation created outside of development sessions that serves as the permanent reference for the project. This includes:

- System architecture documentation
- Feature capabilities and descriptions
- API documentation
- Dependency management
- Configuration guides
- User documentation

These documents are carefully crafted, reviewed, and maintained as the source of truth for understanding the project.

### 📋 `/prds/`
**Purpose**: Product Requirements Documents

Contains formal specifications for features and enhancements. These documents:
- Define feature requirements
- Remain unchanged once created
- Serve as the source of truth for what should be built

## Documentation Methodology

### When to Use Development Docs

During development sessions, create documentation in `/development-docs/` when:
- Implementing new features
- Fixing bugs or issues
- Making architectural decisions
- Creating deployment artifacts
- Writing quick guides or notes
- Tracking work progress

### When to Create Permanent Docs

Outside of development sessions, create documentation in `/permanent-docs/` when:
- Documenting the overall system architecture
- Creating comprehensive feature documentation
- Writing official API documentation
- Establishing configuration standards
- Creating user-facing documentation
- Documenting dependencies and requirements

## Quick Navigation

### For Developers Starting Work
1. Check `/development-docs/in-progress/` for ongoing work
2. Review `/development-docs/planned/` for upcoming tasks
3. Consult `/development-docs/guides/` for implementation help

### For Understanding the System
1. Start with `/permanent-docs/` for authoritative documentation
2. Review `/prds/` for feature requirements
3. Check module READMEs for component-specific details

### For Deployment
1. Check `/development-docs/deployment/` for current status
2. Follow guides in `/development-docs/guides/` for deployment steps
3. Review `/development-docs/implemented/` for deployment history

## Key Project Files

### Root Directory
- **`README.md`** - Main project overview (permanent)
- **`CLAUDE.md`** - AI assistant instructions (permanent, actively maintained)

### Module READMEs
Each module maintains its own README for quick reference:
- `daily_lineups/README.md`
- `player_stats/README.md`
- `web-ui/README.md`
- `cloudflare/README.md`

## Documentation Standards

### Development Documentation Standards
- **Temporal**: Tied to specific development sessions
- **Informal**: Can be quick notes or implementation details
- **Organized by Status**: Implemented, in-progress, planned
- **Archivable**: Can be moved to archive when outdated

### Permanent Documentation Standards
- **Timeless**: Not tied to specific development sessions
- **Formal**: Well-structured and comprehensive
- **Authoritative**: Serves as the source of truth
- **Maintained**: Updated only when system changes significantly

## Maintenance Guidelines

1. **During Development**: All new docs go in `/development-docs/`
2. **After Implementation**: Move relevant info to permanent docs if needed
3. **Regular Cleanup**: Archive old development docs periodically
4. **Keep Current**: Update permanent docs when architecture changes

## Last Updated
August 4, 2025 - Established development vs. permanent documentation methodology