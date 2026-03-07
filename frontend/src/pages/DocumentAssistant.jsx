import React, { useState } from 'react';
import Emblem from '../ui/Emblem';
import { jsPDF } from "jspdf";

// Reusable Card for each download item
function DownloadCard({ title, description, link, category, isDirect }) {
  return (
    <div className="card download-card fade-in-up">
      <div className="icon-wrapper">
        <svg xmlns="http://www.w3.org/2000/svg" className="doc-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m.75 12 3 3m0 0 3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
        </svg>
      </div>
      <div className="content">
        <span className={`badge ${category.toLowerCase()}`}>{category}</span>
        <h4>{title}</h4>
        <p>{description}</p>
        <a href={link} target="_blank" rel="noopener noreferrer" className="btn btn-outline btn-sm">
          {isDirect ? "Download PDF" : "Go to Official Downloads"}
          <svg xmlns="http://www.w3.org/2000/svg" className="btn-icon" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </a>
      </div>
    </div>
  );
}

function DocumentAssistant() {
  const [showGenerator, setShowGenerator] = useState(false);
  const [plaintData, setPlaintData] = useState({
    courtName: "Senior Civil Judge, Islamabad",
    plaintiffName: "",
    plaintiffParentage: "",
    plaintiffAddress: "",
    defendantName: "",
    defendantParentage: "",
    defendantAddress: "",
    suitTitle: "SUIT FOR RECOVERY OF MONEY AND DAMAGES",
    facts: "",
    prayer: "",
    place: "Islamabad",
    date: new Date().toISOString().split('T')[0]
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setPlaintData(prev => ({ ...prev, [name]: value }));
  };

  const generatePlaintPDF = () => {
    const doc = new jsPDF();

    // -- Formatting Constants --
    const margin = 20;
    const pageWidth = doc.internal.pageSize.getWidth();
    const contentWidth = pageWidth - (margin * 2);
    let yPos = 25;

    // --- 1. Header ---
    doc.setFont("times", "bold");
    doc.setFontSize(14);
    doc.text(`IN THE COURT OF ${plaintData.courtName.toUpperCase()}`, pageWidth / 2, yPos, { align: "center" });
    yPos += 10;

    doc.setFontSize(12);
    doc.setFont("times", "normal");
    doc.text("Civil Suit No. _________ / 2025", margin, yPos);
    yPos += 15;

    // --- 2. Parties ---
    // Plaintiff
    const pName = plaintData.plaintiffName || "__________________";
    const pParent = plaintData.plaintiffParentage || "__________________";
    const pAddress = plaintData.plaintiffAddress || "__________________";

    doc.text(`${pName} S/o, D/o ${pParent},`, margin, yPos);
    yPos += 6;
    doc.text(`Resident of ${pAddress}.`, margin, yPos);
    yPos += 8;

    doc.setFont("times", "bold");
    doc.text("... PLAINTIFF", pageWidth - margin, yPos, { align: "right" });
    yPos += 10;

    doc.setFont("times", "bolditalic");
    doc.text("VERSUS", pageWidth / 2, yPos, { align: "center" });
    yPos += 10;

    // Defendant
    doc.setFont("times", "normal");
    const dName = plaintData.defendantName || "__________________";
    const dParent = plaintData.defendantParentage || "__________________";
    const dAddress = plaintData.defendantAddress || "__________________";

    doc.text(`${dName} S/o, D/o ${dParent},`, margin, yPos);
    yPos += 6;
    doc.text(`Resident of ${dAddress}.`, margin, yPos);
    yPos += 8;

    doc.setFont("times", "bold");
    doc.text("... DEFENDANT", pageWidth - margin, yPos, { align: "right" });
    yPos += 18;

    // --- 3. Title ---
    doc.setFont("times", "bold");
    doc.setFontSize(13);
    const titleText = plaintData.suitTitle.toUpperCase();
    const splitTitle = doc.splitTextToSize(titleText, contentWidth);
    doc.text(splitTitle, pageWidth / 2, yPos, { align: "center" });

    // Underline title
    const titleLines = splitTitle.length;
    yPos += (titleLines * 2);
    doc.line(margin + 10, yPos, pageWidth - margin - 10, yPos);
    yPos += 15;

    // --- 4. Body ---
    doc.setFont("times", "normal");
    doc.setFontSize(12);
    doc.text("Respectfully Sheweth:", margin, yPos);
    yPos += 10;

    // User Facts
    const userFacts = plaintData.facts
        ? plaintData.facts
        : "1. That the plaintiff is a law-abiding citizen of Pakistan.\n2. That the defendant entered into a transaction with the plaintiff on [Date]...\n3. That the defendant failed to fulfill their obligations...";

    const factsLines = doc.splitTextToSize(userFacts, contentWidth);
    doc.text(factsLines, margin, yPos);
    yPos += (factsLines.length * 7) + 8;

    // Standard Legal Clauses (Mandatory in Pakistan)
    const legalClauses = "4. That the cause of action accrued in favor of the plaintiff and against the defendant firstly when the transaction took place and finally when the defendant refused to comply with the legal demands.\n\n5. That the parties reside/property is situated within the territorial limits of this Honorable Court, hence this Court has the jurisdiction to adjudicate upon this matter.\n\n6. That the value of the suit for the purposes of court fee and jurisdiction is fixed at Rs. 200/-, and the requisite court fee has been affixed.";

    // Check page break
    const clauseLines = doc.splitTextToSize(legalClauses, contentWidth);
    if (yPos + (clauseLines.length * 7) > 270) { doc.addPage(); yPos = 20; }

    doc.text(clauseLines, margin, yPos);
    yPos += (clauseLines.length * 7) + 15;

    // --- 5. Prayer ---
    if (yPos > 250) { doc.addPage(); yPos = 20; }

    doc.setFont("times", "bold");
    doc.text("PRAYER:", margin, yPos);
    yPos += 8;

    doc.setFont("times", "normal");
    const prayerText = "It is, therefore, most respectfully prayed that a decree be passed in favor of the Plaintiff and against the Defendant as per the following relief:\n\n" +
                       (plaintData.prayer || "A) A decree for recovery of the amount claimed.\nB) Any other relief this Court deems just and proper.");

    const prayerLines = doc.splitTextToSize(prayerText, contentWidth);
    doc.text(prayerLines, margin, yPos);
    yPos += (prayerLines.length * 7) + 20;

    // --- 6. Signatures ---
    if (yPos > 240) { doc.addPage(); yPos = 20; }

    doc.setFont("times", "bold");
    doc.text("PLAINTIFF", margin, yPos);
    doc.text("Through Counsel:", pageWidth - margin, yPos, { align: "right" });
    yPos += 25;

    doc.line(margin, yPos, margin + 40, yPos); // Line for signature
    doc.line(pageWidth - margin - 50, yPos, pageWidth - margin, yPos); // Line for counsel
    yPos += 15;

    // --- 7. Verification ---
    if (yPos > 250) { doc.addPage(); yPos = 20; }

    doc.setFont("times", "bold");
    doc.text("VERIFICATION:", pageWidth / 2, yPos, { align: "center" });
    yPos += 10;

    doc.setFont("times", "normal");
    const verificationText = `Verified on Oath at ${plaintData.place} on this ${plaintData.date} that the contents of the above plaint are true and correct to the best of my knowledge and belief, and nothing has been concealed herein.`;
    const verifLines = doc.splitTextToSize(verificationText, contentWidth);
    doc.text(verifLines, margin, yPos);
    yPos += (verifLines.length * 7) + 15;

    doc.text("DEPONENT", pageWidth - margin, yPos, { align: "right" });

    doc.save("Professional_Plaint_Draft.pdf");
  };

  const forms = [
    {
      title: "Opening Sheet for Civil Appeals",
      category: "Civil",
      description: "Essential cover sheet for filing civil appeals in the Islamabad High Court (Order XLI Rule I).",
      link: "https://mis.ihc.gov.pk/attachments/downloads/Opening_Sheet_for_Civil_Appeals_________________637402670721907442.pdf",
      isDirect: true
    },
    {
      title: "Urgent Application Proforma",
      category: "Civil",
      description: "Required when filing cases that need immediate or urgent hearing.",
      link: "https://mis.ihc.gov.pk/attachments/downloads/Urgent_Form636907575590538498.pdf",
      isDirect: true
    },
    {
      title: "Copy Petition Form",
      category: "Administrative",
      description: "Application form to request certified copies of court orders and judgments.",
      link: "https://mis.ihc.gov.pk/attachments/downloads/Copy_Petition_Proforma_Sample_______.pdf",
      isDirect: true
    },
    {
      title: "Vakalatnama (Power of Attorney)",
      category: "General",
      description: "Standard authorization form for appointing legal counsel. (See Item #5 on Portal)",
      link: "https://mis.ihc.gov.pk/frmDownloads",
      isDirect: false
    },
    {
      title: "Institution Proforma",
      category: "General",
      description: "Standard form for the institution of new cases. (See Item #9 on Portal)",
      link: "https://mis.ihc.gov.pk/frmDownloads",
      isDirect: false
    },
    {
      title: "Index Sheet Template",
      category: "General",
      description: "Standardized index sheet for organizing case files. (See Official Portal)",
      link: "https://mis.ihc.gov.pk/frmDownloads",
      isDirect: false
    }
  ];

  return (
    <div className="container">
      <div className="hero fade-in-up" style={{ padding: '30px', marginBottom: '30px' }}>
        <div className="hero-left">
          <h2>Legal Document Assistant</h2>
          <p>
            Access official judicial forms or use our AI tool to draft a professional civil plaint compliant with Pakistani Law.
          </p>
        </div>
        <div className="emblem-container" style={{ width: '80px', height: '80px' }}>
             <Emblem size={50} />
        </div>
      </div>

      <h3 style={{color: 'var(--olive)', marginBottom:'20px'}}>Official Court Forms</h3>
      <div className="doc-grid">
        {forms.map((form, index) => (
          <DownloadCard
            key={index}
            title={form.title}
            description={form.description}
            category={form.category}
            link={form.link}
            isDirect={form.isDirect}
          />
        ))}
      </div>

      <div className="info-box fade-in-up delay-1" style={{ marginTop: '40px', marginBottom: '40px' }}>
        <h4>📝 Filing Tip</h4>
        <p>
          Always ensure you print these forms on <strong>Legal Size (8.5 x 14 inches)</strong> paper.
          Attach a copy of your CNIC and relevant court fees.
        </p>
      </div>

      {/* --- MOCK PLAINT GENERATOR --- */}
      <div className="plaint-generator-section fade-in-up delay-2" style={{ borderTop: '2px solid #eee', paddingTop: '30px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h3 style={{ color: 'var(--olive)', margin: 0 }}>Draft a Civil Plaint (Mock)</h3>
            <p style={{ color: '#666', margin: '5px 0 0 0' }}>Generate a standardized civil suit format with automatic legal clauses.</p>
          </div>
          <button
            className="btn btn-primary"
            onClick={() => setShowGenerator(!showGenerator)}
          >
            {showGenerator ? "Hide Generator" : "Start Drafting"}
          </button>
        </div>

        {showGenerator && (
          <div className="card form" style={{ maxWidth: '100%', background: '#f9f9f9', border: '1px solid #ddd' }}>

            {/* Court & Suit Title */}
            <div className="grid-2">
              <div className="field">
                <label>Name of Court</label>
                <input type="text" name="courtName" value={plaintData.courtName} onChange={handleInputChange} />
              </div>
              <div className="field">
                <label>Suit Title</label>
                <input type="text" name="suitTitle" value={plaintData.suitTitle} onChange={handleInputChange} />
              </div>
            </div>

            {/* Plaintiff Info */}
            <h4 style={{marginTop: '10px', color: '#333'}}>Plaintiff Details (You)</h4>
            <div className="grid-2">
              <div className="field">
                <label>Full Name</label>
                <input type="text" name="plaintiffName" placeholder="e.g. Muhammad Ali" value={plaintData.plaintiffName} onChange={handleInputChange} />
              </div>
              <div className="field">
                <label>S/o, D/o, W/o</label>
                <input type="text" name="plaintiffParentage" placeholder="e.g. Ahmed Khan" value={plaintData.plaintiffParentage} onChange={handleInputChange} />
              </div>
            </div>
            <div className="field">
                <label>Full Address</label>
                <input type="text" name="plaintiffAddress" placeholder="House #, Street, Sector/City" value={plaintData.plaintiffAddress} onChange={handleInputChange} />
            </div>

            {/* Defendant Info */}
            <h4 style={{marginTop: '10px', color: '#333'}}>Defendant Details (Opposing Party)</h4>
            <div className="grid-2">
              <div className="field">
                <label>Full Name</label>
                <input type="text" name="defendantName" placeholder="e.g. State Life Insurance" value={plaintData.defendantName} onChange={handleInputChange} />
              </div>
              <div className="field">
                <label>S/o, D/o, W/o</label>
                <input type="text" name="defendantParentage" placeholder="e.g. Unknown (or Father's Name)" value={plaintData.defendantParentage} onChange={handleInputChange} />
              </div>
            </div>
            <div className="field">
                <label>Full Address</label>
                <input type="text" name="defendantAddress" placeholder="House #, Street, Sector/City" value={plaintData.defendantAddress} onChange={handleInputChange} />
            </div>

            {/* Body */}
            <div className="field">
              <label>Facts of the Case (Briefly)</label>
              <textarea
                rows="6"
                name="facts"
                placeholder="1. That the plaintiff is a law abiding citizen...&#10;2. That on [Date], the defendant..."
                value={plaintData.facts}
                onChange={handleInputChange}
              ></textarea>
              <small style={{color: '#666'}}>Note: Standard Jurisdiction and Court Fee clauses will be added automatically.</small>
            </div>

            <div className="field">
              <label>Prayer (Relief Claimed)</label>
              <textarea
                rows="4"
                name="prayer"
                placeholder="It is therefore most respectfully prayed that..."
                value={plaintData.prayer}
                onChange={handleInputChange}
              ></textarea>
            </div>

            {/* Footer */}
            <div className="grid-2">
              <div className="field">
                <label>Place of Verification</label>
                <input type="text" name="place" value={plaintData.place} onChange={handleInputChange} />
              </div>
              <div className="field">
                <label>Date</label>
                <input type="date" name="date" value={plaintData.date} onChange={handleInputChange} />
              </div>
            </div>

            <div className="action" style={{ justifyContent: 'flex-end' }}>
              <button className="btn btn-primary" onClick={generatePlaintPDF}>
                📄 Generate Professional Plaint
              </button>
            </div>
          </div>
        )}
      </div>

      <style>{`
        .doc-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 20px;
        }
        .download-card {
          display: flex;
          gap: 15px;
          align-items: flex-start;
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .download-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.08);
        }
        .icon-wrapper {
          background: #f0f8e6;
          padding: 12px;
          border-radius: 8px;
          color: var(--olive);
        }
        .doc-icon {
          width: 24px;
          height: 24px;
        }
        .content {
          flex: 1;
        }
        .badge {
          font-size: 11px;
          padding: 2px 8px;
          border-radius: 4px;
          text-transform: uppercase;
          font-weight: 700;
          letter-spacing: 0.5px;
          margin-bottom: 8px;
          display: inline-block;
        }
        .badge.civil { background: #e3f2fd; color: #1565c0; }
        .badge.administrative { background: #fff3e0; color: #ef6c00; }
        .badge.general { background: #f3f3f3; color: #666; }
        
        .download-card h4 {
          margin: 0 0 6px 0;
          color: #333;
          font-size: 16px;
        }
        .download-card p {
          font-size: 13px;
          color: #666;
          margin: 0 0 12px 0;
          line-height: 1.4;
        }
        .btn-sm {
          padding: 6px 12px;
          font-size: 13px;
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }
        .btn-icon {
          width: 14px;
          height: 14px;
        }
        .info-box {
            background: #fff;
            border-left: 4px solid var(--olive);
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .info-box h4 { margin: 0 0 8px 0; color: var(--olive); }
        .info-box p { margin: 0; color: #555; font-size: 14px; }
        
        /* Grid for form inputs */
        .grid-2 {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }
        @media (max-width: 600px) {
          .grid-2 { grid-template-columns: 1fr; }
        }
      `}</style>
    </div>
  );
}

export default DocumentAssistant;