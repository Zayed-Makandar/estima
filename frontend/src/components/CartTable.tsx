import { MarketplaceItem } from "../types";

type Props = {
  items: MarketplaceItem[];
  onRemove: (idx: number) => void;
  onExport: () => void;
  onCopy: () => void;
};

export function CartTable({ items, onRemove, onExport, onCopy }: Props) {
  return (
    <div className="card">
      <div className="card-header">
        <h2>Chosen Items</h2>
        <div className="actions">
          <button type="button" onClick={onCopy} disabled={items.length === 0}>
            Copy Table
          </button>
          <button type="button" onClick={onExport} disabled={items.length === 0}>
            Export CSV
          </button>
        </div>
      </div>
      {items.length === 0 ? (
        <p className="muted">No items selected yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Price</th>
              <th>Availability</th>
              <th>Source</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, idx) => (
              <tr key={`${item.url}-${idx}`}>
                <td>{item.title}</td>
                <td>{item.price_text}</td>
                <td>{item.availability}</td>
                <td>{item.source}</td>
                <td>
                  <button type="button" onClick={() => onRemove(idx)}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

