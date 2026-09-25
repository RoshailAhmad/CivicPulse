import type { Category, Priority, Status } from "../api/client";
import { CATEGORY_LABEL, PRIORITY_LABEL, STATUS_LABEL } from "../labels";

/** Category shown as a utility-marking colour swatch plus its name. */
export function CategoryMark({ category }: { category: Category }) {
  return (
    <span className={`category category--${category}`}>
      <span className="category__swatch" aria-hidden="true" />
      {CATEGORY_LABEL[category]}
    </span>
  );
}

export function PriorityTag({ priority }: { priority: Priority }) {
  return <span className={`priority priority--${priority}`}>{PRIORITY_LABEL[priority]}</span>;
}

export function StatusText({ status }: { status: Status }) {
  return <span className={`status status--${status}`}>{STATUS_LABEL[status]}</span>;
}
