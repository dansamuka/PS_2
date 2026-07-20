# Sources and limits — Phase 1 national-only scope

Generated for: **Phase 1 — Existing repo stabilisation**

## Included source snapshots

1. **PSCIMS active adverts**
   - Source: `https://pscims.publicservice.go.ke/jobs/ActiveJobsAdverts.aspx`
   - Role: official central public-service active-advert table.
   - Captured current active advert rows in the package.

2. **Kenya School of Government job application portal snapshot**
   - Source: `https://jobapplications.ke/`
   - Role: institutional application portal snapshot.
   - Marked `needs_review` because applications involve an external portal domain; cross-check the institution relationship before submitting sensitive documents.

## Included coverage scope

This package is scoped to national government and government-related institutions only:

- PSC / PSCIMS
- MDAs
- ministries and state departments
- parastatals, SAGAs and state corporations
- constitutional commissions
- independent offices
- Judiciary/Parliament service bodies
- public universities and national training/research bodies
- national hospitals and national health agencies
- all role families

## Excluded coverage scope

The following are deliberately out of scope:

- county public service boards
- county governments
- county assemblies
- ward/sub-county/local county-only roles

A duty station such as Nairobi, Mombasa, Tsavo East or Tsavo West may still appear for a national institution vacancy. That is a location field, not county-source coverage.

## Excluded from open roles

- Gmail-only adverts
- WhatsApp-only adverts
- adverts requiring payment
- screenshots or forwarded images that cannot be traced to an official source
- expired vacancies, unless clearly retained for audit/archive purposes
- county-source vacancies under the current national-only scope

## Not yet done

- Full all-MDA registry enrichment
- MyGov / Government Advertising Agency discovery collector
- PSC advert/PDF extraction
- automated detailed PSCIMS advert-details parser
- ministry vacancy page monitors
- parastatal/SAGA vacancy page monitors
- source-health alerting
- link-check automation

## Accuracy rule

Prefer fewer verified national public-sector vacancies over a large noisy feed. A role should only appear as open if it has a credible source, a `View original role` link, a status, and no scam-risk application channel.
