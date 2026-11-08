# NIFTY 50 February 2018 notice audit — 2026-11-08

## Scope and status

This is a source-discovery and primary-content review note for the first 2018 anchor comparison. The official notice is now located and its indexed PDF text has been inspected. This does not authenticate locally archived PDF bytes, establish a CDX digest match, constitute independent human sign-off, or promote any transition from `SAMPLE_ONLY`.

## Primary-source notice located

Official NSE Indices PDF:

https://www.niftyindices.com/Press_Release/ind_prs21022018.pdf

The PDF identifies:
- Publisher/header: IISL / NIFTY 50
- Notice date: 21 February 2018
- Heading: "Replacements in Indices"
- Decision body: Index Maintenance Sub-Committee (IMSC) periodic review
- Effective date: 2 April 2018, at the close of 28 March 2018

The official PDF text explicitly lists the NIFTY 50 changes:

| Action | Company | Symbol |
|---|---|---|
| Exclude | Ambuja Cements Ltd. | AMBUJACEM |
| Exclude | Aurobindo Pharma Ltd. | AUROPHARMA |
| Exclude | Bosch Ltd. | BOSCHLTD |
| Include | Bajaj Finserv Ltd. | BAJAJFINSV |
| Include | Grasim Industries Ltd. | GRASIM |
| Include | Titan Company Ltd. | TITAN |

The notice also says these replacements apply to the NIFTY50 Equal Weight Index. The official PDF contains separate sections for other indices; those rows must not be accidentally ingested as NIFTY 50 transitions.

The current official archive catalogue separately lists the 21 February 2018 entry as "Change in Indices w.e.f. April 02, 2018":
https://www.niftyindices.com/media

## Evidence integrity still required

The PDF is discoverable and its indexed text is readable, but the repository has not yet recorded a locally retrieved byte-for-byte copy and integrity metadata. Before calling the PDF byte-authenticated, retrieve it from the official URL (or a digest-verified Wayback capture) and record:
- final URL, retrieval timestamp, HTTP status and response headers;
- PDF signature and EOF validation;
- byte length and SHA-256;
- CDX SHA-1 and exact replay-body match, if using Wayback.

Also inspect the complete PDF visually/textually for footnotes, corrections, or qualifications and search the later official archive for any correction/supersession. The extracted text confirms the six NIFTY 50 rows and exact effective close date; it does not substitute for byte-level integrity checks.

## Corroboration

Contemporaneous reporting by The Economic Times (22 February 2018) independently reports the same three exclusions and three inclusions:
https://economictimes.indiatimes.com/markets/stocks/news/nse-rejigs-indices-here-is-the-complete-list/articleshow/63024004.cms

A contemporaneous Zerodha Trading Q&A post (23 February 2018) also reproduces the six NIFTY 50 names/symbols and 2 April effective date:
https://tradingqna.com/t/change-in-constituents-of-nifty-50-and-other-nifty-indices/34089

These are secondary corroboration only; the official PDF is the controlling notice source.

## Audit disposition

| Item | Current disposition |
|---|---|
| Official archive catalogue date/title/effective date | Located |
| Official notice PDF URL | Located |
| Official PDF extracted text: six NIFTY 50 changes | Confirmed in indexed PDF text |
| Exact effective date and close convention | Confirmed: 2 April 2018, close of 28 March 2018 |
| Local original PDF bytes / SHA-256 | Pending |
| Wayback CDX SHA-1 replay match | Pending / not applicable if official direct bytes are successfully retrieved and retained |
| Complete visual page review and correction/supersession check | Pending |
| Independent reviewer sign-off | Pending |
| Transition register rows | Remain `SAMPLE_ONLY` |

## Next required actions

1. Retrieve and retain the exact official PDF bytes; validate PDF structure and compute SHA-256.
2. Check later official notices/catalogue entries for correction or supersession.
3. Compare the six named securities and effective close with the first anchor pair and point-in-time source records.
4. Have an independent reviewer sign off.
5. Only then consider upgrading the relevant evidence status; never infer or promote other index sections as NIFTY 50 changes.

No canonical membership interval, model, holdout, paper-trading, or live-trading state is modified by this note. The release remains on HOLD.


## Follow-up notice / supersession screen

The official NSE Indices archive also lists a 6 March 2018 notice, "Replacements in Indices". Its full text was reviewed:
https://www.niftyindices.com/Press_Release/ind_prs06032018.pdf

That notice explains that Videocon Industries had been included in various indices under the 21 February announcement, but a subsequent NSE circular moved VIDEOIND to the BZ series from 13 March. The 6 March notice then replaces VIDEOIND with ERIS, effective 13 March (close of 12 March), in exactly three listed indices: NIFTY 500, NIFTY Smallcap 250, and NIFTY MidSmallcap 400. It does **not** list NIFTY 50 among the affected indices. This is a useful scope check: the March 6 Videocon adjustment does not amend the six NIFTY 50 changes recorded above.

The same archive listing also has a 22 March 2018 item titled "Change in the Fixed Income Indices w.e.f. April 02, 2018"; its title/scope is fixed income, not NIFTY 50 equity constituents. No correction to the six NIFTY 50 rows has been identified in these follow-up entries. This is a bounded archive screen, not proof that no later correction exists anywhere.

Official archive listing: https://www.niftyindices.com/media
