"""
ai_engine.py  –  CourtReady Legal Analysis Engine (v2)
=======================================================
Architecture:
  • NO heavy ML models (no BERT, no torch, no sentence-transformers).
  • Static CPC 1908 knowledge base – one KB per dispute category.
  • Gemini API selects the 3 most contextually relevant provisions
    AND generates the full legal analysis in a single API call.
  • In-memory response cache keyed on (category, SHA-256 of description)
    for sub-second repeat queries.
  • Falls back through MODEL_HIERARCHY (re-used from processing.py)
    if any model is rate-limited or unavailable.
"""

import os
import json
import hashlib
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ── Gemini Configuration ────────────────────────────────────────────────────
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("CRITICAL WARNING: GEMINI_API_KEY not found in environment variables.")
else:
    genai.configure(api_key=api_key)

MODEL_HIERARCHY = [
    "gemini-flash-lite-latest",
    "gemma-3-4b-it",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-pro-latest",
]

# ── In-Memory Response Cache ─────────────────────────────────────────────────
_RESPONSE_CACHE: dict = {}


def _cache_key(category: str, description: str) -> str:
    digest = hashlib.sha256(description.strip().lower().encode()).hexdigest()
    return f"{category}::{digest}"


# ════════════════════════════════════════════════════════════════════════════
# STATIC KNOWLEDGE BASE  –  Code of Civil Procedure, 1908 (Last Amended 2016)
# ════════════════════════════════════════════════════════════════════════════

# Every entry follows this schema:
# {
#   "source_title": "<Act + Section/Order reference>",
#   "source_text":  "<verbatim or faithfully-paraphrased provision>",
#   "source_category": "<one of the three dispute types>",
# }

# ── 1. FAMILY DISPUTES ───────────────────────────────────────────────────────

