import { CheckCircle, XCircle, Info, X } from "lucide-react";
import { useAppStore } from "../../store";

const icons = {
  success: <CheckCircle size={16} className="text-emerald-500" />,
  error:   <XCircle    size={16} className="text-red-500" />,
  info:    <Info       size={16} className="text-brand-500" />,
};

const bg = {
  success: "border-emerald-200 bg-emerald-50",
  error:   "border-red-200   bg-red-50",
  info:    "border-brand-100 bg-brand-50",
};

export function ToastContainer() {
  const { toasts, dismissToast } = useAppStore();

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 w-80">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`flex items-start gap-2 p-3 rounded-xl border shadow-lg text-sm ${bg[t.kind]} animate-in slide-in-from-right-4`}
        >
          <span className="mt-0.5 shrink-0">{icons[t.kind]}</span>
          <span className="flex-1 text-slate-700">{t.message}</span>
          <button
            onClick={() => dismissToast(t.id)}
            className="shrink-0 text-slate-400 hover:text-slate-600"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
