import { useState, useEffect } from 'react';
import { useRoute, useLocation } from 'wouter';
import styles from './styles.module.scss';

interface AnalysisResult {
  document_id: string;
  summary: string;
  key_points: string[];
  risks_and_concerns: string[];
  recommendations: string[];
  simplified_explanation: string;
}

interface QuestionAnswer {
  question: string;
  answer: string;
  relevant_sections: string[];
  confidence_level: string;
  timestamp?: number;
}

export const ResultsPage = () => {
  const [, params] = useRoute('/results/:documentId');
  const [, setLocation] = useLocation();
  
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [question, setQuestion] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const [answers, setAnswers] = useState<QuestionAnswer[]>([]);
  const [error, setError] = useState('');
  const [isChatExpanded, setIsChatExpanded] = useState(false);

  useEffect(() => {
    // Get analysis result from sessionStorage
    const storedResult = sessionStorage.getItem('analysisResult');
    if (storedResult) {
      setAnalysisResult(JSON.parse(storedResult) as AnalysisResult);
    } else if (!params?.documentId) {
      // No result and no document ID, redirect to home
      setLocation('/');
    }
  }, [params, setLocation]);

  const handleAskQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!question.trim()) return;
    if (!analysisResult) {
      setError('No document loaded');
      return;
    }

    setIsAsking(true);
    const currentQuestion = question;
    setError('');

    try {
      const response = await fetch('/ask-question', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: currentQuestion,
          document_id: analysisResult.document_id,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json() as { detail?: string };
        throw new Error(errorData.detail || 'Question failed');
      }

      const data = await response.json() as {
        answer: string;
        relevant_sections: string[];
        confidence_level: string;
      };
      
      const newAnswer: QuestionAnswer = {
        question: currentQuestion,
        answer: data.answer,
        relevant_sections: data.relevant_sections,
        confidence_level: data.confidence_level,
        timestamp: Date.now(),
      };

      setAnswers(prev => [...prev, newAnswer]);
      setQuestion('');
      setIsChatExpanded(true); // Expand chat when answer arrives

      // Save to backend
      await fetch('/save-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newAnswer),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsAsking(false);
    }
  };

  const handleNewAnalysis = () => {
    sessionStorage.removeItem('analysisResult');
    setLocation('/');
  };

  if (!analysisResult) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading...</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1 className={styles.title}>Analysis Results</h1>
          <button onClick={handleNewAnalysis} className={styles.newAnalysisBtn}>
            New Analysis
          </button>
        </div>
      </header>

      <div className={styles.mainContent}>
        <section className={styles.resultsSection}>
          <div className={styles.card}>
            <div className={styles.analysisBlock}>
              <h3>Summary</h3>
              <p>{analysisResult.summary}</p>
            </div>

            <div className={styles.analysisBlock}>
              <h3>Key Points</h3>
              <ul>
                {analysisResult.key_points.map((point, idx) => (
                  <li key={idx}>{point}</li>
                ))}
              </ul>
            </div>

            <div className={`${styles.analysisBlock} ${styles.risksBlock}`}>
              <h3>Risks & Concerns</h3>
              <ul>
                {analysisResult.risks_and_concerns.map((risk, idx) => (
                  <li key={idx}>{risk}</li>
                ))}
              </ul>
            </div>

            <div className={`${styles.analysisBlock} ${styles.recommendBlock}`}>
              <h3>Recommendations</h3>
              <ul>
                {analysisResult.recommendations.map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            </div>

            <div className={styles.analysisBlock}>
              <h3>In Simple Terms</h3>
              <p>{analysisResult.simplified_explanation}</p>
            </div>
          </div>
        </section>
      </div>

      {/* Fixed Chat Panel at Bottom */}
      <div className={`${styles.chatPanel} ${isChatExpanded ? styles.expanded : ''}`}>
        <div className={styles.chatHeader}>
          <h2>Ask Questions About This Document</h2>
          <div className={styles.chatHeaderButtons}>
            {!isChatExpanded && answers.length > 0 && (
              <button 
                className={styles.expandBtn}
                onClick={() => setIsChatExpanded(true)}
                aria-label="Expand chat history"
                title="View chat history"
              >
                ↑
              </button>
            )}
            {isChatExpanded && (
              <button 
                className={styles.collapseBtn}
                onClick={() => setIsChatExpanded(false)}
                aria-label="Minimize chat"
                title="Minimize"
              >
                −
              </button>
            )}
          </div>
        </div>

        {isChatExpanded && answers.length > 0 && (
          <div className={styles.answersContainer}>
            {answers.map((qa, idx) => (
              <div key={idx} className={styles.answerBlock}>
                <div className={styles.questionLabel}>
                  <strong>Q:</strong> {qa.question}
                </div>
                <div className={styles.answerContent}>
                  <div className={styles.answerText}>
                    <strong>A:</strong> {qa.answer}
                  </div>
                  {qa.relevant_sections.length > 0 && (
                    <div className={styles.relevantSections}>
                      <strong>Relevant Sections:</strong>
                      <ul>
                        {qa.relevant_sections.map((section, sidx) => (
                          <li key={sidx}>{section}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <span className={styles.confidenceBadge}>
                    Confidence: {qa.confidence_level}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        <form onSubmit={handleAskQuestion} className={styles.qaForm}>
          <textarea
            rows={2}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="E.g. What happens if I pay late?"
            className={styles.questionInput}
          />
          <button type="submit" className={styles.askBtn} disabled={isAsking}>
            {isAsking ? 'Getting Answer...' : 'Ask Question'}
          </button>
        </form>

        {error && <div className={styles.error}>{error}</div>}
      </div>
    </div>
  );
};
