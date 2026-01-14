# Review Request for @rijesha

This PR completes Step 1 of the documentation restructure. I need your review before proceeding to Step 3.

## What Was Done

1. **Archived all existing documentation** to `docs/archive/`
2. **Created a new 3-tier structure:**
   - **Basics**: Quick access to common tasks (4 pages)
   - **Advanced**: Detailed technical documentation (7 pages)
   - **Reference**: Developer/contributor guides (4 pages)
3. **Created placeholder stub files** for all new documentation pages
4. **Updated mkdocs.yml** with the new navigation structure

## What I Need From You

Please review the **proposed outline** in `docs/OUTLINE.md` and answer these questions:

### Review Questions

1. **Structure**: Does the 3-tier structure (Basics/Advanced/Reference) make sense for this project?

2. **Language Examples**: Should "Language Examples" be:
   - On the home page (quick reference)
   - A separate page in Basics (as currently planned)
   - Split across language-specific pages

3. **Missing Topics**: Are there any critical topics missing from this outline?

4. **GraphQL**: Should GraphQL have its own usage examples, or is it different enough that examples aren't as useful?

5. **Consolidation**: Any concerns about the consolidated structure vs. the previous more granular approach?

6. **Content Coverage**: Looking at the archived docs, do you see any important content that should be preserved or emphasized in the new structure?

## Next Steps

Once you approve the outline (or request changes), I will:
1. Write all 15 documentation files based on the approved outline
2. Ensure clear, concise, muted tone (no AI-sounding language)
3. Include practical code examples for each language
4. Organize content for quick access to basics
5. Place advanced topics on separate pages

## Review the Outline

👉 **See `docs/OUTLINE.md` for the complete proposed structure**

The outline includes:
- Detailed content plan for each page
- Rationale for the reorganization
- Migration notes explaining the changes
- File checklist

Please comment on this PR or edit the OUTLINE.md file directly with your feedback.

---

**Current Status**: ⏳ Awaiting @rijesha review of outline before proceeding to write new documentation