FAMILY_KB = [
    {
        "source_title": "CPC 1908 – Section 9: Courts to Try Civil Suits",
        "source_text": (
            "The Courts shall (subject to the provisions herein contained) have jurisdiction to try all "
            "suits of a civil nature excepting suits of which their cognizance is either expressly or "
            "impliedly barred. A suit in which the right to property or to an office is contested is a "
            "suit of a civil nature, notwithstanding that such right may depend entirely on the decision "
            "of questions as to religious rites or ceremonies."
        ),
        "source_category": "CPC 1908 – Family Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 10: Stay of Suit (Pending Proceedings)",
        "source_text": (
            "No Court shall proceed with the trial of any suit in which the matter in issue is also "
            "directly and substantially in issue in a previously instituted suit between the same parties, "
            "or between parties under whom they or any of them claim litigating under the same title, "
            "where such suit is pending in the same or any other Court in Pakistan having jurisdiction "
            "to grant the relief claimed. A family court cannot proceed where an identical matter between "
            "the same parties is already pending."
        ),
        "source_category": "CPC 1908 – Family Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 11: Res Judicata",
        "source_text": (
            "No Court shall try a suit or issue in which the matter directly and substantially in issue "
            "has been directly and substantially in issue in a former suit between the same parties, or "
            "between parties under whom they or any of them claim, litigating under the same title, in a "
            "Court competent to try such subsequent suit or the suit in which such issue has been "
            "subsequently raised, and has been heard and finally decided by such Court. Once a family "
            "dispute (e.g., maintenance, dower, custody) is decided by a competent court, the same "
            "matter cannot be re-litigated between the same parties."
        ),
        "source_category": "CPC 1908 – Family Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 12: Bar to Further Suits",
        "source_text": (
            "Where a plaintiff is precluded by rules from instituting a further suit in respect of any "
            "particular cause of action, he shall not be entitled to institute a suit in respect of such "
            "cause of action in any Court to which this Code applies. This bars re-filing of dismissed "
            "family suits on the same cause of action."
        ),
        "source_category": "CPC 1908 – Family Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 20: Place of Institution of Suit (Personal / Family Disputes)",
        "source_text": (
            "Subject to the limitations aforesaid, every suit shall be instituted in a Court within the "
            "local limits of whose jurisdiction: (a) the defendant, at the time of the commencement of "
            "the suit, actually and voluntarily resides, or carries on business, or personally works for "
            "gain; or (b) any of the defendants, where there are more than one, resides or carries on "
            "business; or (c) the cause of action, wholly or in part, arises. In family disputes such as "
            "maintenance, restitution of conjugal rights, or dissolution of marriage, the suit is typically "
            "instituted where the defendant resides or where the marriage took place."
        ),
        "source_category": "CPC 1908 – Family Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 26: Institution of Suits",
        "source_text": (
            "Every suit shall be instituted by the presentation of a plaint or in such other manner as "
            "may be prescribed. For family matters, the plaint must contain the facts constituting the "
            "cause of action and the relief claimed, filed before the competent Family Court or Civil "
            "Court as applicable under the West Pakistan Family Courts Act, 1964."
        ),
        "source_category": "CPC 1908 – Family Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 35: Costs in Suit",
        "source_text": (
            "Subject to such conditions and limitations as may be prescribed, and to the provisions of "
            "any law for the time being in force, the costs of and incident to all suits shall be in the "
            "discretion of the Court, and the Court shall have full power to determine by whom or out of "
            "what property and to what extent such costs are to be paid. In family proceedings, courts "
            "regularly award costs against the party who delays or obstructs proceedings."
        ),
        "source_category": "CPC 1908 – Family Disputes",
    },
    {
        "source_title": "CPC 1908 – Order XXI Rule 33: Execution of Decree for Restitution of Conjugal Rights",
        "source_text": (
            "A decree for restitution of conjugal rights shall not be executed by attachment and sale of "
            "the judgment-debtor's property or by arrest and detention in prison. The Court has discretion "
            "in executing such decrees. Where a decree for restitution of conjugal rights remains "
            "unsatisfied for one year, under Section 2(ix)(b) of the Muslim Family Laws Ordinance 1961, "
            "the wife may treat such non-compliance as a ground for dissolution."
        ),
        "source_category": "CPC 1908 – Family Disputes",
    },
    {
        "source_title": "CPC 1908 – Order XXXII: Suits by or Against Minors and Persons of Unsound Mind",
        "source_text": (
            "Rule 1: A minor shall sue by a next friend. Rule 3: For a minor defendant, the Court shall "
            "appoint a guardian for the suit. Rule 4: Any person who is of sound mind and not under any "
            "disability may act as next friend or guardian for the suit, provided no adverse interest "
            "exists. Rule 7: No agreement, compromise or satisfaction in respect of a minor shall be "
            "recorded unless the Court is satisfied that it is for the benefit of the minor. These rules "
            "are critical in custody disputes and proceedings involving minor children."
        ),
        "source_category": "CPC 1908 – Family Disputes",
    },
    {
        "source_title": "CPC 1908 – Order XXXIII: Suits by Paupers (Indigent Persons)",
        "source_text": (
            "Rule 1: Any person entitled to institute a suit may do so as a pauper if he is not possessed "
            "of sufficient means to pay the fee prescribed for such a plaint. Rule 5: The application "
            "shall be rejected if the applicant is not subject to genuine poverty, the suit appears barred "
            "by law, or no prima facie case exists. This provision allows impoverished spouses or "
            "dependants to pursue family law claims without paying court fees upfront."
        ),
        "source_category": "CPC 1908 – Family Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 94: Supplemental Proceedings (Injunction / Receiver in Family Matters)",
        "source_text": (
            "In order to prevent the ends of justice from being defeated the Court may, where it is so "
            "prescribed, (a) issue a warrant to arrest the defendant and bring him before the Court; "
            "(b) direct the defendant to furnish security to produce any property; (c) grant a temporary "
            "injunction and in cases of disobedience commit the person to prison and order his properties "
            "to be attached; (d) appoint a receiver of any property. In family matters, temporary "
            "injunctions are frequently sought to prevent disposal of matrimonial assets or dower property "
            "pending suit."
        ),
        "source_category": "CPC 1908 – Family Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 51: Powers of Court to Enforce Execution of Decree",
        "source_text": (
            "Subject to such conditions and limitations as may be prescribed, the Court may, on the "
            "application of the decree-holder, order execution of the decree: (a) by delivery of any "
            "property specifically decreed; (b) by attachment and sale or by sale without attachment of "
            "any property; (c) by arrest and detention in prison; (d) by appointing a receiver. Execution "
            "by detention in prison shall not be ordered unless the Court, after giving the judgment-debtor "
            "an opportunity to show cause, is satisfied it is justified. A maintenance or dower decree "
            "against a husband may be executed through attachment of his salary or property."
        ),
        "source_category": "CPC 1908 – Family Disputes",
    },
    {
        "source_title": "West Pakistan Family Courts Act, 1964 – Section 5: Exclusive Jurisdiction of Family Courts",
        "source_text": (
            "(1) Subject to the provisions of the Muslim Family Laws Ordinance, 1961, and the Conciliation "
            "Courts Ordinance, 1961, the Family Courts shall have exclusive jurisdiction to entertain, hear "
            "and adjudicate upon matters specified in Part I of the Schedule.\n\n"
            "Part I of the Schedule includes:\n"
            "(i) dissolution of marriage;\n"
            "(ii) dower;\n"
            "(iii) maintenance;\n"
            "(iv) restitution of conjugal rights;\n"
            "(v) custody of children;\n"
            "(vi) visitation rights of parents to meet children;\n"
            "(vii) jahiz (dowry) and dowry articles;\n"
            "(viii) recovery of personal property and belongings of wife;\n"
            "(ix) injunctions in family matters;\n"
            "(x) declaration pertaining to marital status.\n\n"
            "(2) Notwithstanding anything contained in the Code of Criminal Procedure, 1898, the Family Court "
            "shall have jurisdiction to try the offences specified in Part II of the Schedule, where one of "
            "the spouses is victim of an offence committed by the other."
        ),
        "source_category": "Family Courts Act 1964 – Family Disputes",
    },
    {
        "source_title": "West Pakistan Family Courts Act, 1964 – Section 17: Non-application of CPC and Evidence Act",
        "source_text": (
            "Save as otherwise expressly provided in this Act or any rules made thereunder, the provisions "
            "of the Code of Civil Procedure, 1908, and the Evidence Act, 1872, shall not apply to proceedings "
            "before a Family Court.\n\n"
            "However, the Family Court is guided by principles of natural justice and substantive justice, "
            "unencumbered by technical rules of procedure and evidence."
        ),
        "source_category": "Family Courts Act 1964 – Family Disputes",
    },
    {
        "source_title": "West Pakistan Family Courts Act, 1964 – Section 10: Pre-trial Proceedings",
        "source_text": (
            "(1) When the written statement is filed, the Family Court shall, within seven days, fix an "
            "early date for pre-trial hearing of the suit and shall adjourn the suit for pre-trial hearing.\n"
            "(2) At the pre-trial hearing, the Court shall examine the plaint, the written statement, and "
            "any documents filed by the parties, and shall also discuss with the parties the possibility of "
            "an amicable settlement.\n"
            "(3) The Court shall, at the pre-trial hearing, also:\n"
            "(a) decide the question of the legal representatives of a deceased party;\n"
            "(b) fix the number of witnesses to be produced by each party;\n"
            "(c) record admissions and denials;\n"
            "(d) frame issues;\n"
            "(e) fix a date for recording evidence.\n"
            "(4) Where a decree is to be passed on the basis of a compromise, the provisions of this section "
            "shall not apply."
        ),
        "source_category": "Family Courts Act 1964 – Family Disputes",
    },
    {
        "source_title": "West Pakistan Family Courts Act, 1964 – Section 12: Time Limit for Disposal",
        "source_text": (
            "The Family Court shall fix a date for recording evidence which shall not ordinarily exceed thirty "
            "days from the date of framing of issues, and after recording evidence, the Court shall hear "
            "arguments and pronounce judgment within thirty days. Section 12A further mandates that suits "
            "under this Act shall be disposed of within six months from the date of institution, which may "
            "be extended for a further period of six months with written reasons to be recorded."
        ),
        "source_category": "Family Courts Act 1964 – Family Disputes",
    },
    {
        "source_title": "West Pakistan Family Courts Act, 1964 – Section 13: Execution of Decrees",
        "source_text": (
            "(1) A decree passed by a Family Court shall be executed by the same Court in accordance with the "
            "provisions of the Code of Civil Procedure, 1908, as if the Family Court were a Civil Court.\n"
            "(2) The Family Court shall have all the powers for execution of its decrees as are vested in a "
            "Civil Court under the Code of Civil Procedure, 1908.\n"
            "(3) For purposes of execution of its decrees, the Family Court shall be deemed to be a Civil Court "
            "and shall have all the powers of a Civil Court for the purposes of the Code of Civil Procedure."
        ),
        "source_category": "Family Courts Act 1964 – Family Disputes",
    },
    {
        "source_title": "West Pakistan Family Courts Act, 1964 – Section 7(2) Proviso: Consolidation of Claims",
        "source_text": (
            "Provided that a plaint for dissolution of marriage may contain all claims relating to dowry, "
            "maintenance, dower, personal property and belongings of wife, custody of children and visitation "
            "rights of parents to meet their children."
        ),
        "source_category": "Family Courts Act 1964 – Family Disputes",
    },
    {
        "source_title": "West Pakistan Family Courts Act, 1964 – Section 9(1a) and (1b): Cross Claims",
        "source_text": (
            "(1a) A defendant husband may, where no earlier suit for restitution of conjugal rights is pending, "
            "claim for a decree of restitution of conjugal rights in his written statement to a suit for "
            "dissolution of marriage or maintenance, which shall be deemed as a plaint and no separate suit "
            "shall lie for it.\n"
            "(1b) A defendant wife may, in the written statement to a suit for restitution of conjugal rights, "
            "make a claim for dissolution of marriage including khula which shall be deemed as a plaint and no "
            "separate suit shall lie for it: Provided that the proviso to sub-section (4) of Section 10 shall "
            "apply where the decree for dissolution of marriage is to be passed on the ground of khula."
        ),
        "source_category": "Family Courts Act 1964 – Family Disputes",
    },
    {
        "source_title": "West Pakistan Family Courts Act, 1964 – Section 21A: Interim Orders",
        "source_text": (
            "A Family Court may, at any stage of a suit, pass such interim orders as it may deem fit, including "
            "orders for the grant of interim maintenance, custody or visitation rights, or injunction, and may "
            "vary or discharge such orders."
        ),
        "source_category": "Family Courts Act 1964 – Family Disputes",
    },
    {
        "source_title": "West Pakistan Family Courts Act, 1964 – Section 25: Deemed District Court for Guardianship",
        "source_text": (
            "A Family Court shall be deemed to be a District Court for purposes of the Guardians and Wards Act, "
            "1890, and shall have all the powers of a District Court under that Act."
        ),
        "source_category": "Family Courts Act 1964 – Family Disputes",
    },
    {
        "source_title": "West Pakistan Family Courts Rules, 1965 – Rule 6: Territorial Jurisdiction",
        "source_text": (
            "The Court which shall have jurisdiction to try a suit will be that within the local limits of which:\n"
            "(a) the cause of action wholly or in part has arisen; or\n"
            "(b) where the parties reside or last resided together.\n"
            "Provided that in suits for dissolution of marriage or dower, the Court within the local limits of "
            "which the wife ordinarily resides shall also have jurisdiction.\n\n"
            "As per Rule 2(e), a 'suit' includes an application for guardianship under the Guardians and Wards Act."
        ),
        "source_category": "Family Courts Rules 1965 – Family Disputes",
    },
    {
        "source_title": "Case Law: Muhammad Khalid Karim v. Saadia Yaqub (PLD 2012 SC 66)",
        "source_text": (
            "The Honourable Supreme Court held that for guardianship matters, the territorial jurisdiction of "
            "the Family Court is governed by Rule 6 of the Family Courts Rules, 1965 and not by the provisions "
            "of the Guardians and Wards Act, 1890. Under Rule 6(a), in custody or guardianship disputes, if "
            "the minors were with the mother and have been illegally removed, the cause of action arises at "
            "the place where they were living; otherwise, the cause of action shall be deemed to have arisen "
            "where the minors are residing."
        ),
        "source_category": "Case Law – Family Disputes",
    },
    {
        "source_title": "Muslim Family Laws Ordinance, 1961 – Section 9: Maintenance",
        "source_text": (
            "(1) If any husband fails to maintain his wife adequately, or where there are more wives than one, "
            "fails to maintain them equitably, the wife, or all or any of the wives, may in addition to seeking "
            "any other legal remedy, apply to the Arbitration Council for maintenance.\n"
            "(2) The Arbitration Council may, if satisfied after summary inquiry that the husband has failed to "
            "maintain his wife adequately, or where there are more wives than one, has failed to maintain them "
            "equitably, issue a certificate specifying the amount which shall be paid as maintenance by the "
            "husband.\n"
            "(3) A maintenance certificate issued under this section shall be enforceable as a decree of a "
            "Civil Court and may be executed in the same manner as a decree."
        ),
        "source_category": "Muslim Family Laws Ordinance 1961 – Family Disputes",
    },
    {
        "source_title": "Muslim Family Laws Ordinance, 1961 – Section 7: Talaq (Divorce) Procedure",
        "source_text": (
            "(1) Any man who wishes to divorce his wife shall, as soon as may be after the pronouncement of "
            "talaq in any form whatsoever, give the Chairman notice in writing of his having done so, and shall "
            "supply a copy thereof to the wife.\n"
            "(2) Whoever contravenes the provisions of sub-section (1) shall be punishable with simple "
            "imprisonment for a term which may extend to one year or with fine which may extend to Rs. 5,000 "
            "or with both.\n"
            "(3) Save as provided in sub-section (5), a talaq unless revoked earlier, expressly or otherwise, "
            "shall not be effective until the expiration of ninety days from the day on which notice under "
            "sub-section (1) is delivered to the Chairman.\n"
            "(4) Within thirty days of the receipt of notice under sub-section (1), the Chairman shall "
            "constitute an Arbitration Council for the purpose of bringing about a reconciliation between the "
            "parties.\n"
            "(5) If the wife is pregnant at the time talaq is pronounced, talaq shall not be effective until "
            "the pregnancy ends or the expiration of ninety days, whichever is later."
        ),
        "source_category": "Muslim Family Laws Ordinance 1961 – Family Disputes",
    },
    {
        "source_title": "Dissolution of Muslim Marriages Act, 1939 – Section 2: Grounds for Decree",
        "source_text": (
            "A woman married under Muslim law shall be entitled to obtain a decree for the dissolution of her "
            "marriage on any one or more of the following grounds, namely:\n"
            "(i) whereabouts of the husband unknown for four years;\n"
            "(ii) husband's failure to provide maintenance for two years;\n"
            "(iii) husband sentenced to imprisonment for seven years or more;\n"
            "(iv) husband's failure to perform marital obligations for three years;\n"
            "(v) husband impotent at the time of marriage and continues to be so;\n"
            "(vi) husband insane, suffering from leprosy or virulent venereal disease;\n"
            "(vii) marriage was contracted when she was minor by father or guardian, and she repudiates before "
            "attaining 18 years (option of puberty);\n"
            "(viii) husband treats her with cruelty, including: habitual assault, making life miserable by "
            "unlawful conduct, associating with women of ill-repute, attempting to force her into immoral life, "
            "disposing of her property, obstructing her religious practices, or inequitable treatment if more "
            "than one wife;\n"
            "(ix) any other ground recognized by Muslim law."
        ),
        "source_category": "Dissolution of Muslim Marriages Act 1939 – Family Disputes",
    },
    {
        "source_title": "Guardians and Wards Act, 1890 – Section 17: Matters to be Considered by Court",
        "source_text": (
            "(1) In appointing or declaring the guardian of a minor, the Court shall be guided by what, "
            "consistently with the law to which the minor is subject, appears in the circumstances to be for "
            "the welfare of the minor.\n"
            "(2) The Court shall consider the age, sex, and religion of the minor, the character and capacity "
            "of the proposed guardian, the wishes of the deceased parent, and any existing or previous relations "
            "of the proposed guardian with the minor or his property.\n"
            "(3) If the minor is old enough to form an intelligent preference, the Court may consider that "
            "preference.\n"
            "(5) The Court shall not appoint or declare any person to be a guardian against his will."
        ),
        "source_category": "Guardians and Wards Act 1890 – Family Disputes",
    },
]

