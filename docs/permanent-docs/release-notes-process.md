# Release Notes Process

## Overview

The GKL League Analytics platform maintains user-facing release notes accessible at `/release-notes` on the production website. These release notes provide transparency about new features, bug fixes, and improvements in a user-friendly format.

## Versioning System

We follow **Semantic Versioning (SemVer)** with the format `MAJOR.MINOR.PATCH`:

- **MAJOR** (X.0.0): Breaking changes, major architecture shifts, significant UI overhauls
- **MINOR** (1.X.0): New features, significant improvements, new data pipelines
- **PATCH** (1.0.X): Bug fixes, minor improvements, performance optimizations

### Version History
- **1.0.0** (August 1, 2024): Initial production release
- **1.1.0** - Reserved for future minor features
- **1.2.0** (August 3, 2024): Production deployment standards & draft analytics
- **1.3.0** (August 4, 2024): Data pipeline consolidation
- **1.3.1** (August 5, 2024): Transaction display hotfix
- **1.4.0** (August 6, 2024): Player stats & health tracking
- **1.5.0** (August 7, 2024): Release notes feature & UI improvements

## Release Notes Structure

### Location
Release notes are stored in: `web-ui/frontend/src/data/releaseNotes.js`

### Data Format
Each release entry contains:
```javascript
{
  id: "YYYY-MM-DD",           // Unique identifier
  version: "X.Y.Z",            // Semantic version
  date: "Month DD, YYYY",      // Human-readable date
  title: "Brief Title",        // 3-5 word summary
  summary: "One-line description",
  highlights: [                // 3-4 key bullet points
    "User-facing change with context and details",
    "Another significant improvement or feature",
    "Important fix or enhancement"
  ],
  details: {                   // Expandable details (optional)
    features: [],              // New capabilities
    bugFixes: [],              // Issues resolved
    improvements: []           // Enhancements
  }
}
```

## Guidelines for Writing Release Notes

### User-Focused Language
- Write for end users, not developers
- Avoid technical jargon unless necessary
- Include specific numbers and metrics when helpful (e.g., "750+ MLB players")
- Explain the benefit, not just the change

### Highlights Section
- Include 3-4 bullet points maximum
- Each bullet should be a complete sentence
- Provide enough context to understand the impact
- Order by importance to users

### Details Section
- Only include if there are additional technical details
- Group by type: features, bugFixes, improvements
- Keep concise but informative

## When to Create Release Notes

### Release Notes Required For:
✅ New user-facing features
✅ UI/UX changes or improvements
✅ Performance improvements users would notice
✅ Major bug fixes that restore functionality
✅ New data sources or analytics capabilities

### Release Notes NOT Required For:
❌ Internal refactoring with no user impact
❌ Documentation updates
❌ Development tooling changes
❌ Minor text corrections
❌ Backend optimizations invisible to users

## Process for Adding Release Notes

### 1. Determine Version Number
- Bug fix only? → Increment PATCH (1.4.0 → 1.4.1)
- New feature? → Increment MINOR (1.4.1 → 1.5.0)
- Breaking change? → Increment MAJOR (1.5.0 → 2.0.0)

### 2. Update Release Notes File
Edit `web-ui/frontend/src/data/releaseNotes.js`:
1. Add new entry at the TOP of the array (newest first)
2. Use today's date and next version number
3. Write user-friendly title and summary
4. Include 3-4 detailed highlights
5. Add technical details if helpful

### 3. Test Locally
```bash
cd web-ui/frontend
npm start
# Navigate to http://localhost:3000/release-notes
# Verify formatting and content
```

### 4. Deploy with Feature
- Release notes should be deployed WITH the feature they describe
- Include in the same pull request as the feature
- Ensure version number matches the deployment

## Example Release Note

```javascript
{
  id: "2024-08-07",
  version: "1.5.0",
  date: "August 7, 2024",
  title: "Release Notes & UI Improvements",
  summary: "New release notes page and various UI enhancements",
  highlights: [
    "Access release notes directly from the navigation bar to stay updated on new features",
    "Improved mobile responsiveness across all pages for better on-the-go access",
    "Enhanced error messages provide clearer guidance when issues occur",
    "Faster page load times through optimized API caching strategies"
  ],
  details: {
    features: [
      "Release notes page with expandable details",
      "Version history tracking with semantic versioning"
    ],
    improvements: [
      "Reduced API response times by 40%",
      "Better handling of network errors",
      "Consistent styling across all components"
    ]
  }
}
```

## Maintenance

- Review release notes quarterly for accuracy
- Archive very old releases (>1 year) if list becomes too long
- Keep total release notes under 10-15 entries for performance
- Consider adding pagination if list grows beyond 15 entries

## Related Documentation
- [Deployment Process](./deployment-process.md)
- [Version Control Strategy](./version-control.md)
- [UI/UX Guidelines](./ui-guidelines.md)