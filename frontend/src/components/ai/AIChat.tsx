import { useState } from 'react';
import { Sparkles } from 'lucide-react';

const SUGGESTIONS = [
  'What are the top 5 products by sales?',
  'Show me the correlation between age and income',
  "What's the average revenue by region?",
  'Identify outliers in the price column',
  'Generate a summary of customer segments',
];

export function AIChat({ onAsk, busy, suggestions = SUGGESTIONS }: {
  onAsk: (question: string) => void;
  busy: boolean;
  suggestions?: string[];
}) {
  const [question, setQuestion] = useState('');
  const submit = () => {
    if (!question.trim() || busy) return;
    onAsk(question.trim());
    setQuestion('');
  };

  return <section className="ai-composer">
    <div className="example-queries">
      <h2>Ask Questions About Your Data in Natural Language</h2>
      <p>The analysis agents interpret your question, run verified calculations, and return clear insights from your dataset.</p>
      <h3>Example queries</h3>
      <ul>{suggestions.map(text => <li key={text}><button type="button" onClick={() => setQuestion(text)} disabled={busy}>{text}</button></li>)}</ul>
    </div>
    <label className="question-label" htmlFor="ai-question">Enter your question</label>
    <div className="question-box">
      <textarea id="ai-question" value={question} onChange={event => setQuestion(event.target.value)}
        placeholder="E.g., What are the key insights from this dataset?"
        onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit(); } }} />
      <div className="question-actions">
        <span>Enter to analyze · Shift + Enter for a new line</span>
        <button type="button" onClick={submit} disabled={busy || !question.trim()}><Sparkles size={18}/>{busy ? 'Analyzing…' : 'Analyze question'}</button>
      </div>
    </div>
  </section>;
}
