"""Submission support documents; declarations remain subject to author confirmation."""
import hashlib
import json
from pathlib import Path
import zipfile
from document_formats import blocks, html_document, pdf_document, docx_document

def prepare(root,out,study,policy,status,complete,metadata=None,release_ready=False):
    title="Source-anchored reduction of clinical data-review rules: a paired, dual-track feasibility study using CDISCPILOT01"
    documents={
        "CDISCPILOT01_Title_Page":f"""# {title}

Author: Kunal Dubey

Article type: Methods / computational feasibility study

Running title: Risk-based clinical data-review feasibility

{status}

Affiliation and postal address: author to supply.

Corresponding author: designation and contact details to be confirmed.

ORCID: author to supply if required.

Funding and competing interests: author confirmation required.
""",
        "CDISCPILOT01_Cover_Letter_Draft":f"""# Cover letter — complete before submission

To the Editor of [journal to be selected]

Dear Editor,

Please consider the manuscript “{title}” by Kunal Dubey as a methods/feasibility article.

The study compares a source-anchored reduced review plan with a specified executable comparator using paired source-level perturbations and independent SDTM-to-ADaM reconstruction. It reports query burden, mutation-level capture, and comparisons against clean outputs, while distinguishing shared blind spots from preserved statistical results.

The manuscript presents scoped descriptive evidence, not formal non-inferiority, complete clinical-error protection or validation of all CSR tables. The rule coverage gaps, reference-reconstruction exception and documentary conflicts are disclosed.

Current evidence status: {status}

Before sending this letter, the author must confirm that all results are complete, data-use permissions and ethics requirements are resolved, the work meets the journal's scope, all authors approve submission, and any originality or exclusive-submission declarations are true. No such declarations are asserted by this draft.

Sincerely,

Kunal Dubey

[Affiliation and correspondence details to be supplied]
""",
        "CDISCPILOT01_Author_Declarations":"""# Author declarations — confirmation required

Named author: Kunal Dubey

Authorship and contributions: confirm the applicable CRediT roles and that authorship criteria are met. Roles are not assigned automatically.

Funding: supply grant/support details or explicitly confirm that no relevant funding was received.

Competing interests: supply relevant interests or explicitly confirm their absence.

Ethics: confirm the institutional determination appropriate to secondary analysis of these public materials. An exemption has not been established by this document.

Data use: resolve the applicability of CDISC restrictions on altering data to the perturbation study and any redistribution; retain evidence of permission where required.

Data/code availability: confirm the permitted repository, license and persistent identifier. Local downloadable files are not a public archival deposit.

AI assistance: AI assistance was used for software development and manuscript drafting. Confirm human verification and responsibility, and adapt the disclosure to the journal's requirements.

Publication declarations: confirm originality, prior dissemination, exclusive submission and author approval as required by the selected journal. None is presumed.

Signature and date: to be supplied after review.
""",
        "CDISCPILOT01_Highlights":"""# Manuscript highlights

Source-linked rule selection was evaluated in a paired pilot-data experiment.

Critical-error capture was separated from statistical-output preservation.

Shared missed mutations were audited by identity, not only aggregate counts.

Clean-reference comparisons prevent agreement from concealing shared errors.

The study is scoped feasibility, not universal safety or CSR certification.
""",
    }
    if release_ready:
        m=metadata
        documents["CDISCPILOT01_Title_Page"]=f"# {title}\n\nAuthor: Kunal Dubey\n\nAffiliation: {m['affiliation']}\n\nCorrespondence: {m['corresponding_email']}\n\nORCID: {m['orcid']}\n\nTarget journal: {m['target_journal']}\n\n{status}"
        documents["CDISCPILOT01_Author_Declarations"]="# Author declarations\n\nAuthor: Kunal Dubey\n\n"+"\n\n".join(f"{k.replace('_',' ').title()}: {v}" for k,v in m.items())+"\n\nAI assistance was used in software development and manuscript drafting. Human author verification and responsibility apply."
        documents["CDISCPILOT01_Cover_Letter_Draft"]=f"# Cover letter\n\nDear Editor of {m['target_journal']},\n\nPlease consider “{title}” by Kunal Dubey as a methods/feasibility article. The completed scoped study reports query burden, mutation-level capture and clean-reference comparisons, with explicit shared detection limitations. It does not claim universal safety or full CSR validation.\n\nSincerely,\n\nKunal Dubey\n\n{m['affiliation']}\n\n{m['corresponding_email']}"
    names=[]
    for stem,text in documents.items():
        parts=blocks(text)
        docx_document(parts,out/(stem+".docx"))
        pdf_document(html_document(parts),out/(stem+".pdf"),release_ready=release_ready)
        names += [stem+".docx",stem+".pdf"]
    code_name="CDISCPILOT01_Reproducibility_Code.zip"
    with zipfile.ZipFile(out/code_name,"w",zipfile.ZIP_DEFLATED) as archive:
        for name,digest in policy["codeHashes"].items():
            p=out/"reporting-revisions/frozen_export_scoped_study.py" if name=="export_scoped_study.py" else root/"scripts/clinical"/name
            assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
            archive.write(p,"scripts/clinical/"+name)
        archive.write(root/"scripts/clinical/export_scoped_study.py","reporting_revision/export_scoped_study.py")
        archive.write(out/"reporting-revisions/protected-hashes.json","audit/protected-hashes.json")
        archive.writestr("reporting_revision/README.txt","Reporting-only revision. Original exporter remains under scripts/clinical with its frozen hash. To use the revised publisher in a permitted reconstructed workspace, preserve that original exporter as generated-artifacts/clinical/reporting-revisions/frozen_export_scoped_study.py, place audit/protected-hashes.json alongside it, then copy reporting_revision/export_scoped_study.py to scripts/clinical/export_scoped_study.py. Restore the exact saved scoped_results.json and policy files at their original paths. No clinical experiment rerun is needed for reporting. --release-ready requires all ten author_metadata.json fields to be populated; metadata completeness is not independent verification of author declarations.")
        template=root/"scripts/clinical/input/template.xlsx"
        archive.write(template,str(template.relative_to(root)))
        archive.write(study/"frozen_policy.json","audit/frozen_policy.json")
        archive.write(study/"policy.sha256","audit/policy.sha256")
        for p in (root/"scripts/publication").iterdir():
            if p.suffix in (".py",".md",".json"):archive.write(p,str(p.relative_to(root)))
        archive.writestr("README.txt","""Reproducibility code supplement — Kunal Dubey

This archive contains the frozen analysis scripts, their input rule template,
publication-reporting code and frozen policy. It contains no cached XPT datasets
or reference PDFs/XML files. Data-use permissions remain unresolved.

The original rule template contains hypotheses and unverified catalogue claims;
it is an executable input, not a report of confirmed results.

To reproduce the study, use a separate clean workspace with the original layout,
the permitted cached inputs listed in audit/frozen_policy.json at their specified
paths, and the package versions recorded in Publication_Evidence_Snapshot.json.
Do not overwrite or alter the original study's locked outputs.

The scientific entry point is python scripts/clinical/run_scoped_study.py.
Running it performs a new reconstruction and challenge experiment; it was NOT
run to assemble this submission package. The reporting-only entry point is
python scripts/publication/build_publication.py --require-complete.

Reproduction requires the source cache; this code-only archive is not a
self-contained executable dataset. Confirm permissions before sharing any
data or source-derived materials. No redistribution license is granted here.
""")
    names.append(code_name)
    readme=f"""# Submission package guide

Author: Kunal Dubey

Status: {status}

## Main submission files

- CDISCPILOT01_Manuscript_Draft.docx — editable main manuscript.
- CDISCPILOT01_Manuscript_Draft.pdf — review copy.
- CDISCPILOT01_Title_Page.docx — author/title metadata.
- CDISCPILOT01_Cover_Letter_Draft.docx — complete for the selected journal.
- CDISCPILOT01_Highlights.docx — optional journal highlights.
- CDISCPILOT01_Author_Declarations.docx — confirm, do not submit unverified statements.

## Supporting material

- CDISCPILOT01_Publication_Results.xlsx — supplementary tables and audit.
- Publication_Evidence_Snapshot.json — exact result snapshot and environment.
- CDISCPILOT01_Reproducibility_Code.zip — frozen code and input rule template; no source datasets.
- CDISCPILOT01_Submission_Checklist.md — outstanding release checks.
- Manuscript_Paired_Intervention_Figure.png — {'included when the completed-study figure is available' if complete else 'pending; will be added after the study finishes'}.

The journal may require different file names, a blinded manuscript, special
disclosure forms, a graphical abstract or different figure formats. These cannot
be certified without a selected journal. Author affiliation/contact details,
ethics, funding/conflicts and data-use permissions remain to be confirmed.

The package is for author review, not an automatic journal submission.
"""
    if release_ready:
        readme=readme.replace("Author affiliation/contact details,\nethics, funding/conflicts and data-use permissions remain to be confirmed.","Required author metadata and declarations have been populated. Their truth and journal-specific requirements remain the author's responsibility.").replace("The package is for author review, not an automatic journal submission.","Release metadata checks passed; no journal submission was performed.")
    readme+="\nReporting revision: the frozen clinical exporter is preserved in the code archive. The updated exporter is separately provided under reporting_revision; frozen policy/result hashes were not rewritten. The 118,482-cell denominator is per comparison, not pooled.\n"
    (out/"CDISCPILOT01_Submission_README.md").write_text(readme)
    names.append("CDISCPILOT01_Submission_README.md")
    return names
