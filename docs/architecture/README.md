# Lake Protect — Architecture Pack

Target: a secure, evidence-first geospatial intelligence and case-management platform that can expand from a Hyderabad / HYDRAA pilot to a Telangana-wide, multi-department service.

## Documents
1. [Statewide platform architecture](01-statewide-platform-architecture.md)
2. [Domain and data model](02-domain-data-model.md)
3. [Geospatial data platform](03-geospatial-data-platform.md)
4. [AI/ML detection and model governance](04-ai-ml-detection.md)
5. [Application, APIs and workflows](05-application-api-workflows.md)
6. [Production, security and operations](06-production-security-operations.md)
7. [Repository assessment and migration](07-repository-assessment-migration.md)
8. [Implementation foundation](08-implementation-foundation.md)
9. [Unified platform integration and security hardening](09-unified-platform-integration.md)
10. [Production storage and event delivery](10-production-storage-and-events.md)
11. [Legacy operational-domain row-level security](11-legacy-domain-rls.md)

## Non-negotiable principles
- Department systems remain authoritative sources. Lake Protect stores traceable references or synchronised snapshots; it does not silently become the legal source of truth.
- Ownership, possession, custodianship, jurisdiction, legal protection and operational responsibility are distinct relationships.
- AI detects observable change, not illegality. Human reviewers and competent authorities make decisions.
- Every result is reproducible from source imagery, processing run, model/dataset version, boundary version, rule version and human action.
- Boundary history is immutable. Corrections create new approved versions; historical cases retain the version used at the time.
- Process imagery by geographic scene/tile, then intersect results with many assets. Never download and process a full scene independently for each lake.
- Transactional asset/case services must continue when satellite or ML processing is unavailable.
- Start with a modular backend and independent geospatial/ML workers. Extract microservices only when a measured scaling, security or ownership need exists.

## Status language
- **Current prototype:** implemented capabilities described by source code, tests and PROGRESS.md.
- **Target architecture:** design described in this pack.
- **Proposed integration:** dependent on approved access, data-sharing agreements and operational ownership.
- **Illustrative sizing:** planning ranges, not measured capacity.
- **Legal validation required:** confirm current orders, notifications, authority and procedures before operational use.

The architecture is statewide-ready as a design; statewide operational coverage requires verified data, agreements, training, security approval and acceptance testing for every participating department.