# ── 2. CONTRACT DISPUTES ─────────────────────────────────────────────────────

CONTRACT_KB = [
    {
        "source_title": "CPC 1908 – Section 9: Courts to Try Civil Suits (Including Contract Suits)",
        "source_text": (
            "The Courts shall (subject to the provisions herein contained) have jurisdiction to try all "
            "suits of a civil nature excepting suits of which their cognizance is either expressly or "
            "impliedly barred. Contract suits, including suits for recovery of money, breach of contract, "
            "specific performance, and damages, are suits of a civil nature and are cognizable by civil "
            "courts unless barred by a specific statute."
        ),
        "source_category": "CPC 1908 – Contract Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 11: Res Judicata (Contract Disputes)",
        "source_text": (
            "No Court shall try a suit or issue in which the matter directly and substantially in issue "
            "has been directly and substantially in issue in a former suit between the same parties, "
            "litigating under the same title, in a Court competent to try such subsequent suit, and "
            "has been heard and finally decided by such Court. A contract dispute already adjudicated "
            "between the same parties cannot be re-filed before another court."
        ),
        "source_category": "CPC 1908 – Contract Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 20: Where Contract Suits Are to Be Instituted",
        "source_text": (
            "Subject to the limitations aforesaid, every suit shall be instituted in a Court within the "
            "local limits of whose jurisdiction: (a) the defendant, at the time of commencement of the "
            "suit, actually and voluntarily resides, carries on business, or personally works for gain; "
            "or (b) any of the defendants, where there are more than one, resides or carries on business; "
            "or (c) the cause of action, wholly or in part, arises. In contract disputes, the cause of "
            "action typically arises where the contract was made, where it was to be performed, or where "
            "the breach occurred."
        ),
        "source_category": "CPC 1908 – Contract Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 26: Institution of Suit by Plaint",
        "source_text": (
            "Every suit shall be instituted by the presentation of a plaint or in such other manner as "
            "may be prescribed. A contract suit must be initiated by filing a plaint before the "
            "competent Civil Court. The plaint must disclose the material facts constituting the breach "
            "of contract, the loss suffered, and the relief claimed (money decree, specific performance, "
            "injunction, etc.)."
        ),
        "source_category": "CPC 1908 – Contract Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 34: Interest on Money Decrees",
        "source_text": (
            "Where and in so far as a decree is for the payment of money, the Court may, in the decree, "
            "order interest at such rate as the Court deems reasonable to be paid on the principal sum "
            "adjudged, from the date of the suit to the date of the decree, in addition to any interest "
            "adjudged on such principal sum for any period prior to the institution of the suit, with "
            "further interest at such rate as the Court deems reasonable on the aggregate sum so adjudged, "
            "from the date of the decree to the date of payment. This is the primary provision for "
            "recovering contractual interest and post-decree interest in money suits."
        ),
        "source_category": "CPC 1908 – Contract Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 35: Costs in Contract Suits",
        "source_text": (
            "The costs of and incident to all suits shall be in the discretion of the Court, and the "
            "Court shall have full power to determine by whom or out of what property and to what extent "
            "such costs are to be paid. Section 35-A provides for compensatory costs not exceeding "
            "Rs. 3,000 against a party who raises false or vexatious claims or defences in contract "
            "disputes. Courts ordinarily award costs to the successful party."
        ),
        "source_category": "CPC 1908 – Contract Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 51: Execution of Money Decree Against Judgment-Debtor",
        "source_text": (
            "The Court may, on the application of the decree-holder, order execution of the decree: "
            "(a) by delivery of any property specifically decreed; (b) by attachment and sale or by sale "
            "without attachment of any property; (c) by arrest and detention in prison (subject to "
            "conditions); (d) by appointing a receiver. A money decree passed in a contract suit may be "
            "executed by attachment and sale of the judgment-debtor's moveable or immoveable property."
        ),
        "source_category": "CPC 1908 – Contract Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 64: Private Alienation of Property After Attachment Is Void",
        "source_text": (
            "Where an attachment has been made, any private transfer or delivery of the property attached "
            "or of any interest therein and any payment to the judgment-debtor of any debt, dividend or "
            "other monies contrary to such attachment, shall be void as against all claims enforceable "
            "under the attachment. This prevents a judgment-debtor in a contract dispute from dissipating "
            "assets after the court has ordered attachment."
        ),
        "source_category": "CPC 1908 – Contract Disputes",
    },
    {
        "source_title": "CPC 1908 – Order XXXVII: Summary Procedure on Negotiable Instruments",
        "source_text": (
            "Rule 1: This Order applies to suits upon bills of exchange, hundies, promissory notes, and "
            "other negotiable instruments. Rule 2: The plaintiff in a summary suit must, along with the "
            "summons, serve a copy of the plaint and of the exhibits; the defendant is not entitled to "
            "defend the suit unless he obtains leave from the Court. Rule 3: The defendant may obtain "
            "leave to appear and defend the suit only if he discloses facts which the Court deems "
            "sufficient to entitle him to defend. This procedure allows swift enforcement of dishonoured "
            "cheques, promissory notes, and trade finance instruments."
        ),
        "source_category": "CPC 1908 – Contract Disputes",
    },
    {
        "source_title": "CPC 1908 – Order XXXVI: Special Case (Agreement Referred to Court)",
        "source_text": (
            "Rule 1: If parties to a dispute agree in writing to state their case for the Court's "
            "opinion, the agreement shall be filed and registered as a suit. Rule 3: Once registered, "
            "it is treated as a suit and the parties are subject to the Court's jurisdiction. Rule 5: "
            "The Court hears and disposes of the case as if it were an ordinary suit. This is useful "
            "for commercial contract disputes where parties agree to submit a defined legal question "
            "to the Court without the full trial process."
        ),
        "source_category": "CPC 1908 – Contract Disputes",
    },
    {
        "source_title": "CPC 1908 – Order XXXVIII: Arrest and Attachment Before Judgment",
        "source_text": (
            "Rule 1: Where at any stage of a suit the Court is satisfied, by affidavit or otherwise, "
            "that the defendant has absconded or left the jurisdiction, or is about to remove his "
            "property from the jurisdiction, or has disposed of or is about to dispose of property with "
            "intent to obstruct or delay execution of a decree, the Court may issue a warrant for his "
            "arrest or direct furnishing of security. Rule 5: The Court may order attachment before "
            "judgment to prevent dissipation of assets. This is a crucial remedy in contract disputes "
            "where there is a risk of the debtor removing or dissipating assets before the decree."
        ),
        "source_category": "CPC 1908 – Contract Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 94: Temporary Injunction in Contract Disputes",
        "source_text": (
            "In order to prevent the ends of justice from being defeated the Court may grant a temporary "
            "injunction and in cases of disobedience, commit the person to prison and order his properties "
            "to be attached and sold. A temporary injunction in a contract dispute may be sought to "
            "restrain the other party from breaching a negative stipulation, from using confidential "
            "information, or from disposing of specific goods that are the subject-matter of the contract. "
            "The Court must be satisfied of a prima facie case, balance of convenience, and irreparable harm."
        ),
        "source_category": "CPC 1908 – Contract Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 13: When Foreign Judgment Is Not Conclusive (International Contracts)",
        "source_text": (
            "A foreign judgment shall be conclusive as to any matter thereby directly adjudicated upon "
            "between the same parties except: (a) where it has not been pronounced by a Court of "
            "competent jurisdiction; (b) where it has not been given on the merits of the case; "
            "(c) where it appears to be founded on an incorrect view of international law or a refusal "
            "to recognise the law of Pakistan; (d) where the proceedings are opposed to natural justice; "
            "(e) where it was obtained by fraud. Relevant in cross-border commercial contracts where "
            "a foreign arbitral award or court judgment is sought to be enforced in Pakistan."
        ),
        "source_category": "CPC 1908 – Contract Disputes",
    },
    {
        "source_title": "Contract Act, 1872 – Section 73: Compensation for Loss or Damage Caused by Breach",
        "source_text": (
            "When a contract has been broken, the party who suffers by such breach is entitled to receive, "
            "from the party who has broken the contract, compensation for any loss or damage caused to him "
            "thereby, which naturally arose in the usual course of things from such breach, or which the "
            "parties knew, when they made the contract, to be likely to result from the breach of it.\n\n"
            "Such compensation is not to be given for any remote and indirect loss or damage sustained by "
            "reason of the breach.\n\n"
            "Explanation: In estimating the loss or damage from a breach of contract, the means which existed "
            "of remedying the inconvenience caused by the non-performance of the contract shall be taken into "
            "account."
        ),
        "source_category": "Contract Act 1872 – Contract Disputes",
    },
    {
        "source_title": "Contract Act, 1872 – Section 74: Compensation for Breach Where Penalty Stipulated",
        "source_text": (
            "When a contract has been broken, if a sum is named in the contract as the amount to be paid in "
            "case of such breach, or if the contract contains any other stipulation by way of penalty, the "
            "party complaining of the breach is entitled, whether or not actual damage or loss is proved to "
            "have been caused thereby, to receive from the party who has broken the contract reasonable "
            "compensation not exceeding the amount so named or, as the case may be, the penalty stipulated "
            "for.\n\n"
            "Explanation: A stipulation for increased interest from the date of default may be a stipulation "
            "by way of penalty.\n\n"
            "Exception: When any person enters into any bail-bond, recognizance or other instrument of the "
            "same nature, or, under the provisions of any law, or under the orders of the Central Government "
            "or of any Provincial Government, gives any bond for the performance of any public duty or act "
            "in which the public are interested, he shall be liable, upon breach of the condition of any such "
            "instrument, to pay the whole sum mentioned therein."
        ),
        "source_category": "Contract Act 1872 – Contract Disputes",
    },
    {
        "source_title": "Contract Act, 1872 – Section 65: Obligation of Person Who Has Received Advantage Under Void Agreement",
        "source_text": (
            "When an agreement is discovered to be void, or when a contract becomes void, any person who has "
            "received any advantage under such agreement or contract is bound to restore it, or to make "
            "compensation for it, to the person from whom he received it."
        ),
        "source_category": "Contract Act 1872 – Contract Disputes",
    },
    {
        "source_title": "Specific Relief Act, 1877 – Section 12: Cases in Which Specific Performance Enforceable",
        "source_text": (
            "Except as otherwise provided in this Chapter, the specific performance of any contract may, in "
            "the discretion of the Court, be enforced when:\n"
            "(a) the act agreed to be done is in the performance, wholly or partly, of a trust;\n"
            "(b) there exists no standard for ascertaining the actual damage caused by the non-performance of "
            "the act agreed to be done;\n"
            "(c) the act agreed to be done is such that pecuniary compensation for its non-performance would "
            "not afford adequate relief;\n"
            "(d) it is probable that pecuniary compensation cannot be got for the non-performance of the act "
            "agreed to be done.\n\n"
            "Explanation: Unless and until the contrary is proved, the Court shall presume that the breach of "
            "a contract to transfer immoveable property cannot be adequately relieved by compensation in money, "
            "and that the breach of a contract to transfer moveable property can be thus relieved."
        ),
        "source_category": "Specific Relief Act 1877 – Contract Disputes",
    },
    {
        "source_title": "Specific Relief Act, 1877 – Section 21: Contracts Not Specifically Enforceable",
        "source_text": (
            "The following contracts cannot be specifically enforced:\n"
            "(a) a contract for the non-performance of which compensation in money is an adequate relief;\n"
            "(b) a contract which runs into such a minute or numerous details, or which is so dependent on the "
            "personal qualifications or volition of the parties, or otherwise from its nature is such, that the "
            "Court cannot enforce specific performance of its material terms;\n"
            "(c) a contract the terms of which the Court cannot find with reasonable certainty;\n"
            "(d) a contract which is in its nature revocable;\n"
            "(e) a contract made by a trustee in excess of his powers or in breach of trust;\n"
            "(f) a contract which is of such a nature that, if enforced, it would require constant supervision "
            "by the Court;\n"
            "(g) a contract to refer a controversy to arbitration;\n"
            "(h) a contract to sell property where the seller does not have title, unless the contract provides "
            "for acquisition of title."
        ),
        "source_category": "Specific Relief Act 1877 – Contract Disputes",
    },
    {
        "source_title": "Arbitration Act, 1940 – Section 20: Application to File Arbitration Agreement in Court",
        "source_text": (
            "(1) Where any persons have entered into an arbitration agreement before the institution of any "
            "suit with respect to the subject-matter of the agreement or any part of it, and where a difference "
            "has arisen to which the agreement applies, they may at any time before the suit is filed apply to "
            "a Court having jurisdiction over the subject-matter for an order that the agreement be filed in "
            "Court.\n"
            "(2) The application shall be in writing and shall be numbered and registered as a suit between one "
            "or more of the parties interested or claiming to be interested as plaintiff or plaintiffs and the "
            "remainder as defendant or defendants.\n"
            "(3) On such application, the Court shall direct notice thereof to be given to all parties to the "
            "agreement other than the applicants, requiring them to show cause within the time specified why "
            "the agreement should not be filed.\n"
            "(4) Where no sufficient cause is shown, the Court shall order the agreement to be filed, and shall "
            "make an order of reference to the arbitrator appointed by the parties or, where the parties cannot "
            "agree, to an arbitrator appointed by the Court."
        ),
        "source_category": "Arbitration Act 1940 – Contract Disputes",
    },
    {
        "source_title": "Banking Companies (Recovery of Loans) Ordinance, 1979 – Section 5: Jurisdiction of Banking Courts",
        "source_text": (
            "Notwithstanding anything contained in any law for the time being in force, the Banking Court shall "
            "have exclusive jurisdiction to try all suits and proceedings relating to recovery of loans advanced "
            "by a banking company or financial institution, and no other court shall entertain or try any such "
            "suit or proceeding."
        ),
        "source_category": "Banking Laws – Contract Disputes",
    },
    {
        "source_title": "Financial Institutions (Recovery of Finances) Ordinance, 2001 – Section 9: Summary Trial",
        "source_text": (
            "A Banking Court shall, for the purposes of trial of a suit filed under this Ordinance, follow the "
            "summary procedure provided in Order XXXVII of the Code of Civil Procedure, 1908, and shall not "
            "allow a defendant to defend the suit unless a written application for leave to appear and defend "
            "is filed and the Court is satisfied that the defendant has a good or plausible defence. The Court "
            "shall dispose of the suit within ninety days of service of summons."
        ),
        "source_category": "Banking Laws – Contract Disputes",
    },
    {
        "source_title": "Limitation Act, 1908 – Article 113: Suits for Which No Period Provided",
        "source_text": (
            "For suits for which no period of limitation is provided elsewhere in the Schedule, the period of "
            "limitation is three years from the date when the right to sue accrues. This residuary article "
            "applies to many contract-based claims not specifically covered by other articles."
        ),
        "source_category": "Limitation Act 1908 – Contract Disputes",
    },
    {
        "source_title": "Limitation Act, 1908 – Article 115: Compensation for Breach of Contract in Writing Registered",
        "source_text": (
            "For compensation for the breach of any contract, promise or undertaking in writing and registered, "
            "the period of limitation is three years from the date when the contract or undertaking is broken."
        ),
        "source_category": "Limitation Act 1908 – Contract Disputes",
    },
    {
        "source_title": "Qanun-e-Shahadat (Evidence) Order, 1984 – Article 17: Proof of Contract Terms",
        "source_text": (
            "When the terms of a contract, or of a grant, or of any other disposition of property, have been "
            "reduced to the form of a document, and in all cases in which any matter is required by law to be "
            "reduced to the form of a document, no evidence shall be given in proof of the terms of such "
            "contract, grant or other disposition of property, or of such matter, except the document itself, "
            "or secondary evidence of its contents in cases in which secondary evidence is admissible under "
            "this Order."
        ),
        "source_category": "Evidence Law – Contract Disputes",
    },
]

