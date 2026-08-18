import type { SessionSeat } from "../api/types";

interface SeatMapProps {
  seats: SessionSeat[];
  selectedIds: number[];
  onToggle: (seatId: number) => void;
}

export default function SeatMap({ seats, selectedIds, onToggle }: SeatMapProps) {
  const rowNos = [...new Set(seats.map((s) => s.row_no))].sort((a, b) => a - b);
  const colNos = [...new Set(seats.map((s) => s.col_no))].sort((a, b) => a - b);
  const byPos = new Map(seats.map((s) => [`${s.row_no}-${s.col_no}`, s]));

  return (
    <div className="seat-map">
      <div className="seat-screen">荧 幕</div>
      {rowNos.map((r) => (
        <div className="seat-row" key={r}>
          <span className="seat-row-label">{r}排</span>
          {colNos.map((c) => {
            const seat = byPos.get(`${r}-${c}`);
            if (!seat) return <span className="seat-empty" key={c} />;
            const clickable = seat.status === "AVAILABLE";
            const cls = [
              "seat-btn",
              seat.status.toLowerCase(),
              selectedIds.includes(seat.id) ? "selected" : "",
            ].join(" ");
            const title =
              seat.status === "AVAILABLE"
                ? `${seat.seat_no} 可选`
                : seat.status === "DISABLED"
                  ? "不可用"
                  : "已售罄";
            return (
              <button
                key={c}
                className={cls}
                disabled={!clickable}
                title={title}
                onClick={() => onToggle(seat.id)}
              >
                {seat.seat_no}
              </button>
            );
          })}
        </div>
      ))}
      <div className="seat-legend">
        <span><i className="dot available" />可选</span>
        <span><i className="dot selected" />已选</span>
        <span><i className="dot sold" />已售罄</span>
        <span><i className="dot disabled" />不可用</span>
      </div>
    </div>
  );
}
