import { CheckCircle2 } from 'lucide-react';

export const SECTIONS: { key: string; label: string; help: string }[] = [
  { key: 'executive_summary', label: 'Executive summary', help: 'Headline findings in a paragraph' },
  { key: 'overview', label: 'Data overview', help: 'Size, memory, and the column profile' },
  { key: 'quality', label: 'Data quality', help: 'Missing values, duplicates, outliers, type issues' },
  { key: 'statistics', label: 'Statistical summary', help: 'Numeric and categorical column statistics' },
  { key: 'correlation', label: 'Correlation analysis', help: 'Strong pairs and the full matrix' },
  { key: 'distribution', label: 'Distributions', help: 'Shape and skew of each numeric column' },
  { key: 'insights', label: 'Key insights (AI)', help: 'Answers you saved from AI analysis' },
];

export function ReportSections({ selected, onToggle }: {
  selected: string[];
  onToggle: (key: string) => void;
}) {
  return (
    <>
      <h4>INCLUDED SECTIONS</h4>
      {SECTIONS.map((section) => (
        <label className="check" key={section.key}>
          <input type="checkbox" checked={selected.includes(section.key)}
                 onChange={() => onToggle(section.key)} />
          <span>
            <CheckCircle2 />
            <div>
              {section.label}
              <small>{section.help}</small>
            </div>
          </span>
        </label>
      ))}
    </>
  );
}