# ── 3. PROPERTY DISPUTES ─────────────────────────────────────────────────────

PROPERTY_KB = [
    {
        "source_title": "CPC 1908 – Section 9: Courts to Try Civil Suits (Property Suits)",
        "source_text": (
            "The Courts shall have jurisdiction to try all suits of a civil nature excepting suits of "
            "which their cognizance is either expressly or impliedly barred. A suit in which the right "
            "to property or to an office is contested is a suit of a civil nature, notwithstanding that "
            "such right may depend entirely on the decision of questions as to religious rites or "
            "ceremonies. All disputes over ownership, possession, or title to property are therefore "
            "triable by civil courts."
        ),
        "source_category": "CPC 1908 – Property Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 16: Suits to Be Instituted Where Property Is Situate",
        "source_text": (
            "Subject to the pecuniary or other limitations prescribed by any law, suits for: (a) the "
            "recovery of immoveable property with or without rent or profits; (b) the partition of "
            "immoveable property; (c) foreclosure, sale or redemption in the case of a mortgage of or "
            "charge upon immoveable property; (d) the determination of any other right to or interest "
            "in immoveable property; (e) compensation for wrong to immoveable property; (f) the recovery "
            "of moveable property actually under distraint or attachment – shall be instituted in the "
            "Court within whose local limits the property is situate or is held."
        ),
        "source_category": "CPC 1908 – Property Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 17: Property Situate in Jurisdiction of Different Courts",
        "source_text": (
            "Where a suit is to obtain relief respecting, or compensation for wrong to, immoveable "
            "property situate within the jurisdiction of different Courts, the suit may be instituted "
            "in any Court within the local limits of whose jurisdiction any portion of the property is "
            "situate, provided that in respect of the value of the subject-matter of the suit, the "
            "entire claim is cognizable by such Court. This allows a single suit when disputed property "
            "spans multiple court jurisdictions."
        ),
        "source_category": "CPC 1908 – Property Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 11: Res Judicata in Property Suits",
        "source_text": (
            "No Court shall try a suit or issue in which the matter directly and substantially in issue "
            "has been directly and substantially in issue in a former suit between the same parties "
            "litigating under the same title, in a Court competent to try such subsequent suit, and has "
            "been heard and finally decided. In property disputes, once title or possession has been "
            "finally determined, the same parties cannot relitigate the same claim. The doctrine "
            "operates as a complete bar against a second suit on the same subject-matter."
        ),
        "source_category": "CPC 1908 – Property Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 21: Objections to Jurisdiction in Property Suits",
        "source_text": (
            "No objection as to the place of suing shall be allowed by any appellate or revisional "
            "Court unless such objection was taken in the Court of first instance at the earliest "
            "possible opportunity, and there has been a consequent failure of justice. Parties in "
            "property disputes must raise jurisdictional objections at the first available opportunity "
            "or they are deemed waived."
        ),
        "source_category": "CPC 1908 – Property Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 51: Powers of Court to Enforce Decree for Property",
        "source_text": (
            "The Court may, on the application of the decree-holder, order execution of the decree: "
            "(a) by delivery of any property specifically decreed; (b) by attachment and sale or by "
            "sale without attachment of any property; (c) by arrest and detention in prison; (d) by "
            "appointing a receiver; or (e) in such other manner as the nature of the relief granted "
            "may require. Decrees for possession of specific immoveable property are executed primarily "
            "by mode (a) – physical delivery of possession."
        ),
        "source_category": "CPC 1908 – Property Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 54: Attachment of Immoveable Property in Execution",
        "source_text": (
            "Where the property to be attached is immoveable, the attachment shall be made by an order "
            "prohibiting the judgment-debtor from transferring or charging the property in any way, and "
            "prohibiting all persons from taking any benefit from such transfer or charge. The order of "
            "attachment is communicated by affixing a copy at the property and at the Court. No private "
            "sale or transfer of attached property is valid against the decree-holder."
        ),
        "source_category": "CPC 1908 – Property Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 64: Private Alienation After Attachment Is Void",
        "source_text": (
            "Where an attachment has been made, any private transfer or delivery of the property "
            "attached or of any interest therein and any payment to the judgment-debtor of any debt, "
            "dividend or other monies contrary to such attachment, shall be void as against all claims "
            "enforceable under the attachment. This is a key protection: once a property is attached "
            "by order of court, the owner cannot privately sell or mortgage it to defeat the decree."
        ),
        "source_category": "CPC 1908 – Property Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 65: Purchaser's Title in Court Auction of Immoveable Property",
        "source_text": (
            "Where immoveable property is sold in execution of a decree and such sale has become "
            "absolute, the property shall be deemed to have vested in the purchaser from the time "
            "when the property is sold and not from the time when the sale becomes absolute. A court "
            "auction purchaser therefore acquires a clean title free from encumbrances created by the "
            "judgment-debtor after the attachment, and that title relates back to the date of the "
            "auction sale."
        ),
        "source_category": "CPC 1908 – Property Disputes",
    },
    {
        "source_title": "CPC 1908 – Order XXI: Execution of Decrees and Orders (Property)",
        "source_text": (
            "Order XXI governs the procedure for execution of all decrees including decrees for "
            "immoveable property. Key rules include: Rule 35 – Decree for immoveable property shall "
            "be executed by delivering possession to the decree-holder, removing any person bound by "
            "the decree who refuses to vacate. Rule 36 – Where property is in occupancy of a tenant "
            "not bound by the decree, possession may be delivered subject to the tenancy. Rule 54 – "
            "Attachment of immoveable property is effected by proclamation and prohibitory order. "
            "Rule 90 – Any irregularity or fraud in the conduct of an auction sale may be a ground "
            "to set it aside."
        ),
        "source_category": "CPC 1908 – Property Disputes",
    },
    {
        "source_title": "CPC 1908 – Order XXXIV: Suits Relating to Mortgages of Immoveable Property",
        "source_text": (
            "Rule 1: All persons having an interest in the mortgage shall be joined as parties to a "
            "suit for foreclosure, sale, or redemption. Rule 2: In a foreclosure suit, a preliminary "
            "decree is passed fixing the amount due and giving the mortgagor time to pay; if not paid, "
            "a final decree for foreclosure is passed. Rule 4: In a suit for sale, the Court passes a "
            "preliminary decree for sale of the mortgaged property. Rule 7: In a redemption suit, the "
            "mortgagor gets a preliminary decree to pay the amount due and redeem the property. "
            "Order XXXIV governs all mortgage enforcement and redemption proceedings over immoveable "
            "property in Pakistan."
        ),
        "source_category": "CPC 1908 – Property Disputes",
    },
    {
        "source_title": "CPC 1908 – Section 94: Temporary Injunction in Property Disputes",
        "source_text": (
            "In order to prevent the ends of justice from being defeated, the Court may grant a "
            "temporary injunction and, in cases of disobedience, commit the person to prison and order "
            "his properties to be attached and sold. In property disputes, a temporary injunction may "
            "be sought to restrain the defendant from: (a) constructing on disputed land; (b) selling, "
            "transferring or encumbering the disputed property; (c) interfering with the plaintiff's "
            "possession. The Court must be satisfied of a prima facie case, balance of convenience "
            "favouring the plaintiff, and irreparable injury if the injunction is not granted."
        ),
        "source_category": "CPC 1908 – Property Disputes",
    },
    {
        "source_title": "CPC 1908 – Order XXXVIII: Attachment Before Judgment to Protect Property Rights",
        "source_text": (
            "Where at any stage of a suit the Court is satisfied, by affidavit or otherwise, that the "
            "defendant is about to remove property from the jurisdiction, or has disposed of or is about "
            "to dispose of property with intent to obstruct or delay execution of a decree, the Court "
            "may order attachment before judgment. This prevents a fraudulent defendant in a property "
            "suit from disposing of the disputed asset before the Court can pass a final decree."
        ),
        "source_category": "CPC 1908 – Property Disputes",
    },
    {
        "source_title": "CPC 1908 – Partition of Undivided Estate (Order XXI, Execution by Collector)",
        "source_text": (
            "Where the decree is for the partition of an undivided estate assessed to the payment of "
            "revenue to the Government, or for the separate possession of a share of such estate, "
            "the partition or separation shall be made by the Collector or any gazetted subordinate "
            "of the Collector deputed by him in accordance with the law for the time being in force "
            "relating to the partition. For agricultural land and revenue-assessed estates, partition "
            "decrees are implemented administratively through the Revenue Collector."
        ),
        "source_category": "CPC 1908 – Property Disputes",
    },
    {
        "source_title": "CPC 1908 – Order I Rule 8: Representative Suits in Property Matters",
        "source_text": (
            "(1) Where there are numerous persons having the same interest in one suit, the suit may be "
            "instituted, prosecuted or defended by, or against, one or more of such persons with the "
            "permission of the Court, on behalf of, or for the benefit of, all persons so interested.\n"
            "(2) Notice of the institution of the suit shall be given to all persons so interested by "
            "public advertisement or by personal service as the Court may direct.\n"
            "(3) Any person on whose behalf the suit is instituted or defended may apply to the Court to "
            "be made a party to the suit.\n"
            "This provision is essential in property disputes involving community rights, such as common "
            "land, graveyards, shamlat deh, or other collective property interests ."
        ),
        "source_category": "CPC 1908 – Property Disputes",
    },
    {
        "source_title": "CPC 1908 – Order VII Rule 11: Rejection of Plaint",
        "source_text": (
            "The plaint shall be rejected in the following cases:\n"
            "(a) where it does not disclose a cause of action;\n"
            "(b) where the relief claimed is undervalued, and the plaintiff fails to correct the valuation "
            "within time fixed by the Court;\n"
            "(c) where the relief claimed is properly valued but the plaint is insufficiently stamped;\n"
            "(d) where the suit appears from the statement in the plaint to be barred by any law;\n"
            "(e) where it is not filed in duplicate;\n"
            "(f) where the plaintiff fails to comply with Order VII Rule 9.\n"
            "It is the duty of the Court to reject the plaint if on perusal it appears that the suit is "
            "incompetent, even without any application from a party ."
        ),
        "source_category": "CPC 1908 – Property Disputes",
    },
    {
        "source_title": "Transfer of Property Act, 1882 – Section 54: Sale of Immoveable Property",
        "source_text": (
            "'Sale' is a transfer of ownership in exchange for a price paid or promised or part-paid and "
            "part-promised. Such transfer, in the case of tangible immoveable property of the value of one "
            "hundred rupees and upwards, or in the case of a reversion or other intangible thing, can be "
            "made only by a registered instrument. In the case of tangible immoveable property of a value "
            "less than one hundred rupees, such transfer may be made either by a registered instrument or "
            "by delivery of the property."
        ),
        "source_category": "Transfer of Property Act 1882 – Property Disputes",
    },
    {
        "source_title": "Transfer of Property Act, 1882 – Section 58: Mortgage Defined",
        "source_text": (
            "A mortgage is the transfer of an interest in specific immoveable property for the purpose of "
            "securing the payment of money advanced or to be advanced by way of loan, an existing or future "
            "debt, or the performance of an engagement which may give rise to a pecuniary liability.\n"
            "The transferor is called a mortgagor, the transferee a mortgagee; the principal money and "
            "interest of which payment is secured for the time being are called the mortgage-money, and the "
            "instrument (if any) by which the transfer is effected is called a mortgage-deed."
        ),
        "source_category": "Transfer of Property Act 1882 – Property Disputes",
    },
    {
        "source_title": "Transfer of Property Act, 1882 – Section 60: Right of Redemption",
        "source_text": (
            "At any time after the principal money has become due, the mortgagor has a right, on payment or "
            "tender to the mortgagee of the mortgage-money, to require the mortgagee to reconvey the property "
            "to him or to such third person as he may direct, or to acknowledge in writing that the property "
            "has been redeemed, and to deliver possession or to authorize the mortgagor to receive such "
            "possession.\n"
            "Provided that the right conferred by this section has not been extinguished by the act of the "
            "parties or by the decree of a Court.\n"
            "The right of redemption shall not be deemed to be extinguished by any contract to the contrary "
            "entered into at the time of the mortgage which unreasonably restricts the right of redemption."
        ),
        "source_category": "Transfer of Property Act 1882 – Property Disputes",
    },
    {
        "source_title": "Transfer of Property Act, 1882 – Section 105: Lease Defined",
        "source_text": (
            "A lease of immoveable property is a transfer of a right to enjoy such property, made for a "
            "certain time, express or implied, or in perpetuity, in consideration of a price paid or promised, "
            "or of money, a share of crops, service or any other thing of value, to be rendered periodically "
            "or on specified occasions to the transferor by the transferee, who accepts the transfer on such "
            "terms.\n"
            "The transferor is called the lessor, the transferee is called the lessee, the price is called the "
            "premium, and the money, share, service or other thing to be so rendered is called the rent."
        ),
        "source_category": "Transfer of Property Act 1882 – Property Disputes",
    },
    {
        "source_title": "Registration Act, 1908 – Section 17: Documents of Which Registration is Compulsory",
        "source_text": (
            "(1) The following documents shall be registered, if the property to which they relate is situate "
            "in a district in which, and if they have been executed on or after the date on which, the "
            "Registration Act came into force:\n"
            "(a) instruments of gift of immoveable property;\n"
            "(b) other non-testamentary instruments which purport or operate to create, declare, assign, limit "
            "or extinguish, whether in present or in future, any right, title or interest, whether vested or "
            "contingent, of the value of one hundred rupees and upwards, to or in immoveable property;\n"
            "(c) non-testamentary instruments which acknowledge the receipt or payment of any consideration on "
            "account of the creation, declaration, assignment, limitation or extinction of any such right, "
            "title or interest;\n"
            "(d) leases of immoveable property from year to year, or for any term exceeding one year, or "
            "reserving a yearly rent;\n"
            "(e) non-testamentary instruments transferring or assigning any decree or order of a Court or any "
            "award when such decree or order or award purports or operates to create, declare, assign, limit "
            "or extinguish any right, title or interest of the value of one hundred rupees and upwards to or "
            "in immoveable property."
        ),
        "source_category": "Registration Act 1908 – Property Disputes",
    },
    {
        "source_title": "Constitution of Pakistan, 1973 – Article 23: Right to Hold Property",
        "source_text": (
            "Every citizen shall have the right to acquire, hold and dispose of property in any part of "
            "Pakistan, subject to the Constitution and any reasonable restrictions imposed by law in the "
            "public interest ."
        ),
        "source_category": "Constitutional Law – Property Disputes",
    },
    {
        "source_title": "Constitution of Pakistan, 1973 – Article 24: Protection of Property Rights",
        "source_text": (
            "(1) No person shall be deprived of his property save in accordance with law.\n"
            "(2) No property shall be compulsorily acquired or taken possession of save for a public purpose, "
            "and save by the authority of law which provides for compensation therefor and either fixes the "
            "amount of compensation or specifies the principles on and the manner in which compensation is to "
            "be determined and given.\n"
            "(3) Nothing in this Article shall affect the validity of—\n"
            "(a) any law permitting the compulsory acquisition or taking possession of any property for "
            "preventing danger to life, property or public health; or\n"
            "(b) any law permitting the taking over of any property which has been acquired by, or come into "
            "the possession of, any person by any unfair means, or in any manner, contrary to law; or\n"
            "(c) any law relating to the acquisition, administration or disposal of any property which is or "
            "is deemed to be enemy property or evacuee property under any law; or\n"
            "(d) any law providing for the taking over of the management of any property by the State for a "
            "limited period; or\n"
            "(e) any law providing for the acquisition of any class of property for specified public purposes "
            "including education, medical aid, housing and public facilities.\n"
            "(4) The adequacy or otherwise of any compensation provided for by any such law shall not be called "
            "in question in any court ."
        ),
        "source_category": "Constitutional Law – Property Disputes",
    },
    {
        "source_title": "Land Acquisition Act, 1894 – Section 4: Publication of Preliminary Notification",
        "source_text": (
            "Whenever it appears to the appropriate Government that land in any locality is needed or is likely "
            "to be needed for any public purpose, a notification to that effect shall be published in the "
            "official Gazette and in two daily newspapers circulating in that locality, and the Collector shall "
            "cause public notice of the substance of such notification to be given at convenient places on or "
            "near the land to be acquired."
        ),
        "source_category": "Land Acquisition – Property Disputes",
    },
    {
        "source_title": "Land Acquisition Act, 1894 – Section 23: Matters to be Considered in Determining Compensation",
        "source_text": (
            "(1) In determining the amount of compensation to be awarded for land acquired under this Act, the "
            "Court shall take into consideration:\n"
            "first, the market value of the land at the date of the publication of the notification under "
            "section 4;\n"
            "secondly, the damage sustained by the person interested by reason of the taking of any standing "
            "crops or trees which may be on the land at the time of the Collector's taking possession thereof;\n"
            "thirdly, the damage sustained by the person interested by reason of severing such land from his "
            "other land;\n"
            "fourthly, the damage sustained by the person interested by reason of the acquisition injuriously "
            "affecting his other property, movable or immovable, in any other manner;\n"
            "fifthly, if, in consequence of the acquisition, he is compelled to change his residence or place "
            "of business, the reasonable expenses, if any, incidental to such change;\n"
            "sixthly, the damage sustained by the person interested by reason of the diminution of the profits "
            "of the land between the time of the publication of the declaration under section 6 and the time "
            "of the Collector's taking possession of the land.\n"
            "(2) In addition to the market value of the land, the Court shall in every case award a sum of "
            "fifteen per centum on such market value, in consideration of the compulsory nature of the "
            "acquisition."
        ),
        "source_category": "Land Acquisition – Property Disputes",
    },
    {
        "source_title": "Punjab Land Revenue Act, 1967 – Section 117: Division of Joint Land",
        "source_text": (
            "When two or more persons are jointly interested in land as landowners or tenants, any of them may "
            "apply to the Revenue Officer for partition of the joint land. The Revenue Officer shall, after "
            "inquiry and notice to all interested parties, divide the land by metes and bounds according to "
            "the shares of the parties."
        ),
        "source_category": "Revenue Law – Property Disputes",
    },
]
# ── Master KB lookup ─────────────────────────────────────────────────────────

