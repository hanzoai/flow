import { Background, Panel } from "@xyflow/react";
import { cloneDeep } from "lodash";
import { memo, useCallback, useState } from "react";
import { useShallow } from "zustand/react/shallow";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import CanvasControlButton from "@/components/core/canvasControlsComponent/CanvasControlButton";
import CanvasControls from "@/components/core/canvasControlsComponent/CanvasControls";
import { Button } from "@hanzo/ui";
import { ENABLE_NEW_SIDEBAR } from "@/customization/feature-flags";
import useSaveFlow from "@/hooks/flows/use-save-flow";
import useFlowStore from "@/stores/flowStore";
import { AllNodeType } from "@/types/flow";
import { cn } from "@/utils/utils";

export const MemoizedBackground = memo(() => (
  <Background size={2} gap={20} className="" />
));

interface MemoizedCanvasControlsProps {
  setIsAddingNote: (value: boolean) => void;
  shadowBoxWidth: number;
  shadowBoxHeight: number;
  selectedNode: AllNodeType | null;
  isAgentWorking?: boolean;
}

export const MemoizedCanvasControls = memo(
  ({
    setIsAddingNote,
    shadowBoxWidth,
    shadowBoxHeight,
    selectedNode,
    isAgentWorking,
  }: MemoizedCanvasControlsProps) => {
    const currentFlow = useFlowStore(useShallow((state) => state.currentFlow));
    const setCurrentFlow = useFlowStore((state) => state.setCurrentFlow);
    const saveFlow = useSaveFlow();
    const isLocked = currentFlow?.locked ?? false;
    const effectiveLocked = isLocked || isAgentWorking;
    const [isSaving, setIsSaving] = useState(false);

    const handleToggleLock = useCallback(async () => {
      if (isAgentWorking || isSaving || !currentFlow) return;
      const newFlow = cloneDeep(currentFlow);
      newFlow.locked = !isLocked;
      setIsSaving(true);
      try {
        await saveFlow(newFlow);
        setCurrentFlow(newFlow);
      } finally {
        setIsSaving(false);
      }
    }, [
      currentFlow,
      isLocked,
      isAgentWorking,
      isSaving,
      saveFlow,
      setCurrentFlow,
    ]);

    return (
      <CanvasControls
        selectedNode={selectedNode}
        effectiveLocked={effectiveLocked}
      >
        <Button
          unstyled
          size="icon"
          data-testid="lock-status"
          disabled={isAgentWorking || isSaving}
          className={cn(
            "flex items-center justify-center px-2 rounded-none gap-1",
            isAgentWorking || isSaving
              ? "cursor-default opacity-70"
              : "cursor-pointer",
          )}
          title={
            isAgentWorking
              ? "Agent Working"
              : isSaving
                ? "Saving..."
                : isLocked
                  ? "Unlock flow"
                  : "Lock flow"
          }
          onClick={handleToggleLock}
        >
          <ForwardedIconComponent
            name={effectiveLocked ? "Lock" : "Unlock"}
            className={cn(
              "!h-[18px] !w-[18px] text-muted-foreground",
              effectiveLocked && "text-destructive",
            )}
          />
          {effectiveLocked && (
            <span className="text-xs text-destructive">
              {isAgentWorking ? "Agent Working" : "Flow Locked"}
            </span>
          )}
        </Button>
      </CanvasControls>
    );
  },
);

