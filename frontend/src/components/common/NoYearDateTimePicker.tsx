import { useMemo } from "react";
import { Calendar } from "lucide-react";

interface NoYearDateTimePickerProps {
  label: string;
  value: string; // e.g. "2026-10-20T11:28:57" or ""
  onChange: (value: string) => void;
  disabled?: boolean;
  defaultTime?: string; // e.g. "00:00:00" for start, "23:59:59" for end
}

const MONTHS = [
  { value: "01", name: "Jan", full: "January" },
  { value: "02", name: "Feb", full: "February" },
  { value: "03", name: "Mar", full: "March" },
  { value: "04", name: "Apr", full: "April" },
  { value: "05", name: "May", full: "May" },
  { value: "06", name: "Jun", full: "June" },
  { value: "07", name: "Jul", full: "July" },
  { value: "08", name: "Aug", full: "August" },
  { value: "09", name: "Sep", full: "September" },
  { value: "10", name: "Oct", full: "October" },
  { value: "11", name: "Nov", full: "November" },
  { value: "12", name: "Dec", full: "December" },
];

export function NoYearDateTimePicker({
  label,
  value,
  onChange,
  disabled,
  defaultTime = "00:00:00",
}: NoYearDateTimePickerProps) {
  // Parse month, day, time from value
  const { month, day, time } = useMemo(() => {
    if (!value) return { month: "", day: "", time: "" };

    // Matches YYYY-MM-DDTHH:mm(:ss) or MM-DDTHH:mm(:ss)
    const match = value.match(
      /(?:^\d{4}-)?(\d{2})-(\d{2})[T ](\d{2}:\d{2}(?::\d{2})?)/,
    );
    if (match) {
      return { month: match[1], day: match[2], time: match[3] };
    }
    return { month: "", day: "", time: "" };
  }, [value]);

  // Max days in the selected month
  const maxDays = useMemo(() => {
    if (!month) return 31;
    const m = parseInt(month, 10);
    if (m === 2) return 29;
    if ([4, 6, 9, 11].includes(m)) return 30;
    return 31;
  }, [month]);

  const update = (newMonth: string, newDay: string, newTime: string) => {
    if (!newMonth && !newDay && !newTime) {
      onChange("");
      return;
    }

    const m = newMonth !== undefined ? newMonth : month;
    const d = newDay !== undefined ? newDay : day;
    const t = newTime !== undefined ? newTime : time || defaultTime;

    if (!m || !d) {
      onChange("");
      return;
    }

    const year = new Date().getFullYear();
    const formatted = `${year}-${m.padStart(2, "0")}-${d.padStart(2, "0")}T${t || defaultTime}`;
    onChange(formatted);
  };

  // Compute log format preview (e.g. "Oct 20 11:28:57 AM")
  const preview = useMemo(() => {
    if (!month || !day) return null;
    const mObj = MONTHS.find((item) => item.value === month);
    const mName = mObj ? mObj.name : month;

    if (!time) return `${mName} ${parseInt(day, 10)}`;

    const [hStr, minStr, secStr] = time.split(":");
    const h = parseInt(hStr, 10);
    const ampm = h >= 12 ? "PM" : "AM";
    const h12 = h % 12 || 12;
    const sec = secStr !== undefined ? `:${secStr}` : ":00";
    return `${mName} ${parseInt(day, 10)} ${String(h12).padStart(2, "0")}:${minStr || "00"}${sec} ${ampm}`;
  }, [month, day, time]);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label className="block text-xs font-medium text-slate-700">
          {label}
        </label>
        {preview && (
          <span className="text-[11px] font-mono text-primary-700 bg-primary-50 px-2 py-0.5 rounded border border-primary-100">
            Log format: {preview}
          </span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-2">
        {/* Month */}
        <div className="relative">
          <select
            aria-label={`${label} Month`}
            value={month}
            onChange={(e) => update(e.target.value, day, time)}
            disabled={disabled}
            className="w-full appearance-none rounded-md border border-slate-300 bg-white px-2.5 py-2 pr-7 text-sm text-slate-800 focus:border-primary-500 focus:ring-primary-500 focus:outline-none disabled:bg-slate-50 disabled:text-slate-400"
          >
            <option value="">Month</option>
            {MONTHS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.name} ({m.value})
              </option>
            ))}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2 text-slate-400">
            <Calendar size={14} />
          </div>
        </div>

        {/* Day */}
        <div className="relative">
          <select
            aria-label={`${label} Day`}
            value={day}
            onChange={(e) => update(month, e.target.value, time)}
            disabled={disabled}
            className="w-full appearance-none rounded-md border border-slate-300 bg-white px-2.5 py-2 pr-7 text-sm text-slate-800 focus:border-primary-500 focus:ring-primary-500 focus:outline-none disabled:bg-slate-50 disabled:text-slate-400"
          >
            <option value="">Day</option>
            {Array.from({ length: maxDays }, (_, i) => i + 1).map((d) => {
              const dStr = String(d).padStart(2, "0");
              return (
                <option key={dStr} value={dStr}>
                  {d}
                </option>
              );
            })}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2 text-slate-400">
            <Calendar size={14} />
          </div>
        </div>

        {/* Time */}
        <div>
          <input
            aria-label={`${label} Time`}
            type="time"
            step="1"
            value={time ? time.slice(0, 8) : ""}
            onChange={(e) => update(month, day, e.target.value)}
            disabled={disabled}
            className="w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-800 focus:border-primary-500 focus:ring-primary-500 focus:outline-none disabled:bg-slate-50 disabled:text-slate-400"
          />
        </div>
      </div>
    </div>
  );
}