CATEGORY_KB = {
    "Family Disputes":   FAMILY_KB,
    "Contract Disputes": CONTRACT_KB,
    "Property Disputes": PROPERTY_KB,
}

VALID_CATEGORIES = set(CATEGORY_KB.keys())


# ════════════════════════════════════════════════════════════════════════════
# CORE ENGINE
# ════════════════════════════════════════════════════════════════════════════

class LegalAIEngine:
    """
    Lightweight engine: static KB + Gemini API.
    No heavy models, no disk caches, near-instant startup.
    """

    def __init__(self):
        print("--- Initializing Legal AI Engine (CPC Knowledge Base + Gemini) ---")
        if not api_key:
            print("⚠️  Gemini API key missing – analysis will fail.")
        else:
            print("✅  Gemini API configured.")
        print(f"✅  Knowledge Base loaded: "
              f"{len(FAMILY_KB)} Family | "
              f"{len(CONTRACT_KB)} Contract | "
              f"{len(PROPERTY_KB)} Property provisions.")

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze_case(self, description: str, category: str) -> dict:
        """
        Main entry point called by FastAPI.
        Returns the standard analysis dict expected by the frontend.
        """
        # 1. Validate category
        if category not in VALID_CATEGORIES:
            return self._rejection_response(
                f"Unknown category '{category}'. "
                f"Please choose from: {', '.join(VALID_CATEGORIES)}."
            )

        # 2. Basic guard against empty / nonsensical input
        if not description or len(description.strip()) < 20:
            return self._rejection_response(
                "Please provide a more detailed description of your case (at least a few sentences)."
            )

        # 3. Check in-memory cache
        key = _cache_key(category, description)
        if key in _RESPONSE_CACHE:
            print(f"⚡ Cache hit for [{category}]")
            return _RESPONSE_CACHE[key]

        # 4. Retrieve relevant laws + generate analysis (single Gemini call)
        kb = CATEGORY_KB[category]
        result = self._generate_analysis(category, description, kb)

        if result is None:
            return self._error_response("All Gemini models failed. Please try again later.")

        # 5. Store in cache
        _RESPONSE_CACHE[key] = result
        return result

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _build_prompt(self, category: str, description: str, kb: list) -> str:
        """
        Builds a single prompt that asks Gemini to:
          (a) select the 3 most relevant CPC provisions from the KB, and
          (b) generate the full legal analysis JSON.
        """
        kb_text = ""
        for i, entry in enumerate(kb):
            kb_text += (
                f"[{i}] SOURCE: {entry['source_title']}\n"
                f"    TEXT: {entry['source_text']}\n\n"
            )

        return f"""You are a Senior Pakistani Legal Advocate specialising in civil litigation.

DISPUTE CATEGORY: {category}

CASE DESCRIPTION:
\"\"\"{description}\"\"\"

CPC 1908 KNOWLEDGE BASE ({len(kb)} provisions):
{kb_text}

TASK:
1. From the knowledge base above, identify the 3 most contextually relevant provisions for this specific case.
2. Provide a professional legal analysis of the case strictly based on those provisions and Pakistani law.
3. Return ONLY a single valid JSON object – no preamble, no markdown fences.

STRICT JSON FORMAT:
{{
    "selected_law_indices": [<index_a>, <index_b>, <index_c>],
    "case_summary": "One paragraph professional summary of the case and its legal standing.",
    "key_facts": ["Key legal fact 1", "Key legal fact 2", "Key legal fact 3"],
    "validity_status": "Strong|Moderate|Weak",
    "validity_assessment": {{
        "risk_level": "Low|Moderate|High",
        "advice_summary": "Full legal analysis in paragraphs only (no bullet lists). Apply the selected CPC provisions directly to the facts. Minimum 3 paragraphs.",
        "simplified_advice": "Explain the situation in plain simple language a non-lawyer can understand in 2–3 sentences."
    }}
}}

INSTRUCTIONS:
- `validity_status` reflects how well-grounded the claim is in Pakistani law.
- `risk_level` reflects litigation risk for the claimant (Low = favourable, High = difficult).
- `advice_summary` must reference specific CPC sections/Orders selected.
- Do NOT include any text outside the JSON object.
"""

    def _generate_analysis(self, category: str, description: str, kb: list) -> dict | None:
        """
        Calls Gemini models in order. On success, returns the parsed result dict
        ready to be sent to the frontend (including relevant_laws).
        Returns None if all models fail.
        """
        prompt = self._build_prompt(category, description, kb)

        for model_name in MODEL_HIERARCHY:
            try:
                print(f"🔍 Calling {model_name} for [{category}]...")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                raw = response.text.strip()

                # Strip any accidental markdown fences
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                raw = raw.strip()

                parsed = json.loads(raw)
                result = self._build_response(parsed, kb, category)
                print(f"✅ Analysis generated successfully using {model_name}.")
                return result

            except json.JSONDecodeError as e:
                print(f"⚠️  JSON parse error from {model_name}: {e}")
                continue
            except Exception as e:
                print(f"⚠️  Error with {model_name}: {e} – trying next model...")
                continue

        print("❌ All models in hierarchy failed.")
        return None

    def _build_response(self, parsed: dict, kb: list, category: str) -> dict:
        """
        Combines the LLM's JSON with the actual KB entries it selected.
        Produces the final dict that FastAPI returns to the frontend.
        """
        indices = parsed.get("selected_law_indices", [])

        # Clamp indices to valid range
        valid_indices = [i for i in indices if isinstance(i, int) and 0 <= i < len(kb)]

        # Fallback: first 3 entries if model returned bad indices
        if not valid_indices:
            valid_indices = list(range(min(3, len(kb))))

        relevant_laws = []
        for rank, idx in enumerate(valid_indices[:3]):
            entry = kb[idx]
            relevant_laws.append({
                "source_title":    entry["source_title"],
                "source_text":     self._truncate(entry["source_text"]),
                "relevance_score": round(1.0 - rank * 0.05, 2),   # 1.0, 0.95, 0.90
                "source_category": entry["source_category"],
            })

        return {
            "case_summary":    parsed.get("case_summary", "Summary unavailable."),
            "key_facts":       parsed.get("key_facts", []),
            "relevant_laws":   relevant_laws,
            "validity_status": parsed.get("validity_status", "Uncertain"),
            "validity_assessment": parsed.get(
                "validity_assessment",
                {
                    "risk_level":       "Unknown",
                    "advice_summary":   "Analysis unavailable.",
                    "simplified_advice": "Please try again.",
                },
            ),
        }

    @staticmethod
    def _truncate(text: str, max_len: int = 220) -> str:
        """Truncates source_text for frontend display."""
        text = text.replace("\n", " ").strip()
        if len(text) <= max_len:
            return text
        cut = text.rfind(" ", 0, max_len)
        return text[: cut if cut > 0 else max_len] + "…"

    @staticmethod
    def _rejection_response(reason: str) -> dict:
        return {
            "case_summary": "Case Rejected",
            "key_facts": [],
            "relevant_laws": [],
            "validity_status": "REJECTED",
            "validity_assessment": {
                "risk_level": "N/A",
                "advice_summary": reason,
                "simplified_advice": reason,
            },
        }

    @staticmethod
    def _error_response(msg: str) -> dict:
        return {
            "case_summary": f"System Alert: {msg}",
            "key_facts": [],
            "relevant_laws": [],
            "validity_status": "ERROR",
            "validity_assessment": {
                "risk_level": "Unknown",
                "advice_summary": "The AI analysis service is temporarily unavailable.",
                "simplified_advice": "Please try again in a moment.",
            },
        }


# ── Singleton instance (imported by main.py) ─────────────────────────────────
legal_engine = LegalAIEngine()
