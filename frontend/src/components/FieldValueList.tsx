import type { FieldEvidence, FieldValue } from "../api/fusion";
import { fieldNameLabel, sourceTypeLabel } from "../formatters";

export function FieldValueList({
  values,
  evidence
}: {
  values: FieldValue[];
  evidence: FieldEvidence[];
}) {
  return (
    <div className="candidate-groups">
      {values.map((value) => {
        const relatedEvidence = evidence.filter((item) => item.field_value_id === value.id);
        return (
          <section className="candidate-group" key={value.id}>
            <h4>{fieldNameLabel(value.field_name)}</h4>
            <article className="candidate-row">
              <strong>{value.display_value}</strong>
              <span>标准化：{value.normalized_value || "-"}</span>
              <span>来源：{sourceTypeLabel(value.final_source)}</span>
              <span>置信度：{value.confidence}</span>
              <span>人工确认：{value.is_reviewed ? "是" : "否"}</span>
              {relatedEvidence.length > 0 ? (
                <details>
                  <summary>证据链</summary>
                  {relatedEvidence.map((item) => (
                    <p key={item.id}>
                      {sourceTypeLabel(item.source_type)} / {item.confidence}：{item.raw_text}
                    </p>
                  ))}
                </details>
              ) : null}
            </article>
          </section>
        );
      })}
    </div>
  );
}
