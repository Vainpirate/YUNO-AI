import { useEffect, useState } from "react";
import { AgentList } from "../components/AgentList";
import { Spinner } from "../components/shared/Spinner";
import { agentApi } from "../services/api";
import { useAppStore } from "../store";

export function AgentManager() {
  const { setAgents, pushToast } = useAppStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    agentApi.list()
      .then(setAgents)
      .catch(() => pushToast("Failed to load agents", "error"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex-1 flex items-center justify-center">
      <Spinner size={28} />
    </div>
  );

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <AgentList />
    </div>
  );
}
