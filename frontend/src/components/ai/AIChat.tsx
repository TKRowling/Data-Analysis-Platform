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
    onAsk(question);
    setQuestion('');
  };

  return (
    <div className="prompt-card">
      <textarea
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        placeholder="Ask anything about this dataset — try: What are the top 5 products by sales?"
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
      />
      <button onClick={submit} disabled={busy || !question.trim()}>
        <Sparkles size={18} />
        {busy ? 'Analyzing…' : 'Ask Datum'}
      </button>
      <div className="suggestions">
        {suggestions.map((text) => (
          <button key={text} onClick={() => setQuestion(text)} disabled={busy}>{text}</button>
        ))}
      </div>
    </div>
  );
}
