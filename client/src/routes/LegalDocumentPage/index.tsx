import { useState } from 'react';
import { useLocation } from 'wouter';
import styles from './styles.module.scss';
import { getApiUrl } from '@client/utils/api';

interface AnalysisResult {
  document_id: string;
  summary: string;
  key_points: string[];
  risks_and_concerns: string[];
  recommendations: string[];
  simplified_explanation: string;
}

export const LegalDocumentPage = () => {
  const [, setLocation] = useLocation();
  
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState('');
  const [documentType, setDocumentType] = useState('contract');
  const [userRole, setUserRole] = useState('individual');
  const [complexityLevel, setComplexityLevel] = useState('simple');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!file && !text.trim()) {
      setError('Please upload a file or paste text');
      return;
    }

    setIsAnalyzing(true);
    setError('');

    try {
      let response;
      
      if (file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('document_type', documentType);
        formData.append('user_role', userRole);
        formData.append('complexity_level', complexityLevel);
        
        response = await fetch(getApiUrl('analyze-document'), {
          method: 'POST',
          body: formData,
        });
      } else {
        response = await fetch(getApiUrl('analyze-text'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text,
            document_type: documentType,
            user_role: userRole,
            complexity_level: complexityLevel,
          }),
        });
      }

      if (!response.ok) {
        const errorData = await response.json() as { detail?: string };
        throw new Error(errorData.detail || 'Analysis failed');
      }

      const data = await response.json() as AnalysisResult;
      
      // Store result in sessionStorage
      sessionStorage.setItem('analysisResult', JSON.stringify(data));
      
      // Navigate to results page
      setLocation(`/results/${data.document_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      
      // Provide helpful guidance if it's an API key error
      if (err instanceof Error && err.message.includes('400')) {
        setError('API Error: Please ensure your GEMINI_API_KEY environment variable is set with a valid API key. Get one from: https://aistudio.google.com/app/apikey');
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className={styles.container}>
      {isAnalyzing && (
        <div className={styles.loadingOverlay}>
          <div className={styles.loadingContent}>
            <div className={styles.spinner}></div>
            <h2 className={styles.loadingTitle}>Analyzing Your Document</h2>
            <p className={styles.loadingText}>Our AI is reading and understanding your document...</p>
            <div className={styles.loadingSteps}>
              <div className={styles.step}>Extracting content</div>
              <div className={styles.step}>Identifying key points</div>
              <div className={styles.step}>Analyzing legal terms</div>
              <div className={styles.step}>Generating insights</div>
            </div>
          </div>
        </div>
      )}
      
      <header className={styles.header}>
        <h1 className={styles.title}>Legal Document Demystifier</h1>
        <p className={styles.subtitle}>AI-powered clarity for your legal documents</p>
      </header>

      <div className={styles.mainContent}>
        <section className={styles.uploadSection}>
          <div className={styles.card}>
            <h2>Upload or Paste Document</h2>
            <p className={styles.helperText}>We process your document in-memory only. No storage.</p>
            
            <form onSubmit={handleAnalyze} className={styles.form}>
              <div className={styles.fileInput}>
                <label htmlFor="fileInput">File (PDF / TXT / DOCX)</label>
                <input
                  id="fileInput"
                  type="file"
                  accept=".pdf,.txt,.doc,.docx"
                  onChange={handleFileChange}
                />
                <span className={styles.hint}>Optional if you paste text</span>
              </div>

              <div className={styles.textInput}>
                <label htmlFor="textInput">Or Paste Text</label>
                <textarea
                  id="textInput"
                  rows={6}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Paste your legal document here..."
                />
                <span className={styles.hint}>We recommend under 10k characters for fastest results.</span>
              </div>

              <div className={styles.selectGroup}>
                <div>
                  <label htmlFor="documentType">Document Type</label>
                  <select
                    id="documentType"
                    value={documentType}
                    onChange={(e) => setDocumentType(e.target.value)}
                  >
                    <option value="contract">Contract</option>
                    <option value="rental_agreement">Rental Agreement</option>
                    <option value="loan_agreement">Loan Agreement</option>
                    <option value="terms_of_service">Terms of Service</option>
                    <option value="privacy_policy">Privacy Policy</option>
                    <option value="employment_contract">Employment Contract</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="userRole">Your Role</label>
                  <select
                    id="userRole"
                    value={userRole}
                    onChange={(e) => setUserRole(e.target.value)}
                  >
                    <option value="individual">Individual / Consumer</option>
                    <option value="business">Small Business Owner</option>
                    <option value="tenant">Tenant / Renter</option>
                    <option value="borrower">Borrower</option>
                    <option value="employee">Employee</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="complexityLevel">Explanation Detail</label>
                  <select
                    id="complexityLevel"
                    value={complexityLevel}
                    onChange={(e) => setComplexityLevel(e.target.value)}
                  >
                    <option value="simple">Simple</option>
                    <option value="detailed">Detailed</option>
                    <option value="expert">Expert</option>
                  </select>
                </div>
              </div>

              <div className={styles.actions}>
                <button type="submit" className={styles.primaryBtn} disabled={isAnalyzing}>
                  {isAnalyzing ? 'Analyzing...' : 'Analyze Document'}
                </button>
              </div>

              {error && <div className={styles.error}>{error}</div>}
            </form>
          </div>
        </section>
      </div>
    </div>
  );
};
