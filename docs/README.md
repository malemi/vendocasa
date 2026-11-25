# VendoCasa documentation

<!-- doc-scope:start -->
Scope: Routing index for VendoCasa's durable system, valuation, data, deployment, and legal documentation. Repository ownership is defined in ../AGENTS.md; immediate work state is in active-context.md.
<!-- doc-scope:end -->

- [Active context](active-context.md): current state, unresolved questions, and next actions.
- [Active context archive](active-context-archive.md): earlier snapshots of the active context, newest first; not startup context.
- [Project overview](overview.md): product introduction, local setup, and repository layout.
- [Architecture](architecture.md): service topology, schema, agent, and request flow.
- [API](api.md): endpoint contracts and streaming responses.
- [Valuation methodology](valuation-methodology.md): estimates and correction coefficients.
- [Data sources](data-sources.md): OMI source formats and acquisition.
- [Data pipeline](data-pipeline.md): imports and semester handling.
- [Deployment](deployment.md): configuration and operational constraints.
- [Legal](legal.md): licensing and data-use constraints.
- [Harness backlog](harness-backlog.md): documentation-harness gaps and the reviewed verdicts for oversized documents.

Dated work briefs belong in `briefs/` and execution plans in `execution-plans/`. Like the earlier private working files in `brief/` and `plans/`, they are internal working documents: kept on disk, ignored by git, and not published. Test-audit decision records belong in `test-audits/`.

- [Test audit 2026-11-25](test-audits/2026-11-25-open-product.md): keep, rewrite, merge and retire decisions for the backend tests in the open-product workstream, and the evidence from real services.
