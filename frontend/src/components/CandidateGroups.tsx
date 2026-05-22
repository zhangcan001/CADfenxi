import type { RecognitionCandidate } from "../api/candidates";
import { fieldNameLabel, sourceTypeLabel } from "../formatters";

export function CandidateGroups({ candidates }: { candidates: RecognitionCandidate[] }) {
  const fields = ["drawing_no", "drawing_name", "discipline", "version", "issue_date"];
  return (
    <div className="candidate-groups">
      {fields.map((field) => {
        const items = candidates.filter((candidate) => candidate.field_name === field);
        if (items.length === 0) {
          return null;
        }
        return (
          <section className="candidate-group" key={field}>
            <h4>{fieldNameLabel(field)}</h4>
            {items.map((candidate) => (
              <article className="candidate-row" key={candidate.id}>
                <strong>{candidate.candidate_value}</strong>
                <span>标准化：{candidate.normalized_value || "-"}</span>
                <span>来源：{sourceTypeLabel(candidate.source_type)}</span>
                <span>置信度：{candidate.confidence}</span>
                <span>解析器：{candidate.parser_name} / {candidate.parser_version}</span>
                <details>
                  <summary>原始文本</summary>
                  <p>{candidate.raw_text}</p>
                </details>
              </article>
            ))}
          </section>
        );
      })}
    </div>
  );
}
