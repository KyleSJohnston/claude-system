# Research Brief Template

<!--
@decision DEC-ARCH-004
@title Research brief template structure for /architect --research Phase 2
@status accepted
@rationale Template-based approach with explicit PLACEHOLDER markers (matching
mermaid-module-dependency.md pattern) lets the skill populate batch-specific
context before dispatching to /deep-research. Markers are keyed strings, not
positional, so population order doesn't matter and validation is grep-able.
Includes cross-batch dependency section to give researchers full context even
when related nodes land in different batches.
-->

Used by /architect Phase 2 to generate focused research queries per node batch.
Populate the PLACEHOLDER sections with manifest.json node data before dispatching to /deep-research.

---

## Template

# Research Brief: PLACEHOLDER: project-name

## Target Structure

This is a PLACEHOLDER: content-type project.
PLACEHOLDER: language-framework-context

## Nodes in This Batch

PLACEHOLDER: batch-nodes
Format each node as:
- **[Node Name]** ([type]): [description]
  - Path: [relative path]
  - Files: [count] | LOC: [count] | Complexity: [level]
  - Key files: [list]

## Relationships Within This Batch

PLACEHOLDER: batch-relationships
Format:
- [Source Node] --[edge-type]--> [Target Node]: [description]

## Cross-Batch Dependencies

PLACEHOLDER: external-edges
Nodes in this batch that connect to nodes in other batches:
- [Node] --[edge-type]--> [External Node] (not in this batch)

## Research Questions

For each node in this batch, investigate:

1. **Patterns & Anti-patterns:** What are established best practices for components of this type ([types])? What anti-patterns should be avoided?
2. **Failure Modes:** What are common failure modes, performance bottlenecks, or reliability risks for this type of component?
3. **Technical Debt Signals:** What indicators suggest accumulated technical debt? Which files or patterns are red flags?
4. **Improvement Opportunities:** What specific, actionable improvements would increase maintainability, performance, or reliability?
5. **Architectural Coupling:** Are there coupling issues between the nodes in this batch? Between this batch and the rest of the system?

## Context

PLACEHOLDER: system-context
Brief dependency summary of the overall project structure (from manifest system diagram description).

---

## How to Populate

1. Replace PLACEHOLDER: project-name with the project name (from manifest root path basename)
2. Replace PLACEHOLDER: content-type with manifest.content_type
3. Replace PLACEHOLDER: language-framework-context with language and framework info from detect_info
4. For each node in the batch, populate the batch-nodes section from manifest node data
5. For edges where BOTH source and target are in this batch, list under batch-relationships
6. For edges where source is in this batch but target is NOT, list under external-edges
7. Replace PLACEHOLDER: system-context with a brief structural summary
